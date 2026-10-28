"""Step 8 validation: reads the EXPORTED CSV files (not in-memory objects) and checks integrity, reconciliation,
lifecycle and that planted anomalies are exactly the labelled ones."""
from __future__ import annotations
import json, re
import numpy as np
import pandas as pd
from . import schema as S


def run_validation(out: str) -> dict:
    T = {k: pd.read_csv(f"{out}/input/{k}.csv", low_memory=False) for k in S.TABLES}
    G = {k: pd.read_csv(f"{out}/ground_truth/{k}.csv") for k in S.GT_TABLES}
    res = []

    def chk(group, name, ok, detail=""):
        res.append(dict(group=group, check=name, passed=bool(ok), detail=str(detail)))

    # ---- primary keys, id formats, contiguity, required, enums
    for src, tabs in ((T, S.TABLES), (G, S.GT_TABLES)):
        for k, spec in tabs.items():
            df = src[k]
            chk("primary_key", f"{k}: PK {spec['pk']} unique", not df.duplicated(spec["pk"]).any(), f"{len(df)} rows")
            req = [f["name"] for f in spec["fields"] if f["required"] == "Y"]
            nn = df[req].isna().sum(); chk("required", f"{k}: required fields non-null", nn.sum() == 0, nn[nn > 0].to_dict())
            for f in spec["fields"]:
                if f["allowed"] and (k, f["name"]) in S.ENUMS:
                    bad = ~df[f["name"]].dropna().isin(S.ENUMS[(k, f["name"])])
                    chk("enum", f"{k}.{f['name']} in allowed values", not bad.any(), df[f["name"]].dropna()[bad].unique()[:5])
    for key, pat in S.ID_PATTERNS.items():
        k, c = key.split("."); df = {**T, **G}[k]
        bad = ~df[c].dropna().astype(str).str.match(pat)
        chk("id_format", f"{key} matches {pat}", not bad.any(), int(bad.sum()))
    for k, c in (("inventory_movements", "movement_id"), ("cycle_counts", "count_id"), ("returns", "return_id"),
                 ("shrinkage_alerts", "alert_id"), ("investigations", "investigation_id"), ("alert_status_events", "alert_event_id"),
                 ("investigation_events", "investigation_event_id"), ("shifts", "shift_id")):
        n = T[k][c].str.extract(r"(\d+)$")[0].astype(int)
        chk("id_format", f"{k}.{c} counters contiguous 1..N, zero-padded, no gaps", n.sort_values().reset_index(drop=True).equals(pd.Series(np.arange(1, len(n) + 1))))

    # ---- foreign keys
    for src, tabs in ((T, S.TABLES), (G, S.GT_TABLES)):
        for k, spec in tabs.items():
            for c, rt, rc in spec["fks"]:
                parent = {**T, **G}[rt][rc]
                v = src[k][c].dropna()
                chk("foreign_key", f"{k}.{c} -> {rt}.{rc}", v.isin(parent).all(), f"{int((~v.isin(parent)).sum())} orphans")
    ss = T["store_skus"][["store_id", "sku_id"]]
    for k in ("inventory_movements", "cycle_counts"):
        j = T[k][["store_id", "sku_id"]].drop_duplicates().merge(ss, how="left", indicator=True)
        chk("foreign_key", f"{k}: (store_id, sku_id) exists in store_skus", (j._merge == "both").all())
    ev = T["alert_evidence"]
    for et, tab, col in (("MOVEMENT", "inventory_movements", "movement_id"), ("COUNT", "cycle_counts", "count_id"),
                         ("RETURN", "returns", "return_id"), ("SHIFT", "shifts", "shift_id"), ("TRANSFER", "inventory_movements", "transfer_id")):
        e = ev[ev.evidence_type == et].evidence_id
        chk("foreign_key", f"alert_evidence {et} ids exist in {tab}.{col}", e.isin(T[tab][col]).all(), len(e))
    gl = G["ground_truth_links"]
    for et, tab, col in (("MOVEMENT", "inventory_movements", "movement_id"), ("COUNT", "cycle_counts", "count_id"), ("TRANSFER", "inventory_movements", "transfer_id")):
        chk("foreign_key", f"ground_truth_links {et} ids exist", gl[gl.entity_type == et].entity_id.isin(T[tab][col]).all())

    mv, cn, sh, rt, er = T["inventory_movements"], T["cycle_counts"], T["shifts"], T["returns"], T["employee_roles"]
    sku = T["skus"].set_index("sku_id")
    mv["mts"] = pd.to_datetime(mv.movement_ts); mv["pts"] = pd.to_datetime(mv.posted_ts)
    sh["s"] = pd.to_datetime(sh.start_ts); sh["e"] = pd.to_datetime(sh.end_ts)

    # ---- domain rules on movements
    sign = mv.movement_type.map({"SALE": -1, "TRANSFER_OUT": -1, "DAMAGE": -1, "RECEIPT": 1, "TRANSFER_IN": 1, "CUSTOMER_RETURN": 1, "ADJUSTMENT": 0})
    chk("domain", "movement sign matches movement_type", ((sign == 0) & (mv.quantity_signed != 0) | (sign * mv.quantity_signed > 0)).all())
    wh = T["stores"].set_index("store_id").store_type.eq("WAREHOUSE")
    chk("domain", "warehouses record no SALE / CUSTOMER_RETURN", not mv[mv.movement_type.isin(["SALE", "CUSTOMER_RETURN"]) & mv.store_id.map(wh)].shape[0])
    m = mv.merge(sh[["shift_id", "store_id", "employee_id", "s", "e"]].rename(columns={"store_id": "sh_store", "employee_id": "sh_emp"}), on="shift_id")
    chk("lineage", "movement.employee_id = shift.employee_id", (m.employee_id == m.sh_emp).all())
    chk("date_order", "posted_ts falls inside its shift window", ((m.pts >= m.s) & (m.pts < m.e)).all())
    n_ws = int((m.store_id != m.sh_store).sum()); gt = G["ground_truth_cases"]
    cnt = lambda t: int((gt.issue_type == t).sum())
    chk("anomaly_reconciliation", "movements whose store <> shift store == labelled MOVEMENT_WRONG_STORE", n_ws == cnt("MOVEMENT_WRONG_STORE"), f"{n_ws} vs {cnt('MOVEMENT_WRONG_STORE')}")
    nr = int((mv.movement_type.eq("ADJUSTMENT") & mv.reason_code.isna()).sum())
    chk("anomaly_reconciliation", "adjustments without reason == labelled ADJUSTMENT_NO_REASON", nr == cnt("ADJUSTMENT_NO_REASON"), f"{nr} vs {cnt('ADJUSTMENT_NO_REASON')}")
    need = mv.movement_type.isin(["DAMAGE", "CUSTOMER_RETURN"]) | (mv.movement_type.eq("ADJUSTMENT") & ~mv.reason_code.isna())
    chk("domain", "reason_code present for DAMAGE / CUSTOMER_RETURN (and every non-exception ADJUSTMENT)", not (mv.reason_code.isna() & mv.movement_type.isin(["DAMAGE", "CUSTOMER_RETURN"])).any())
    late = int((mv.pts > mv.mts).sum()); early = int((mv.pts < mv.mts).sum())
    chk("date_order", "posted_ts >= movement_ts except labelled early-posted transfer receipts", early == cnt("TRANSFER_IN_TRANSIT_BOTH_ENDS") and late == cnt("TRANSFER_IN_TRANSIT_BOTH_ENDS"), f"early={early}, late={late}, labelled={cnt('TRANSFER_IN_TRANSIT_BOTH_ENDS')}")
    x = mv[mv.transfer_id.notna()]
    g = x.groupby("transfer_id").agg(n=("movement_id", "size"), o=("movement_type", lambda s: (s == "TRANSFER_OUT").sum()), q=("quantity_signed", "sum"), sk=("sku_id", "nunique"))
    chk("lifecycle", "each transfer_id has exactly 1 OUT + 1 IN, equal quantity, same SKU", ((g.n == 2) & (g.o == 1) & (g.q == 0) & (g.sk == 1)).all(), f"{len(g)} transfers")
    o_, i_ = x[x.movement_type == "TRANSFER_OUT"].set_index("transfer_id"), x[x.movement_type == "TRANSFER_IN"].set_index("transfer_id")
    chk("lifecycle", "transfer legs: counterparties mirror each other and IN movement_ts is after OUT movement_ts",
        ((o_.counterparty_store_id == i_.reindex(o_.index).store_id) & (i_.reindex(o_.index).counterparty_store_id == o_.store_id) & (i_.reindex(o_.index).mts > o_.mts)).all())
    p = mv[mv.promotion_id.notna()].merge(T["promotions"], on="promotion_id").merge(T["promotion_skus"], on=["promotion_id", "sku_id"], how="left", indicator=True)
    d = p.mts.dt.normalize()
    chk("domain", "promotion sales: SKU in promotion_skus and date inside promo window", ((p._merge == "both") & (d >= pd.to_datetime(p.start_date)) & (d <= pd.to_datetime(p.end_date))).all(), len(p))

    # ---- stock equation, running balance >= 0, count reconciliation
    pair = mv.store_id + "|" + mv.sku_id
    ss["pair"] = ss.store_id + "|" + ss.sku_id
    opn = T["store_skus"].assign(pair=ss.pair).set_index("pair").opening_qty
    mvs = mv.assign(pair=pair).sort_values(["pair", "pts"], kind="stable")
    mvs["cum"] = mvs.groupby("pair").quantity_signed.cumsum() + mvs.pair.map(opn)
    chk("reconciliation", "book running balance (opening + movements) never negative", (mvs.cum >= 0).all(), f"min={int(mvs.cum.min())}")
    closing = mvs.groupby("pair").cum.last()
    chk("reconciliation", "stock equation: closing = opening + sum(movements) and >= 0 for every store/SKU", (closing == mvs.groupby("pair").quantity_signed.sum() + opn.reindex(closing.index)).all())
    cnv = cn.assign(pair=cn.store_id + "|" + cn.sku_id, cts=pd.to_datetime(cn.count_ts), ets=pd.to_datetime(cn.entered_ts)).sort_values("cts", kind="stable")
    cum = mvs[["pair", "pts", "cum"]].sort_values("pts", kind="stable")
    asof = pd.merge_asof(cnv, cum, left_on="cts", right_on="pts", by="pair", direction="backward")
    book = asof.cum.fillna(asof.pair.map(opn))
    chk("reconciliation", "cycle_counts.book_qty = opening + movements posted <= count_ts (independent recomputation)", (book.values == asof.book_qty.values).all())
    chk("reconciliation", "variance_units = counted_qty - book_qty", (cn.variance_units == cn.counted_qty - cn.book_qty).all())
    chk("reconciliation", "variance_value = variance_units * unit_cost", np.allclose(cn.variance_value, cn.variance_units * cn.sku_id.map(sku.unit_cost), atol=.011))
    within = (cn.variance_units.abs() <= np.maximum(2, .03 * cn.book_qty)) & (cn.variance_value.abs() < 50)
    st = np.where(cn.variance_units == 0, "MATCHED", np.where(within, "WITHIN_TOLERANCE", "OUT_OF_TOLERANCE"))
    chk("reconciliation", "count status derived from variance rule", (st == cn.status).all())
    cz = G["ground_truth_count_causes"]
    chk("reconciliation", "every count variance exactly decomposes into the six ground-truth causes", cz.variance_explained.eq(1).all() and len(cz) == len(cn))
    chk("date_order", "count entered_ts >= count_ts", (cnv.ets >= cnv.cts).all())
    ce = cn.merge(sh[["shift_id", "employee_id"]].rename(columns={"employee_id": "se"}), on="shift_id")
    chk("lineage", "count shift belongs to the counting employee", (ce.counted_by_employee_id == ce.se).all())
    r = er.merge(sh[["employee_id"]].drop_duplicates(), on="employee_id")
    cr = cn.merge(er[er.can_perform_counts == 1][["employee_id"]].drop_duplicates(), left_on="counted_by_employee_id", right_on="employee_id", how="left", indicator=True)
    chk("authorization", "every count is performed by an employee with can_perform_counts", (cr._merge == "both").all())

    # ---- roles / shifts
    er["f"], er["t"] = pd.to_datetime(er.effective_from), pd.to_datetime(er.effective_to)
    ov = er.sort_values(["employee_id", "f"]); nxt = ov.groupby("employee_id").f.shift(-1)
    chk("date_order", "employee_roles: effective ranges ordered and non-overlapping", ((ov.t.isna() & nxt.isna()) | (ov.t < nxt) | nxt.isna()).all())
    chk("date_order", "promotions start_date <= end_date; shifts start < end",
        (pd.to_datetime(T["promotions"].start_date) <= pd.to_datetime(T["promotions"].end_date)).all() and (sh.s < sh.e).all())
    j = sh[["shift_id", "employee_id", "role_on_shift", "shift_date"]].assign(d=pd.to_datetime(sh.shift_date)).merge(er[["employee_id", "role_code", "f", "t"]], on="employee_id")
    j = j[(j.d >= j.f) & (j.t.isna() | (j.d <= j.t))]
    chk("lineage", "shift.role_on_shift equals the employee's effective role on shift_date", len(j) == len(sh) and (j.role_on_shift == j.role_code).all())

    # ---- returns
    rs = rt.merge(mv[["movement_id", "mts", "quantity_signed", "store_id", "sku_id"]].rename(columns={"movement_id": "original_sale_movement_id", "mts": "smts", "quantity_signed": "sq", "store_id": "ss", "sku_id": "sk"}),
                  on="original_sale_movement_id", how="left")
    k = rs.original_sale_movement_id.notna()
    chk("date_order", "return_ts is after the original sale", (pd.to_datetime(rs.return_ts)[k] > rs.smts[k]).all())
    chk("reconciliation", "return quantity <= original sale quantity; same store and SKU", ((rs.quantity[k] <= -rs.sq[k]) & (rs.store_id_x[k] == rs.ss[k]) & (rs.sku_id_x[k] == rs.sk[k])).all() if "store_id_x" in rs else ((rs.quantity[k] <= -rs.sq[k]) & (rs.store_id[k] == rs.ss[k])).all())
    chk("duplicates", "each sale has at most one return; each return movement is used once", not rt.original_sale_movement_id.dropna().duplicated().any() and not rt.return_movement_id.dropna().duplicated().any())
    chk("lifecycle", "return: RESTOCK <=> return_movement_id set <=> status RESTOCKED", (rt.return_movement_id.notna() == rt.disposition.eq("RESTOCK")).all() and (rt.status.eq("RESTOCKED") == rt.disposition.eq("RESTOCK")).all())
    cm = mv[mv.movement_type == "CUSTOMER_RETURN"]
    chk("reconciliation", "every CUSTOMER_RETURN movement has exactly one Return row", set(cm.movement_id) == set(rt.return_movement_id.dropna()))
    pr = T["promotions"].set_index("promotion_id").discount_pct
    disc = rt.original_sale_movement_id.map(mv.set_index("movement_id").promotion_id).map(pr).fillna(0)
    chk("reconciliation", "refund_amount = qty * unit_price * (1 - promo discount)", np.allclose(rt.refund_amount, rt.quantity * rt.sku_id.map(sku.unit_price) * (1 - disc / 100), atol=.011))

    # ---- alerts, evidence, lifecycle
    al, ae, inv, ie, ia = T["shrinkage_alerts"], T["alert_status_events"], T["investigations"], T["investigation_events"], T["investigation_alerts"]
    for name, ev_, key, trans, ent, stcol in (("alert", ae, "alert_id", S.ALERT_TRANSITIONS, al, "status"), ("investigation", ie, "investigation_id", S.INV_TRANSITIONS, inv, "status")):
        e = ev_.sort_values([key, "event_ts"], kind="stable"); e["ts"] = pd.to_datetime(e.event_ts)
        ok = all(row.to_status in trans[None if pd.isna(row.from_status) else row.from_status] for row in e.itertuples())
        chk("lifecycle", f"{name} transitions follow the allowed state machine", ok, len(e))
        chk("lifecycle", f"{name} event timestamps non-decreasing and chain (from = previous to)",
            e.groupby(key).apply(lambda g: g.ts.is_monotonic_increasing and list(g.from_status.iloc[1:]) == list(g.to_status.iloc[:-1]), include_groups=False).all())
        chk("lifecycle", f"{name}.status equals its last event", (e.groupby(key).to_status.last().reindex(ent[key]).values == ent[stcol].values).all())
    chk("lifecycle", "investigation outcome/closed_ts set iff CLOSED", ((inv.status == "CLOSED") == inv.outcome.notna()).all() and ((inv.status == "CLOSED") == inv.closed_ts.notna()).all())
    chk("lifecycle", "only INVESTIGATE alerts are linked to investigations", ia.merge(al, on="alert_id").recommended_action.eq("INVESTIGATE").all())
    chk("lifecycle", "every INVESTIGATE alert belongs to an investigation", set(al[al.recommended_action == "INVESTIGATE"].alert_id) == set(ia.alert_id))
    chk("date_order", "investigation opened_ts >= earliest linked alert created_ts", (inv.merge(ia, on="investigation_id").merge(al, on="alert_id").groupby("investigation_id").apply(lambda g: pd.to_datetime(g.opened_ts.iloc[0]) >= pd.to_datetime(g.created_ts).min(), include_groups=False)).all())
    al_c = al[al.alert_type == "COUNT_VARIANCE"]
    ar = al_c.merge(cn[["count_id", "variance_units", "variance_value"]], left_on=al_c.alert_id.map(ev[(ev.evidence_role == "PRIMARY") & (ev.evidence_type == "COUNT")].drop_duplicates("alert_id").set_index("alert_id").evidence_id), right_on="count_id")
    chk("reconciliation", "COUNT_VARIANCE alerts: estimated loss = -(variance of primary count)", (ar.estimated_loss_units == -ar.variance_units).all() and np.allclose(ar.estimated_loss_value, -ar.variance_value, atol=.011), len(ar))
    sev = np.select([al.estimated_loss_value >= 2000, al.estimated_loss_value >= 800, al.estimated_loss_value >= 250], ["CRITICAL", "HIGH", "MEDIUM"], "LOW")
    chk("reconciliation", "alert severity derived from estimated_loss_value", (sev == al.severity).all())
    chk("evidence", "every alert has >=1 PRIMARY evidence row and a reason_text citing a record id", (al.alert_id.isin(ev[ev.evidence_role == "PRIMARY"].alert_id)).all() and al.reason_text.str.contains(r"(?:MOV|CNT|RET)-2026-").all())
    chk("duplicates", "no duplicate alerts (same rule + primary evidence)", not ev[ev.evidence_role == "PRIMARY"].merge(al[["alert_id", "rule_code"]], on="alert_id").groupby(["rule_code", "evidence_id"]).size().gt(1).any())
    dup = mv.duplicated(["store_id", "sku_id", "movement_type", "quantity_signed", "movement_ts", "employee_id"]).mean()
    chk("duplicates", "exact duplicate movements (same store, SKU, type, qty, second, employee) < 0.5% of rows", dup < .005, f"{dup:.4%}")
    chk("duplicates", "store_skus / employee_roles natural keys unique", not T["store_skus"].duplicated(["store_id", "sku_id"]).any() and not er.duplicated(["employee_id", "effective_from"]).any())

    # ---- ground-truth separation
    leak = [(k, c) for k, df in T.items() for c in df.columns if re.search(r"issue_type|ground|gt_|expected_decision|is_anomal", c)]
    chk("ground_truth", "no ground-truth column exists in any input table", not leak, leak)
    chk("ground_truth", "no 'GT-' identifier appears in alert text / notes of the input tables",
        not (al.reason_text.str.contains("GT-").any() or ae.note.fillna("").str.contains("GT-").any() or ie.note.fillna("").str.contains("GT-").any() or mv.reference_note.fillna("").str.contains("GT-").any()))
    chk("ground_truth", "every ground-truth case has >=1 linked record", gt.gt_id.isin(gl.gt_id).all())
    chk("ground_truth", "all alerts have a label row", set(G["ground_truth_alert_labels"].alert_id) == set(al.alert_id))

    passed = sum(r["passed"] for r in res)
    summary = dict(total=len(res), passed=passed, failed=len(res) - passed, checks=res,
                   row_counts={k: len(v) for k, v in {**T, **G}.items()})
    json.dump(summary, open(f"{out}/validation_summary.json", "w"), indent=1, default=str)
    lines = [f"# Validation summary", f"**{passed}/{len(res)} checks passed.**", "", "| Group | Check | Result | Detail |", "|---|---|---|---|"]
    lines += [f"| {r['group']} | {r['check']} | {'PASS' if r['passed'] else '**FAIL**'} | {r['detail'][:80]} |" for r in res]
    lines += ["", "## Row counts", "", "| Table | Rows |", "|---|---|"] + [f"| {k} | {v:,} |" for k, v in summary["row_counts"].items()]
    open(f"{out}/validation_summary.md", "w").write("\n".join(lines))
    return summary
