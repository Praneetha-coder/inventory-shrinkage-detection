"""Builds alert/investigation state-change history (append-only events) from detector output.

Documented rules (not random labels):
  * AUTO_CLOSE_BENIGN  : NEW -> AUTO_CLOSED (system, +1h)
  * DATA_FIX           : NEW -> DATA_FIX_REQUESTED (analyst, +4h) -> DATA_FIXED (+2..10 days) if before the as-of date
  * INVESTIGATE        : NEW -> UNDER_INVESTIGATION (when its investigation opens) -> CLOSED (when it closes)
  * Investigations group INVESTIGATE alerts of the same store and family whose created_ts are <=30 days apart.
  * SLA to close: CRITICAL 3d, HIGH 7d, MEDIUM 14d, LOW 21d (+0..3 days jitter from the seeded RNG); still open at the as-of date otherwise.
  * Outcome = the true cause of the matched ground-truth case (simulated investigator finding): theft pattern -> CONFIRMED_LOSS,
    unauthorised adjustment -> POLICY_BREACH, anything else -> CLEARED_NO_ISSUE. The detector never sees this.
"""
from __future__ import annotations
import numpy as np
import pandas as pd

FAMILY = {"COUNT_VARIANCE": "COUNT", "REPEATED_ADJUSTMENTS": "ADJUSTMENT", "UNAUTHORIZED_ADJUSTMENT": "POLICY",
          "RETURN_WITHOUT_SALE": "RETURN", "DAMAGE_SPIKE": "DAMAGE"}
SLA = {"CRITICAL": 3, "HIGH": 7, "MEDIUM": 14, "LOW": 21}
SEV = {"LOW": 0, "MEDIUM": 1, "HIGH": 2, "CRITICAL": 3}
THEFT = {"UNEXPLAINED_LOSS", "REPEATED_ADJUSTMENTS", "RETURN_WITHOUT_SALE_ABUSE"}


def fmt(ts): return pd.Timestamp(ts).strftime("%Y-%m-%d %H:%M:%S")


