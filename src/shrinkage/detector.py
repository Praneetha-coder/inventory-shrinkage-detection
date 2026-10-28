"""Rule engine that compares receipts, sales, transfers, adjustments, returns and counts.

INPUT: only operational tables (never ground truth).  OUTPUT: shrinkage_alerts + alert_evidence.
Every alert carries evidence rows and a reason_text built from those records (evidence-based).

Rules / decisions
  R01 COUNT_VARIANCE            negative count variance >= 4 units AND >= $40
        - explained by a timing mismatch around a transfer leg   -> AUTO_CLOSE_BENIGN (exception path)
        - explained by count_ts earlier than a posted movement   -> handled by R08 (DATA_FIX), no theft alert
        - otherwise                                              -> INVESTIGATE
  R02 REPEATED_ADJUSTMENTS      >= 8 negative adjustments by one employee in 14 days, >= 3 on the same SKU -> INVESTIGATE
  R03 RETURN_WITHOUT_SALE       >= 3 unapproved no-receipt returns by one cashier in 30 days               -> INVESTIGATE
  R04 DAMAGE_SPIKE              store-day with >= 6 damage rows (and >= 3x that store's normal daily rate) and >= $400
        - >= 80% of the value has reason + incident reference + manager actor -> AUTO_CLOSE_BENIGN, else INVESTIGATE
  R05 UNAUTHORIZED_ADJUSTMENT   adjustment by an employee whose effective role cannot adjust                -> INVESTIGATE
  R06 WRONG_STORE_MOVEMENT      movement.store_id <> store of the shift that posted it                      -> DATA_FIX
  R07 ADJUSTMENT_NO_REASON      adjustment with NULL reason_code                                            -> DATA_FIX
  R08 COUNT_TIMESTAMP_INCONSISTENT  count entered >45 min after count_ts and a movement posted in between   -> DATA_FIX
"""
from __future__ import annotations

import math

import numpy as np
import pandas as pd

TH = dict(min_units=4, min_value=40.0, dmg_rows=6, dmg_value=400.0, adj_days=14, adj_n=8, adj_same=3,
          ret_days=30, ret_n=3, ts_gap_min=45, qty_tol=.10)


def _ts(x):
    return pd.to_datetime(x)


