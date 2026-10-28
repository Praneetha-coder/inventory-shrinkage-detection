# Evaluation metrics

- Alerts: **72** {'INVESTIGATE': 40, 'DATA_FIX': 21, 'AUTO_CLOSE_BENIGN': 11}
- Precision of INVESTIGATE alerts: **100.0%**
- Recall of planted theft cases (all / detectable by data): **100.0%** / **100.0%**
- Benign traps wrongly escalated: **0 of 7**
- DATA_FIX edge cases routed correctly: **21/21**
- Overall case-level decision accuracy: **100.0%**
- Naive baseline (escalate every count with variance <= -3 units): 43 escalations, precision 69.8%, flags 13 benign-trap counts

## Per issue type

| Issue type | Cases | Detectable | Correct decision | Missed | Accuracy |
|---|---|---|---|---|---|
| ADJUSTMENT_NO_REASON | 8 | 8 | 8 | 0 | 100.0% |
| COUNT_TIMESTAMP_PRECEDES_MOVEMENT | 5 | 5 | 5 | 0 | 100.0% |
| LEGIT_DAMAGE_EVENT | 3 | 3 | 3 | 0 | 100.0% |
| MOVEMENT_WRONG_STORE | 8 | 8 | 8 | 0 | 100.0% |
| REPEATED_ADJUSTMENTS | 3 | 3 | 3 | 0 | 100.0% |
| RETURN_WITHOUT_SALE_ABUSE | 2 | 2 | 2 | 0 | 100.0% |
| TRANSFER_IN_TRANSIT_BOTH_ENDS | 4 | 4 | 4 | 0 | 100.0% |
| UNAUTHORIZED_ADJUSTMENT | 5 | 5 | 5 | 0 | 100.0% |
| UNEXPLAINED_LOSS | 3 | 3 | 3 | 0 | 100.0% |