def build(cfg, alerts, matches, gt_cases, ops_ids, analyst_ids):
    rng = np.random.default_rng([cfg.seed, 7])
    as_of = pd.Timestamp(cfg.start_date) + pd.Timedelta(days=cfg.as_of_days)
    a = alerts.copy()
    a["created"] = pd.to_datetime(a.created_ts)
    a["assigned_to_employee_id"] = [analyst_ids[i % len(analyst_ids)] for i in range(len(a))]
    a = a.merge(matches, on="alert_id", how="left").merge(gt_cases[["gt_id", "issue_type"]], on="gt_id", how="left")
    ev = []   # (alert_id, from, to, ts, actor, note)
    for r in a.itertuples():
        ev.append((r.alert_id, None, "NEW", r.created, None, f"Raised by rule {r.rule_code}"))
        if r.recommended_action == "AUTO_CLOSE_BENIGN":
            ev.append((r.alert_id, "NEW", "AUTO_CLOSED", r.created + pd.Timedelta(hours=1), None, "Benign explanation found in evidence"))
        elif r.recommended_action == "DATA_FIX":
            t1 = r.created + pd.Timedelta(hours=4)
            ev.append((r.alert_id, "NEW", "DATA_FIX_REQUESTED", t1, r.assigned_to_employee_id, "Data correction requested from store"))
            t2 = t1 + pd.Timedelta(days=int(rng.integers(2, 11)), hours=int(rng.integers(0, 8)))
            if t2 <= as_of:
                ev.append((r.alert_id, "DATA_FIX_REQUESTED", "DATA_FIXED", t2, r.assigned_to_employee_id, "Corrective record posted"))
    # investigations
    inv_rows, inv_alerts, inv_ev = [], [], []
    inv = a[a.recommended_action == "INVESTIGATE"].copy()
    inv["family"] = inv.alert_type.map(FAMILY)
    groups = []
    for (sid, fam), g in inv.sort_values("created").groupby(["store_id", "family"]):
        cur, last = [], None
        for r in g.itertuples():
            if last is not None and r.created - last > pd.Timedelta(days=30):
                groups.append((sid, fam, cur)); cur = []
            cur.append(r); last = r.created
        groups.append((sid, fam, cur))
    groups.sort(key=lambda g: (min(r.created for r in g[2]), g[0], g[1]))
    for i, (sid, fam, rows) in enumerate(groups):
        iid = f"INV-2026-{i + 1:06d}"
        opened = min(r.created for r in rows) + pd.Timedelta(hours=7)
        prio = max((r.severity for r in rows), key=SEV.get)
        owner = ops_ids[i % len(ops_ids)]
        t_prog = opened + pd.Timedelta(days=1)
        base_t = max(t_prog, max(r.created for r in rows) + pd.Timedelta(hours=8))   # cannot close before the last linked alert exists
        t_close = base_t + pd.Timedelta(days=SLA[prio] + int(rng.integers(0, 4)), hours=int(rng.integers(0, 8)))
        status, outcome, cu, cv, closed = "OPEN", None, None, None, None
        ev_i = [(None, "OPEN", opened, owner, "Opened from escalated alert(s)")]
        if t_prog <= as_of:
            status = "IN_PROGRESS"; ev_i.append(("OPEN", "IN_PROGRESS", t_prog, owner, "Evidence review started"))
        if t_close <= as_of:
            status, closed = "CLOSED", t_close
            issues = {r.issue_type for r in rows if isinstance(r.issue_type, str)}
            hit = [r for r in rows if r.issue_type in THEFT]
            if hit:
                outcome, cu, cv = "CONFIRMED_LOSS", int(sum(r.estimated_loss_units for r in hit)), round(float(sum(r.estimated_loss_value for r in hit)), 2)
            elif "UNAUTHORIZED_ADJUSTMENT" in issues:
                outcome = "POLICY_BREACH"
            else:
                outcome = "CLEARED_NO_ISSUE"
            ev_i.append(("IN_PROGRESS", "CLOSED", t_close, owner, f"Finding: {outcome}"))
        exposure = sum(r.estimated_loss_value for r in rows)
        inv_rows.append(dict(investigation_id=iid, store_id=sid, alert_family=fam, opened_ts=fmt(opened), assigned_to_employee_id=owner,
                             priority=prio, status=status, outcome=outcome, confirmed_loss_units=cu, confirmed_loss_value=cv,
                             closed_ts=fmt(closed) if closed is not None else None,
                             summary=f"{fam} case at {sid}: {len(rows)} alert(s), estimated exposure ${exposure:,.2f}"))
        for r in rows:
            inv_alerts.append((iid, r.alert_id))
            ev.append((r.alert_id, "NEW", "UNDER_INVESTIGATION", max(opened, r.created + pd.Timedelta(hours=7)), owner, f"Escalated to {iid}"))
            if status == "CLOSED":
                ev.append((r.alert_id, "UNDER_INVESTIGATION", "CLOSED", closed, owner, f"{iid} closed: {outcome}"))
        for k, (f_, t_, ts_, ac, nt) in enumerate(ev_i):
            inv_ev.append((iid, f_, t_, ts_, ac, nt))
    # events -> tables with ids in chronological order
    ae = pd.DataFrame(ev, columns=["alert_id", "from_status", "to_status", "ts", "actor_employee_id", "note"])
    ae["seq"] = np.arange(len(ae))
    ae = ae.sort_values(["ts", "alert_id", "seq"], kind="stable").reset_index(drop=True)
    ae.insert(0, "alert_event_id", [f"ALE-2026-{i + 1:06d}" for i in range(len(ae))])
    ae["event_ts"] = ae.ts.dt.strftime("%Y-%m-%d %H:%M:%S")
    last = ae.sort_values(["ts", "seq"]).groupby("alert_id").to_status.last()
    a["status"] = a.alert_id.map(last)
    ie = pd.DataFrame(inv_ev, columns=["investigation_id", "from_status", "to_status", "ts", "actor_employee_id", "note"])
    ie["seq"] = np.arange(len(ie))
    ie = ie.sort_values(["ts", "investigation_id", "seq"], kind="stable").reset_index(drop=True)
    ie.insert(0, "investigation_event_id", [f"IVE-2026-{i + 1:06d}" for i in range(len(ie))])
    ie["event_ts"] = ie.ts.dt.strftime("%Y-%m-%d %H:%M:%S")
    cols = list(alerts.columns)
    return dict(
        shrinkage_alerts=a[cols],
        alert_status_events=ae[["alert_event_id", "alert_id", "from_status", "to_status", "event_ts", "actor_employee_id", "note"]],
        investigations=pd.DataFrame(inv_rows),
        investigation_alerts=pd.DataFrame(inv_alerts, columns=["investigation_id", "alert_id"]),
        investigation_events=ie[["investigation_event_id", "investigation_id", "from_status", "to_status", "event_ts", "actor_employee_id", "note"]])
