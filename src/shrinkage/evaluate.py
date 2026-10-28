"""Evaluation metrics: detector decisions vs ground truth, plus a naive 'every negative variance is theft' baseline."""
from __future__ import annotations
import json
import numpy as np
import pandas as pd


def run_evaluation(out: str) -> dict:
    al = pd.read_csv(f"{out}/input/shrinkage_alerts.csv"); cn = pd.read_csv(f"{out}/input/cycle_counts.csv")
    inv = pd.read_csv(f"{out}/input/investigations.csv")
    gc = pd.read_csv(f"{out}/ground_truth/ground_truth_cases.csv"); gl = pd.read_csv(f"{out}/ground_truth/ground_truth_links.csv")
    lb = pd.read_csv(f"{out}/ground_truth/ground_truth_alert_labels.csv")
    rank = {"INVESTIGATE": 3, "DATA_FIX": 2, "AUTO_CLOSE_BENIGN": 1}
    x = lb.dropna(subset=["gt_id"]).assign(r=lambda d: d.predicted_decision.map(rank)).sort_values("r").groupby("gt_id").predicted_decision.last()
    gc["predicted_decision"] = gc.gt_id.map(x).fillna("MISSED")
    gc["correct"] = gc.predicted_decision == gc.expected_decision
    per = gc.groupby("issue_type").agg(cases=("gt_id", "size"), detectable=("detectable", "sum"), correct=("correct", "sum"),
                                       missed=("predicted_decision", lambda s: (s == "MISSED").sum())).reset_index()
    per["decision_accuracy"] = (per.correct / per.cases).round(3)
    theft = gc[gc.expected_decision == "INVESTIGATE"]
    benign = gc[gc.expected_decision == "AUTO_CLOSE_BENIGN"]
    inv_alerts = lb[lb.predicted_decision == "INVESTIGATE"]
    # naive baseline: escalate every count with variance <= -3 units
    cl = gl[gl.entity_type == "COUNT"].merge(gc[["gt_id", "expected_decision", "issue_type"]], on="gt_id")
    naive = cn[cn.variance_units <= -3]
    tp_n = naive.count_id.isin(cl[cl.expected_decision == "INVESTIGATE"].entity_id).sum()
    fp_benign = naive.count_id.isin(cl[cl.expected_decision != "INVESTIGATE"].entity_id).sum()
    theft_counts = cl[cl.expected_decision == "INVESTIGATE"].entity_id.nunique()
    m = dict(
        alerts_total=len(al), alerts_by_action=al.recommended_action.value_counts().to_dict(),
        alert_labels=lb.label.value_counts().to_dict(),
        investigate_alert_precision=round(float((inv_alerts.label == "TRUE_POSITIVE").mean()), 4),
        theft_case_recall_all=round(float((theft.predicted_decision == "INVESTIGATE").mean()), 4),
        theft_case_recall_detectable=round(float((theft[theft.detectable == 1].predicted_decision == "INVESTIGATE").mean()), 4),
        benign_cases_wrongly_escalated=int((benign.predicted_decision == "INVESTIGATE").sum()), benign_cases=len(benign),
        data_fix_cases_correct=f"{int(gc[gc.expected_decision == 'DATA_FIX'].correct.sum())}/{int((gc.expected_decision == 'DATA_FIX').sum())}",
        overall_case_decision_accuracy=round(float(gc.correct.mean()), 4),
        loss_value_flagged_for_investigation=round(float(al[al.recommended_action == "INVESTIGATE"].estimated_loss_value.sum()), 2),
        true_theft_loss_value=round(float(theft.true_loss_value.sum()), 2),
        investigations=dict(total=len(inv), by_status=inv.status.value_counts().to_dict(), by_outcome=inv.outcome.value_counts().to_dict(),
                            confirmed_loss_value=round(float(inv.confirmed_loss_value.sum()), 2)),
        naive_baseline=dict(rule="escalate every count with variance <= -3 units", escalations=len(naive),
                            precision_vs_theft=round(float(tp_n / max(1, len(naive))), 4),
                            recall_of_theft_counts=round(float(tp_n / max(1, theft_counts)), 4),
                            benign_trap_counts_flagged=int(fp_benign)),
        per_issue_type=per.to_dict("records"))
    json.dump(m, open(f"{out}/evaluation_metrics.json", "w"), indent=1, default=str)
    L = ["# Evaluation metrics", "", f"- Alerts: **{m['alerts_total']}** {m['alerts_by_action']}",
         f"- Precision of INVESTIGATE alerts: **{m['investigate_alert_precision']:.1%}**",
         f"- Recall of planted theft cases (all / detectable by data): **{m['theft_case_recall_all']:.1%}** / **{m['theft_case_recall_detectable']:.1%}**",
         f"- Benign traps wrongly escalated: **{m['benign_cases_wrongly_escalated']} of {m['benign_cases']}**",
         f"- DATA_FIX edge cases routed correctly: **{m['data_fix_cases_correct']}**",
         f"- Overall case-level decision accuracy: **{m['overall_case_decision_accuracy']:.1%}**",
         f"- Naive baseline ({m['naive_baseline']['rule']}): {m['naive_baseline']['escalations']} escalations, precision {m['naive_baseline']['precision_vs_theft']:.1%}, "
         f"flags {m['naive_baseline']['benign_trap_counts_flagged']} benign-trap counts", "", "## Per issue type", "",
         "| Issue type | Cases | Detectable | Correct decision | Missed | Accuracy |", "|---|---|---|---|---|---|"]
    L += [f"| {r['issue_type']} | {r['cases']} | {r['detectable']} | {r['correct']} | {r['missed']} | {r['decision_accuracy']:.1%} |" for r in m["per_issue_type"]]
    open(f"{out}/evaluation_metrics.md", "w").write("\n".join(L))
    return m
