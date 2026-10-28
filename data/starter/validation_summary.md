# Validation summary
**203/203 checks passed.**

| Group | Check | Result | Detail |
|---|---|---|---|
| primary_key | stores: PK ['store_id'] unique | PASS | 10 rows |
| required | stores: required fields non-null | PASS | {} |
| enum | stores.store_type in allowed values | PASS | <StringArray>
[]
Length: 0, dtype: str |
| enum | stores.store_format in allowed values | PASS | <StringArray>
[]
Length: 0, dtype: str |
| enum | stores.region in allowed values | PASS | <StringArray>
[]
Length: 0, dtype: str |
| enum | stores.status in allowed values | PASS | <StringArray>
[]
Length: 0, dtype: str |
| primary_key | skus: PK ['sku_id'] unique | PASS | 500 rows |
| required | skus: required fields non-null | PASS | {} |
| enum | skus.category in allowed values | PASS | <StringArray>
[]
Length: 0, dtype: str |
| enum | skus.status in allowed values | PASS | <StringArray>
[]
Length: 0, dtype: str |
| primary_key | store_skus: PK ['store_id', 'sku_id'] unique | PASS | 2200 rows |
| required | store_skus: required fields non-null | PASS | {} |
| enum | store_skus.status in allowed values | PASS | <StringArray>
[]
Length: 0, dtype: str |
| primary_key | employees: PK ['employee_id'] unique | PASS | 84 rows |
| required | employees: required fields non-null | PASS | {} |
| enum | employees.employment_status in allowed values | PASS | <StringArray>
[]
Length: 0, dtype: str |
| primary_key | employee_roles: PK ['employee_role_id'] unique | PASS | 96 rows |
| required | employee_roles: required fields non-null | PASS | {} |
| enum | employee_roles.role_code in allowed values | PASS | <StringArray>
[]
Length: 0, dtype: str |
| primary_key | shifts: PK ['shift_id'] unique | PASS | 10860 rows |
| required | shifts: required fields non-null | PASS | {} |
| enum | shifts.shift_type in allowed values | PASS | <StringArray>
[]
Length: 0, dtype: str |
| enum | shifts.role_on_shift in allowed values | PASS | <StringArray>
[]
Length: 0, dtype: str |
| enum | shifts.status in allowed values | PASS | <StringArray>
[]
Length: 0, dtype: str |
| primary_key | promotions: PK ['promotion_id'] unique | PASS | 10 rows |
| required | promotions: required fields non-null | PASS | {} |
| enum | promotions.status in allowed values | PASS | <StringArray>
[]
Length: 0, dtype: str |
| primary_key | promotion_skus: PK ['promotion_id', 'sku_id'] unique | PASS | 50 rows |
| required | promotion_skus: required fields non-null | PASS | {} |
| primary_key | inventory_movements: PK ['movement_id'] unique | PASS | 20000 rows |
| required | inventory_movements: required fields non-null | PASS | {} |
| enum | inventory_movements.movement_type in allowed values | PASS | <StringArray>
[]
Length: 0, dtype: str |
| enum | inventory_movements.reason_code in allowed values | PASS | <StringArray>
[]
Length: 0, dtype: str |
| primary_key | cycle_counts: PK ['count_id'] unique | PASS | 500 rows |
| required | cycle_counts: required fields non-null | PASS | {} |
| enum | cycle_counts.count_type in allowed values | PASS | <StringArray>
[]
Length: 0, dtype: str |
| enum | cycle_counts.status in allowed values | PASS | <StringArray>
[]
Length: 0, dtype: str |
| primary_key | returns: PK ['return_id'] unique | PASS | 1416 rows |
| required | returns: required fields non-null | PASS | {} |
| enum | returns.reason_code in allowed values | PASS | <StringArray>
[]
Length: 0, dtype: str |
| enum | returns.disposition in allowed values | PASS | <StringArray>
[]
Length: 0, dtype: str |
| enum | returns.status in allowed values | PASS | <StringArray>
[]
Length: 0, dtype: str |
| primary_key | shrinkage_alerts: PK ['alert_id'] unique | PASS | 72 rows |
| required | shrinkage_alerts: required fields non-null | PASS | {} |
| enum | shrinkage_alerts.alert_type in allowed values | PASS | <StringArray>
[]
Length: 0, dtype: str |
| enum | shrinkage_alerts.severity in allowed values | PASS | <StringArray>
[]
Length: 0, dtype: str |
| enum | shrinkage_alerts.recommended_action in allowed values | PASS | <StringArray>
[]
Length: 0, dtype: str |
| enum | shrinkage_alerts.status in allowed values | PASS | <StringArray>
[]
Length: 0, dtype: str |
| primary_key | alert_evidence: PK ['alert_id', 'evidence_type', 'evidence_id'] unique | PASS | 224 rows |
| required | alert_evidence: required fields non-null | PASS | {} |
| enum | alert_evidence.evidence_type in allowed values | PASS | <StringArray>
[]
Length: 0, dtype: str |
| enum | alert_evidence.evidence_role in allowed values | PASS | <StringArray>
[]
Length: 0, dtype: str |
| primary_key | alert_status_events: PK ['alert_event_id'] unique | PASS | 205 rows |
| required | alert_status_events: required fields non-null | PASS | {} |
| enum | alert_status_events.to_status in allowed values | PASS | <StringArray>
[]
Length: 0, dtype: str |
| primary_key | investigations: PK ['investigation_id'] unique | PASS | 13 rows |
| required | investigations: required fields non-null | PASS | {} |
| enum | investigations.alert_family in allowed values | PASS | <StringArray>
[]
Length: 0, dtype: str |
| enum | investigations.priority in allowed values | PASS | <StringArray>
[]
Length: 0, dtype: str |
| enum | investigations.status in allowed values | PASS | <StringArray>
[]
Length: 0, dtype: str |
| enum | investigations.outcome in allowed values | PASS | <StringArray>
[]
Length: 0, dtype: str |
| primary_key | investigation_alerts: PK ['investigation_id', 'alert_id'] unique | PASS | 40 rows |
| required | investigation_alerts: required fields non-null | PASS | {} |
| primary_key | investigation_events: PK ['investigation_event_id'] unique | PASS | 39 rows |
| required | investigation_events: required fields non-null | PASS | {} |
| enum | investigation_events.to_status in allowed values | PASS | <StringArray>
[]
Length: 0, dtype: str |
| primary_key | ground_truth_cases: PK ['gt_id'] unique | PASS | 41 rows |
| required | ground_truth_cases: required fields non-null | PASS | {} |
| enum | ground_truth_cases.issue_type in allowed values | PASS | <StringArray>
[]
Length: 0, dtype: str |
| enum | ground_truth_cases.case_group in allowed values | PASS | <StringArray>
[]
Length: 0, dtype: str |
| enum | ground_truth_cases.expected_decision in allowed values | PASS | <StringArray>
[]
Length: 0, dtype: str |
| primary_key | ground_truth_links: PK ['gt_id', 'entity_type', 'entity_id'] unique | PASS | 243 rows |
| required | ground_truth_links: required fields non-null | PASS | {} |
| primary_key | ground_truth_count_causes: PK ['count_id'] unique | PASS | 500 rows |
| required | ground_truth_count_causes: required fields non-null | PASS | {} |
| primary_key | ground_truth_alert_labels: PK ['alert_id'] unique | PASS | 72 rows |
| required | ground_truth_alert_labels: required fields non-null | PASS | {} |
| id_format | stores.store_id matches ^STORE-\d{6}$ | PASS | 0 |
| id_format | skus.sku_id matches ^SKU-\d{6}$ | PASS | 0 |
| id_format | employees.employee_id matches ^EMP-\d{6}$ | PASS | 0 |
| id_format | employee_roles.employee_role_id matches ^ERL-\d{6}$ | PASS | 0 |
| id_format | shifts.shift_id matches ^SHIFT-\d{7}$ | PASS | 0 |
| id_format | promotions.promotion_id matches ^PROMO-\d{6}$ | PASS | 0 |
| id_format | inventory_movements.movement_id matches ^MOV-2026-\d{8}$ | PASS | 0 |
| id_format | inventory_movements.transfer_id matches ^XFR-2026-\d{6}$ | PASS | 0 |
| id_format | cycle_counts.count_id matches ^CNT-2026-\d{6}$ | PASS | 0 |
| id_format | returns.return_id matches ^RET-2026-\d{6}$ | PASS | 0 |
| id_format | shrinkage_alerts.alert_id matches ^SHR-2026-\d{6}$ | PASS | 0 |
| id_format | investigations.investigation_id matches ^INV-2026-\d{6}$ | PASS | 0 |
| id_format | alert_status_events.alert_event_id matches ^ALE-2026-\d{6}$ | PASS | 0 |
| id_format | investigation_events.investigation_event_id matches ^IVE-2026-\d{6}$ | PASS | 0 |
| id_format | ground_truth_cases.gt_id matches ^GT-\d{6}$ | PASS | 0 |
| id_format | inventory_movements.movement_id counters contiguous 1..N, zero-padded, no gaps | PASS |  |
| id_format | cycle_counts.count_id counters contiguous 1..N, zero-padded, no gaps | PASS |  |
| id_format | returns.return_id counters contiguous 1..N, zero-padded, no gaps | PASS |  |
| id_format | shrinkage_alerts.alert_id counters contiguous 1..N, zero-padded, no gaps | PASS |  |
| id_format | investigations.investigation_id counters contiguous 1..N, zero-padded, no gaps | PASS |  |
| id_format | alert_status_events.alert_event_id counters contiguous 1..N, zero-padded, no gaps | PASS |  |
| id_format | investigation_events.investigation_event_id counters contiguous 1..N, zero-padded, no gaps | PASS |  |
| id_format | shifts.shift_id counters contiguous 1..N, zero-padded, no gaps | PASS |  |
| foreign_key | store_skus.store_id -> stores.store_id | PASS | 0 orphans |
| foreign_key | store_skus.sku_id -> skus.sku_id | PASS | 0 orphans |
| foreign_key | employees.home_store_id -> stores.store_id | PASS | 0 orphans |
| foreign_key | employee_roles.employee_id -> employees.employee_id | PASS | 0 orphans |
| foreign_key | employee_roles.store_id -> stores.store_id | PASS | 0 orphans |
| foreign_key | shifts.store_id -> stores.store_id | PASS | 0 orphans |
| foreign_key | shifts.employee_id -> employees.employee_id | PASS | 0 orphans |
| foreign_key | promotions.owner_employee_id -> employees.employee_id | PASS | 0 orphans |
| foreign_key | promotion_skus.promotion_id -> promotions.promotion_id | PASS | 0 orphans |
| foreign_key | promotion_skus.sku_id -> skus.sku_id | PASS | 0 orphans |
| foreign_key | inventory_movements.store_id -> stores.store_id | PASS | 0 orphans |
| foreign_key | inventory_movements.sku_id -> skus.sku_id | PASS | 0 orphans |
| foreign_key | inventory_movements.shift_id -> shifts.shift_id | PASS | 0 orphans |
| foreign_key | inventory_movements.employee_id -> employees.employee_id | PASS | 0 orphans |
| foreign_key | inventory_movements.counterparty_store_id -> stores.store_id | PASS | 0 orphans |
| foreign_key | inventory_movements.promotion_id -> promotions.promotion_id | PASS | 0 orphans |
| foreign_key | cycle_counts.store_id -> stores.store_id | PASS | 0 orphans |
| foreign_key | cycle_counts.sku_id -> skus.sku_id | PASS | 0 orphans |
| foreign_key | cycle_counts.counted_by_employee_id -> employees.employee_id | PASS | 0 orphans |
| foreign_key | cycle_counts.shift_id -> shifts.shift_id | PASS | 0 orphans |
| foreign_key | returns.store_id -> stores.store_id | PASS | 0 orphans |
| foreign_key | returns.sku_id -> skus.sku_id | PASS | 0 orphans |
| foreign_key | returns.original_sale_movement_id -> inventory_movements.movement_id | PASS | 0 orphans |
| foreign_key | returns.return_movement_id -> inventory_movements.movement_id | PASS | 0 orphans |
| foreign_key | returns.processed_by_employee_id -> employees.employee_id | PASS | 0 orphans |
| foreign_key | returns.approved_by_employee_id -> employees.employee_id | PASS | 0 orphans |
| foreign_key | shrinkage_alerts.store_id -> stores.store_id | PASS | 0 orphans |
| foreign_key | shrinkage_alerts.sku_id -> skus.sku_id | PASS | 0 orphans |
| foreign_key | shrinkage_alerts.employee_id -> employees.employee_id | PASS | 0 orphans |
| foreign_key | shrinkage_alerts.assigned_to_employee_id -> employees.employee_id | PASS | 0 orphans |
| foreign_key | alert_evidence.alert_id -> shrinkage_alerts.alert_id | PASS | 0 orphans |
| foreign_key | alert_status_events.alert_id -> shrinkage_alerts.alert_id | PASS | 0 orphans |
| foreign_key | alert_status_events.actor_employee_id -> employees.employee_id | PASS | 0 orphans |
| foreign_key | investigations.store_id -> stores.store_id | PASS | 0 orphans |
| foreign_key | investigations.assigned_to_employee_id -> employees.employee_id | PASS | 0 orphans |
| foreign_key | investigation_alerts.investigation_id -> investigations.investigation_id | PASS | 0 orphans |
| foreign_key | investigation_alerts.alert_id -> shrinkage_alerts.alert_id | PASS | 0 orphans |
| foreign_key | investigation_events.investigation_id -> investigations.investigation_id | PASS | 0 orphans |
| foreign_key | investigation_events.actor_employee_id -> employees.employee_id | PASS | 0 orphans |
| foreign_key | ground_truth_cases.store_id -> stores.store_id | PASS | 0 orphans |
| foreign_key | ground_truth_links.gt_id -> ground_truth_cases.gt_id | PASS | 0 orphans |
| foreign_key | ground_truth_count_causes.count_id -> cycle_counts.count_id | PASS | 0 orphans |
| foreign_key | ground_truth_alert_labels.alert_id -> shrinkage_alerts.alert_id | PASS | 0 orphans |
| foreign_key | inventory_movements: (store_id, sku_id) exists in store_skus | PASS |  |
| foreign_key | cycle_counts: (store_id, sku_id) exists in store_skus | PASS |  |
| foreign_key | alert_evidence MOVEMENT ids exist in inventory_movements.movement_id | PASS | 145 |
| foreign_key | alert_evidence COUNT ids exist in cycle_counts.count_id | PASS | 43 |
| foreign_key | alert_evidence RETURN ids exist in returns.return_id | PASS | 15 |
| foreign_key | alert_evidence SHIFT ids exist in shifts.shift_id | PASS | 13 |
| foreign_key | alert_evidence TRANSFER ids exist in inventory_movements.transfer_id | PASS | 8 |
| foreign_key | ground_truth_links MOVEMENT ids exist | PASS |  |
| foreign_key | ground_truth_links COUNT ids exist | PASS |  |
| foreign_key | ground_truth_links TRANSFER ids exist | PASS |  |
| domain | movement sign matches movement_type | PASS |  |
| domain | warehouses record no SALE / CUSTOMER_RETURN | PASS |  |
| lineage | movement.employee_id = shift.employee_id | PASS |  |
| date_order | posted_ts falls inside its shift window | PASS |  |
| anomaly_reconciliation | movements whose store <> shift store == labelled MOVEMENT_WRONG_STORE | PASS | 8 vs 8 |
| anomaly_reconciliation | adjustments without reason == labelled ADJUSTMENT_NO_REASON | PASS | 8 vs 8 |
| domain | reason_code present for DAMAGE / CUSTOMER_RETURN (and every non-exception ADJUSTMENT) | PASS |  |
| date_order | posted_ts >= movement_ts except labelled early-posted transfer receipts | PASS | early=4, late=4, labelled=4 |
| lifecycle | each transfer_id has exactly 1 OUT + 1 IN, equal quantity, same SKU | PASS | 900 transfers |
| lifecycle | transfer legs: counterparties mirror each other and IN movement_ts is after OUT movement_ts | PASS |  |
| domain | promotion sales: SKU in promotion_skus and date inside promo window | PASS | 712 |
| reconciliation | book running balance (opening + movements) never negative | PASS | min=3 |
| reconciliation | stock equation: closing = opening + sum(movements) and >= 0 for every store/SKU | PASS |  |
| reconciliation | cycle_counts.book_qty = opening + movements posted <= count_ts (independent recomputation) | PASS |  |
| reconciliation | variance_units = counted_qty - book_qty | PASS |  |
| reconciliation | variance_value = variance_units * unit_cost | PASS |  |
| reconciliation | count status derived from variance rule | PASS |  |
| reconciliation | every count variance exactly decomposes into the six ground-truth causes | PASS |  |
| date_order | count entered_ts >= count_ts | PASS |  |
| lineage | count shift belongs to the counting employee | PASS |  |
| authorization | every count is performed by an employee with can_perform_counts | PASS |  |
| date_order | employee_roles: effective ranges ordered and non-overlapping | PASS |  |
| date_order | promotions start_date <= end_date; shifts start < end | PASS |  |
| lineage | shift.role_on_shift equals the employee's effective role on shift_date | PASS |  |
| date_order | return_ts is after the original sale | PASS |  |
| reconciliation | return quantity <= original sale quantity; same store and SKU | PASS |  |
| duplicates | each sale has at most one return; each return movement is used once | PASS |  |
| lifecycle | return: RESTOCK <=> return_movement_id set <=> status RESTOCKED | PASS |  |
| reconciliation | every CUSTOMER_RETURN movement has exactly one Return row | PASS |  |
| reconciliation | refund_amount = qty * unit_price * (1 - promo discount) | PASS |  |
| lifecycle | alert transitions follow the allowed state machine | PASS | 205 |
| lifecycle | alert event timestamps non-decreasing and chain (from = previous to) | PASS |  |
| lifecycle | alert.status equals its last event | PASS |  |
| lifecycle | investigation transitions follow the allowed state machine | PASS | 39 |
| lifecycle | investigation event timestamps non-decreasing and chain (from = previous to) | PASS |  |
| lifecycle | investigation.status equals its last event | PASS |  |
| lifecycle | investigation outcome/closed_ts set iff CLOSED | PASS |  |
| lifecycle | only INVESTIGATE alerts are linked to investigations | PASS |  |
| lifecycle | every INVESTIGATE alert belongs to an investigation | PASS |  |
| date_order | investigation opened_ts >= earliest linked alert created_ts | PASS |  |
| reconciliation | COUNT_VARIANCE alerts: estimated loss = -(variance of primary count) | PASS | 38 |
| reconciliation | alert severity derived from estimated_loss_value | PASS |  |
| evidence | every alert has >=1 PRIMARY evidence row and a reason_text citing a record id | PASS |  |
| duplicates | no duplicate alerts (same rule + primary evidence) | PASS |  |
| duplicates | exact duplicate movements (same store, SKU, type, qty, second, employee) < 0.5% of rows | PASS | 0.0000% |
| duplicates | store_skus / employee_roles natural keys unique | PASS |  |
| ground_truth | no ground-truth column exists in any input table | PASS | [] |
| ground_truth | no 'GT-' identifier appears in alert text / notes of the input tables | PASS |  |
| ground_truth | every ground-truth case has >=1 linked record | PASS |  |
| ground_truth | all alerts have a label row | PASS |  |

## Row counts

| Table | Rows |
|---|---|
| stores | 10 |
| skus | 500 |
| store_skus | 2,200 |
| employees | 84 |
| employee_roles | 96 |
| shifts | 10,860 |
| promotions | 10 |
| promotion_skus | 50 |
| inventory_movements | 20,000 |
| cycle_counts | 500 |
| returns | 1,416 |
| shrinkage_alerts | 72 |
| alert_evidence | 224 |
| alert_status_events | 205 |
| investigations | 13 |
| investigation_alerts | 40 |
| investigation_events | 39 |
| ground_truth_cases | 41 |
| ground_truth_links | 243 |
| ground_truth_count_causes | 500 |
| ground_truth_alert_labels | 72 |