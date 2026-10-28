# Evaluation metrics

- Alerts: **735** {'DATA_FIX': 490, 'INVESTIGATE': 187, 'AUTO_CLOSE_BENIGN': 58}
- Precision of INVESTIGATE alerts: **96.8%**
- Recall of planted theft cases (all / detectable by data): **100.0%** / **100.0%**
- Benign traps wrongly escalated: **0 of 33**
- DATA_FIX edge cases routed correctly: **490/490**
- Overall case-level decision accuracy: **100.0%**
- Naive baseline (escalate every count with variance <= -3 units): 208 escalations, precision 51.0%, flags 78 benign-trap counts

## Per issue type

| Issue type | Cases | Detectable | Correct decision | Missed | Accuracy |
|---|---|---|---|---|---|
| ADJUSTMENT_NO_REASON | 60 | 60 | 60 | 0 | 100.0% |
| COUNT_TIMESTAMP_PRECEDES_MOVEMENT | 30 | 30 | 30 | 0 | 100.0% |
| LEGIT_DAMAGE_EVENT | 8 | 8 | 8 | 0 | 100.0% |
| MOVEMENT_WRONG_STORE | 400 | 400 | 400 | 0 | 100.0% |
| REPEATED_ADJUSTMENTS | 10 | 10 | 10 | 0 | 100.0% |
| RETURN_WITHOUT_SALE_ABUSE | 6 | 6 | 6 | 0 | 100.0% |
| TRANSFER_IN_TRANSIT_BOTH_ENDS | 25 | 25 | 25 | 0 | 100.0% |
| UNAUTHORIZED_ADJUSTMENT | 60 | 60 | 60 | 0 | 100.0% |
| UNEXPLAINED_LOSS | 12 | 12 | 12 | 0 | 100.0% |