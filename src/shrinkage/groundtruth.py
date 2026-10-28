"""Links alerts to ground-truth cases by evidence overlap and labels each alert.
Used only AFTER detection, for labels / evaluation / simulated investigation outcomes."""
from __future__ import annotations
import numpy as np
import numpy as np
import pandas as pd

PRIORITY = {"INVESTIGATE": 3, "DATA_FIX": 2, "AUTO_CLOSE_BENIGN": 1}


def match_alerts(alerts: pd.DataFrame, evidence: pd.DataFrame, gt_links: pd.DataFrame) -> pd.DataFrame:
    """alert_id -> gt_id (first overlapping case on PRIMARY / EXPLAINING evidence)."""
    lk = gt_links[gt_links.entity_type.isin(["MOVEMENT", "COUNT"])]
    m = evidence[evidence.evidence_role.isin(["PRIMARY", "EXPLAINING"])].merge(
        lk, left_on=["evidence_type", "evidence_id"], right_on=["entity_type", "entity_id"])
    first = m.sort_values(["alert_id", "gt_id"]).drop_duplicates("alert_id")[["alert_id", "gt_id"]]
    return alerts[["alert_id"]].merge(first, on="alert_id", how="left")


def label_alerts(alerts, matches, gt_cases) -> pd.DataFrame:
    x = alerts[["alert_id", "recommended_action"]].merge(matches, on="alert_id").merge(
        gt_cases[["gt_id", "expected_decision"]], on="gt_id", how="left").rename(columns={"recommended_action": "predicted_decision"})
    cond = [x.gt_id.isna() & (x.predicted_decision == "INVESTIGATE"), x.gt_id.isna(), x.predicted_decision == x.expected_decision]
    x["label"] = np.select(cond, ["FALSE_POSITIVE", "SPURIOUS_NON_ESCALATED", "TRUE_POSITIVE"], "MISCLASSIFIED")
    return x[["alert_id", "gt_id", "expected_decision", "predicted_decision", "label"]]