def detect(t: dict) -> tuple[pd.DataFrame, pd.DataFrame]:
    mv, cn, sh, er, rt, sk = (t[k] for k in ("inventory_movements", "cycle_counts", "shifts", "employee_roles", "returns", "skus"))
    cost = sk.set_index("sku_id").unit_cost
    mv = mv.assign(mts=_ts(mv.movement_ts), pts=_ts(mv.posted_ts))
    cn = cn.assign(cts=_ts(cn.count_ts), ets=_ts(cn.entered_ts))
    raw = []

    def emit(rule, atype, store, sku, emp, anchor, units, value, action, text, ev):
        raw.append(dict(rule_code=rule, alert_type=atype, store_id=store, sku_id=sku, employee_id=emp, anchor=anchor,
                        units=int(units), value=round(float(value), 2), action=action, text=text, ev=ev))

    # ---------------------------------------------------------------- R06 wrong store
    sstore = sh.set_index("shift_id").store_id
    m = mv.assign(shift_store=mv.shift_id.map(sstore))
    for r in m[m.store_id != m.shift_store].itertuples():
        v = abs(r.quantity_signed) * cost[r.sku_id]
        emit("R06", "WRONG_STORE_MOVEMENT", r.store_id, r.sku_id, r.employee_id, r.pts, abs(r.quantity_signed), v, "DATA_FIX",
             f"{r.movement_id} ({r.movement_type}, {r.quantity_signed:+d} units of {r.sku_id}) is booked to {r.store_id} but its shift "
             f"{r.shift_id} and employee {r.employee_id} belong to {r.shift_store}; both stores' book balances are mis-stated by the same quantity.",
             [("MOVEMENT", r.movement_id, "PRIMARY"), ("SHIFT", r.shift_id, "SUPPORTING")])

    # ---------------------------------------------------------------- R07 adjustment without reason / R05 unauthorised
    adj = mv[mv.movement_type == "ADJUSTMENT"]
    for r in adj[adj.reason_code.isna()].itertuples():
        emit("R07", "ADJUSTMENT_NO_REASON", r.store_id, r.sku_id, r.employee_id, r.pts, abs(r.quantity_signed),
             abs(r.quantity_signed) * cost[r.sku_id], "DATA_FIX",
             f"Adjustment {r.movement_id} ({r.quantity_signed:+d} units of {r.sku_id}) by {r.employee_id} has no reason code; a reason is mandatory for every adjustment.",
             [("MOVEMENT", r.movement_id, "PRIMARY")])
    a = adj.merge(er[["employee_id", "role_code", "can_adjust_inventory", "effective_from", "effective_to"]], on="employee_id")
    d = a.pts.dt.normalize()
    a = a[(d >= _ts(a.effective_from)) & (a.effective_to.isna() | (d <= _ts(a.effective_to))) & (a.can_adjust_inventory == 0)]
    for r in a.itertuples():
        emit("R05", "UNAUTHORIZED_ADJUSTMENT", r.store_id, r.sku_id, r.employee_id, r.pts, abs(r.quantity_signed),
             abs(r.quantity_signed) * cost[r.sku_id], "INVESTIGATE",
             f"Adjustment {r.movement_id} ({r.quantity_signed:+d} units of {r.sku_id}) was posted by {r.employee_id} whose effective role "
             f"{r.role_code} has no inventory-adjustment authority.", [("MOVEMENT", r.movement_id, "PRIMARY"), ("SHIFT", r.shift_id, "SUPPORTING")])

    # ---------------------------------------------------------------- R08 count timestamp precedes movement
    c8 = cn[(cn.ets - cn.cts) > pd.Timedelta(minutes=TH["ts_gap_min"])]
    explained_counts = set()
    if len(c8):
        j = c8[["count_id", "store_id", "sku_id", "cts", "ets", "variance_units"]].merge(
            mv[["movement_id", "store_id", "sku_id", "pts", "quantity_signed", "movement_type"]], on=["store_id", "sku_id"])
        j = j[(j.pts > j.cts) & (j.pts <= j.ets)]
        for cid, g in j.groupby("count_id"):
            c = c8[c8.count_id == cid].iloc[0]
            explained_counts.add(cid)
            q = int(-g.quantity_signed.sum())
            emit("R08", "COUNT_TIMESTAMP_INCONSISTENT", c.store_id, c.sku_id, None, c.ets, abs(q), abs(q) * cost[c.sku_id], "DATA_FIX",
                 f"Count {cid} is stamped {c.count_ts} but was entered {c.entered_ts}; {len(g)} movement(s) ({', '.join(g.movement_id)}) posted in between, "
                 f"so the book quantity used for the variance ({c.variance_units:+d}) excludes stock that the physical count already reflected.",
                 [("COUNT", cid, "PRIMARY")] + [("MOVEMENT", x, "EXPLAINING") for x in g.movement_id])

    # ---------------------------------------------------------------- R01 count variance with benign-explanation checks
    neg = cn[(cn.variance_units <= -TH["min_units"]) & (cn.variance_value <= -TH["min_value"]) & ~cn.count_id.isin(explained_counts)]
    if len(neg):
        xf = mv[mv.movement_type.isin(["TRANSFER_OUT", "TRANSFER_IN"])][
            ["movement_id", "store_id", "sku_id", "movement_type", "quantity_signed", "mts", "pts", "transfer_id", "counterparty_store_id"]]
        j = neg[["count_id", "store_id", "sku_id", "cts", "variance_units"]].merge(xf, on=["store_id", "sku_id"])
        lo, hi = j[["mts", "pts"]].min(axis=1), j[["mts", "pts"]].max(axis=1)
        tol = np.maximum(1, TH["qty_tol"] * j.variance_units.abs())
        j = j[(lo <= j.cts) & (j.cts < hi) & ((j.quantity_signed.abs() - j.variance_units.abs()).abs() <= tol)]
        j = j.drop_duplicates("count_id").set_index("count_id")
        ctx = mv[mv.movement_type.isin(["ADJUSTMENT", "DAMAGE"])][["store_id", "sku_id", "movement_id", "movement_type", "quantity_signed", "pts"]]
        ctx = ctx.merge(neg[["store_id", "sku_id"]].drop_duplicates(), on=["store_id", "sku_id"])
        for r in neg.itertuples():
            ev = [("COUNT", r.count_id, "PRIMARY")]
            if r.count_id in j.index:
                x = j.loc[r.count_id]
                other = mv[(mv.transfer_id == x.transfer_id) & (mv.movement_id != x.movement_id)]
                ev += [("MOVEMENT", x.movement_id, "EXPLAINING"), ("TRANSFER", x.transfer_id, "EXPLAINING")]
                ev += [("MOVEMENT", o, "SUPPORTING") for o in other.movement_id]
                txt = (f"Count {r.count_id} shows {r.variance_units:+d} units (${r.variance_value:,.2f}) for {r.sku_id} at {r.store_id}, but transfer movement "
                       f"{x.movement_id} ({x.movement_type}, {x.quantity_signed:+d}) of {x.transfer_id} straddles the count time: movement_ts and posted_ts are on "
                       f"opposite sides of count_ts, so the gap is goods in transit, not loss.")
                emit("R01", "COUNT_VARIANCE", r.store_id, r.sku_id, None, r.ets, -r.variance_units, -r.variance_value, "AUTO_CLOSE_BENIGN", txt, ev)
                continue
            c = ctx[(ctx.store_id == r.store_id) & (ctx.sku_id == r.sku_id) & (ctx.pts <= r.cts) & (ctx.pts > r.cts - pd.Timedelta(days=30))]
            ev += [("MOVEMENT", x, "SUPPORTING") for x in c.movement_id.head(5)]
            emit("R01", "COUNT_VARIANCE", r.store_id, r.sku_id, None, r.ets, -r.variance_units, -r.variance_value, "INVESTIGATE",
                 f"Count {r.count_id} shows {r.variance_units:+d} units (${r.variance_value:,.2f}; counted {r.counted_qty} vs book {r.book_qty}) for {r.sku_id} at {r.store_id}. "
                 f"No transfer timing mismatch or count-timestamp issue explains it, and {len(c)} recorded adjustment/damage movement(s) in the previous 30 days "
                 f"(net {int(c.quantity_signed.sum()):+d} units) do not account for the gap.", ev)

    # ---------------------------------------------------------------- R04 damage spike (store-specific baseline)
    dm = mv[mv.movement_type == "DAMAGE"].assign(day=lambda x: x.pts.dt.normalize(), val=lambda x: -x.quantity_signed * x.sku_id.map(cost))
    rs = sh.set_index("shift_id").role_on_shift
    dm["doc"] = dm.reason_code.notna() & dm.reference_note.notna() & dm.shift_id.map(rs).isin(["STORE_MANAGER", "ASSISTANT_MANAGER"])
    dm["docval"] = dm.val.where(dm.doc, 0.0)
    n_days = max(1, (mv.pts.max().normalize() - mv.pts.min().normalize()).days + 1)
    avg_rows = dm.groupby("store_id").size() / n_days                      # each store's normal daily write-off rate
    g = dm.groupby(["store_id", "day"]).agg(n=("movement_id", "size"), val=("val", "sum"), docval=("docval", "sum"),
                                            units=("quantity_signed", lambda s: -s.sum())).reset_index()
    g = g[(g.n >= np.maximum(TH["dmg_rows"], 3 * g.store_id.map(avg_rows))) & (g.val >= TH["dmg_value"])]
    for r in g.itertuples():
        rows = dm[(dm.store_id == r.store_id) & (dm.day == r.day)]
        share = r.docval / r.val
        doc = share >= .8
        emit("R04", "DAMAGE_SPIKE", r.store_id, None, None, rows.pts.max(), r.units, r.val, "AUTO_CLOSE_BENIGN" if doc else "INVESTIGATE",
             f"{int(r.n)} damage write-offs worth ${r.val:,.2f} at {r.store_id} on {r.day.date()}, well above its normal daily rate of {avg_rows[r.store_id]:.1f}. " +
             (f"{share:.0%} of the value carries a reason code, an incident reference and a manager-level actor, so the event is documented and the loss is already in the book."
              if doc else f"Only {share:.0%} of the value is documented with an incident reference and manager approval.") +
             f" Evidence includes {', '.join(rows.movement_id.head(3))}.",
             [("MOVEMENT", x, "PRIMARY") for x in rows.movement_id])

    # ---------------------------------------------------------------- R02 repeated negative adjustments
    na = adj[adj.quantity_signed < 0].assign(val=lambda x: -x.quantity_signed * x.sku_id.map(cost)).sort_values(["employee_id", "pts"])
    W = pd.Timedelta(days=TH["adj_days"])
    for emp, g in na.groupby("employee_id"):
        t_ = g.pts.values.astype("datetime64[s]").astype(np.int64); n = len(g)
        j0 = np.searchsorted(t_, t_ - int(W.total_seconds()), side="left")
        cand = np.flatnonzero(np.arange(n) - j0 + 1 >= TH["adj_n"])
        spans = []
        for i in cand:
            w = g.iloc[j0[i]:i + 1]
            if w.groupby("sku_id").size().max() >= TH["adj_same"]:
                spans.append([j0[i], i])
        merged = []
        for s_, e_ in spans:
            if merged and s_ <= merged[-1][1] + 1: merged[-1][1] = max(merged[-1][1], e_)
            else: merged.append([s_, e_])
        for s_, e_ in merged:
            w = g.iloc[s_:e_ + 1]
            top = w.groupby("sku_id").size().sort_values(ascending=False)
            emit("R02", "REPEATED_ADJUSTMENTS", w.store_id.iloc[0], None, emp, w.pts.max(), -w.quantity_signed.sum(), w.val.sum(), "INVESTIGATE",
                 f"{emp} posted {len(w)} negative adjustments totalling {-w.quantity_signed.sum()} units (${w.val.sum():,.2f}) between {w.pts.min():%Y-%m-%d} and "
                 f"{w.pts.max():%Y-%m-%d}; {top.index[0]} alone was adjusted {top.iloc[0]} times. Counts cannot reveal this because each adjustment resets the book. Evidence includes {', '.join(w.movement_id.head(3))}.",
                 [("MOVEMENT", x, "PRIMARY") for x in w.movement_id])

    # ---------------------------------------------------------------- R03 phantom returns
    rr = rt[rt.original_sale_movement_id.isna() & rt.approved_by_employee_id.isna() & rt.return_movement_id.notna()].assign(rts=lambda x: _ts(x.return_ts))
    rr = rr.assign(val=rr.quantity * rr.sku_id.map(cost)).sort_values(["store_id", "processed_by_employee_id", "rts"])
    for (sid, emp), g in rr.groupby(["store_id", "processed_by_employee_id"]):
        grp, last = [], None
        for r in g.itertuples():
            if last is None or r.rts - last > pd.Timedelta(days=TH["ret_days"]): grp.append([])
            grp[-1].append(r); last = r.rts
        for rows in grp:
            if len(rows) >= TH["ret_n"]:
                units = sum(r.quantity for r in rows); val = sum(r.val for r in rows)
                emit("R03", "RETURN_WITHOUT_SALE", sid, None, emp, max(r.rts for r in rows), units, val, "INVESTIGATE",
                     f"{emp} processed {len(rows)} no-receipt returns ({units} units, ${val:,.2f}) at {sid} between {rows[0].rts:%Y-%m-%d} and {rows[-1].rts:%Y-%m-%d} "
                     f"with no original sale and no manager approval; each was restocked into book inventory. Evidence includes {', '.join(r.return_id for r in rows[:3])}.",
                     [x for r in rows for x in (("RETURN", r.return_id, "PRIMARY"), ("MOVEMENT", r.return_movement_id, "PRIMARY"))])

    # ---------------------------------------------------------------- assemble
    if not raw:
        raise RuntimeError("detector produced no alerts")
    df = pd.DataFrame(raw)
    df["created"] = df.anchor.dt.normalize() + pd.Timedelta(days=1, hours=2)      # nightly batch at 02:00
    df["prim"] = df.ev.apply(lambda e: e[0][1])
    df = df.sort_values(["created", "rule_code", "prim"], kind="stable").reset_index(drop=True)
    df["alert_id"] = [f"SHR-2026-{i + 1:06d}" for i in range(len(df))]
    n_ev = df.ev.apply(len)
    sev = np.select([df.value >= 2000, df.value >= 800, df.value >= 250], ["CRITICAL", "HIGH", "MEDIUM"], "LOW")
    base = df.action.map({"INVESTIGATE": 25, "DATA_FIX": 5, "AUTO_CLOSE_BENIGN": 0})
    risk = np.minimum(100, np.round(15 * np.log10(1 + df.value) + 4 * np.minimum(n_ev, 10) + base)).astype(int)
    alerts = pd.DataFrame({
        "alert_id": df.alert_id, "alert_type": df.alert_type, "rule_code": df.rule_code, "store_id": df.store_id, "sku_id": df.sku_id,
        "employee_id": df.employee_id, "created_ts": df.created.dt.strftime("%Y-%m-%d %H:%M:%S"), "estimated_loss_units": df.units,
        "estimated_loss_value": df.value, "severity": sev, "risk_score": risk, "recommended_action": df.action,
        "status": "NEW", "assigned_to_employee_id": None, "reason_text": df.text})
    ev_rows = []
    for aid, evs in zip(df.alert_id, df.ev):
        seen = set()
        for et, eid, role in evs:
            if (et, eid) not in seen:
                seen.add((et, eid)); ev_rows.append((aid, et, eid, role))
    evidence = pd.DataFrame(ev_rows, columns=["alert_id", "evidence_type", "evidence_id", "evidence_role"])
    return alerts, evidence
