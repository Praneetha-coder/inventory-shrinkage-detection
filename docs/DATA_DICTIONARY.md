# Data Dictionary

Generated from `src/shrinkage/schema.py` (single source of truth). Money = USD, timestamps = naive local store time, booleans = 0/1.
Required: Y = always, N = optional, C = conditionally required (see rule).

## Input / operational tables

### `stores`
Store or warehouse (inventory location). Master data.

- **Primary key:** store_id
- **Foreign keys:** none
- **Cardinality / relationships:** root entity

| Field | Type | Req | Allowed values | Unit | Uniqueness | Validation rule |
|---|---|---|---|---|---|---|
| store_id | STRING | Y |  | - | PK | ID_PATTERN STORE-000001 |
| store_name | STRING | Y |  | - | - | non-empty |
| store_type | STRING | Y | STORE,WAREHOUSE | - | - | warehouses never record SALE or CUSTOMER_RETURN |
| store_format | STRING | Y | EXPRESS,STANDARD,SUPERSTORE,DISTRIBUTION_CENTER | - | - | DISTRIBUTION_CENTER iff WAREHOUSE |
| region | STRING | Y | NORTH,SOUTH,EAST,WEST,CENTRAL | - | - | enum |
| open_date | DATE | Y |  | date | - | <= effective_from |
| status | STRING | Y | ACTIVE,TEMP_CLOSED,CLOSED | - | - | lifecycle state (all ACTIVE in window) |
| effective_from | DATE | Y |  | date | - | = open_date |
| effective_to | DATE | N |  | date | - | NULL = current; >= effective_from |

### `skus`
Stock-keeping unit. Master data.

- **Primary key:** sku_id
- **Foreign keys:** none
- **Cardinality / relationships:** root entity

| Field | Type | Req | Allowed values | Unit | Uniqueness | Validation rule |
|---|---|---|---|---|---|---|
| sku_id | STRING | Y |  | - | PK | ID_PATTERN SKU-000001 |
| sku_name | STRING | Y |  | - | - | non-empty |
| category | STRING | Y | 12 categories | - | - | enum |
| unit_cost | DECIMAL | Y |  | USD | - | > 0 |
| unit_price | DECIMAL | Y |  | USD | - | > unit_cost |
| case_qty | INTEGER | Y |  | units per case | - | > 0; receipts/transfers are multiples of it |
| is_perishable | BOOLEAN | Y | 0,1 | - | - | - |
| launch_date | DATE | Y |  | date | - | <= window start |
| status | STRING | Y | ACTIVE,DISCONTINUED | - | - | enum |

### `store_skus`
Bridge Store N:M SKU (assortment) holding the OPENING BALANCE per store/SKU.

- **Primary key:** store_id, sku_id
- **Foreign keys:** store_id → stores.store_id; sku_id → skus.sku_id
- **Cardinality / relationships:** Store 1:N store_skus N:1 SKU

| Field | Type | Req | Allowed values | Unit | Uniqueness | Validation rule |
|---|---|---|---|---|---|---|
| store_id | STRING | Y |  | - | PK part | FK stores |
| sku_id | STRING | Y |  | - | PK part | FK skus |
| opening_qty | INTEGER | Y |  | units | - | >= 0; sized so book AND physical stock never go negative |
| opening_as_of | DATE | Y |  | date | - | = window start |
| min_stock_level | INTEGER | Y |  | units | - | >= 1; DERIVED = ceil(weekly sales units) |
| status | STRING | Y | ACTIVE,DELISTED | - | - | enum |
| effective_from | DATE | Y |  | date | - | - |
| effective_to | DATE | N |  | date | - | NULL = current |

### `employees`
Employee master (synthetic, no personal data).

- **Primary key:** employee_id
- **Foreign keys:** home_store_id → stores.store_id
- **Cardinality / relationships:** Store 1:N Employee (HQ staff have no store)

| Field | Type | Req | Allowed values | Unit | Uniqueness | Validation rule |
|---|---|---|---|---|---|---|
| employee_id | STRING | Y |  | - | PK | ID_PATTERN EMP-000001 |
| home_store_id | STRING | N |  | - | - | FK stores; NULL for HQ staff |
| hire_date | DATE | Y |  | date | - | - |
| employment_status | STRING | Y | ACTIVE,TERMINATED | - | - | enum |

### `employee_roles`
EmployeeRole: role assignment with effective dates and authorisations (history preserved).

- **Primary key:** employee_role_id
- **Foreign keys:** employee_id → employees.employee_id; store_id → stores.store_id
- **Cardinality / relationships:** Employee 1:N EmployeeRole (non-overlapping effective ranges)

| Field | Type | Req | Allowed values | Unit | Uniqueness | Validation rule |
|---|---|---|---|---|---|---|
| employee_role_id | STRING | Y |  | - | PK | ID_PATTERN ERL-000001 |
| employee_id | STRING | Y |  | - | part of UNIQUE | FK employees |
| store_id | STRING | N |  | - | - | FK stores; NULL for HQ roles |
| role_code | STRING | Y | 7 role codes | - | - | enum |
| can_adjust_inventory | BOOLEAN | Y | 0,1 | - | - | 1 only for STORE_MANAGER, ASSISTANT_MANAGER |
| can_perform_counts | BOOLEAN | Y | 0,1 | - | - | - |
| can_investigate | BOOLEAN | Y | 0,1 | - | - | 1 only for OPERATIONS_MANAGER |
| effective_from | DATE | Y |  | date | UNIQUE(employee_id, effective_from) | - |
| effective_to | DATE | N |  | date | - | NULL = current; no overlap per employee |

### `shifts`
Shift roster entry: one employee on one shift slot at one store.

- **Primary key:** shift_id
- **Foreign keys:** store_id → stores.store_id; employee_id → employees.employee_id
- **Cardinality / relationships:** Store 1:N Shift; Employee 1:N Shift; Shift 1:N InventoryMovement

| Field | Type | Req | Allowed values | Unit | Uniqueness | Validation rule |
|---|---|---|---|---|---|---|
| shift_id | STRING | Y |  | - | PK | ID_PATTERN SHIFT-0000001 |
| store_id | STRING | Y |  | - | - | FK stores |
| employee_id | STRING | Y |  | - | - | FK employees; must work at store_id |
| shift_date | DATE | Y |  | date | - | within activity window |
| shift_type | STRING | Y | DAY,EVENING | - | - | DAY 06-14, EVENING 14-22 |
| role_on_shift | STRING | Y | role codes | - | - | equals the employee's effective role on shift_date |
| start_ts | TIMESTAMP | Y |  | ts | - | < end_ts |
| end_ts | TIMESTAMP | Y |  | ts | - | = start_ts + 8h |
| status | STRING | Y | COMPLETED | - | - | enum |

### `promotions`
Chain-wide price promotion (drives legitimate sales surges).

- **Primary key:** promotion_id
- **Foreign keys:** owner_employee_id → employees.employee_id
- **Cardinality / relationships:** Promotion N:M SKU via promotion_skus

| Field | Type | Req | Allowed values | Unit | Uniqueness | Validation rule |
|---|---|---|---|---|---|---|
| promotion_id | STRING | Y |  | - | PK | ID_PATTERN PROMO-000001 |
| promotion_name | STRING | Y |  | - | - | non-empty |
| discount_pct | INTEGER | Y | 10..40 | percent | - | 1..90 |
| start_date | DATE | Y |  | date | - | <= end_date |
| end_date | DATE | Y |  | date | - | - |
| status | STRING | Y | PLANNED,ACTIVE,ENDED,CANCELLED | - | - | derived from dates vs as-of date |
| owner_employee_id | STRING | Y |  | - | - | FK employees with role MERCH_ANALYST |

### `promotion_skus`
Bridge Promotion N:M SKU.

- **Primary key:** promotion_id, sku_id
- **Foreign keys:** promotion_id → promotions.promotion_id; sku_id → skus.sku_id
- **Cardinality / relationships:** Promotion 1:N promotion_skus N:1 SKU

| Field | Type | Req | Allowed values | Unit | Uniqueness | Validation rule |
|---|---|---|---|---|---|---|
| promotion_id | STRING | Y |  | - | PK part | FK promotions |
| sku_id | STRING | Y |  | - | PK part | FK skus |

### `inventory_movements`
Immutable stock-movement event ledger (never updated; corrections are new rows).

- **Primary key:** movement_id
- **Foreign keys:** store_id → stores.store_id; sku_id → skus.sku_id; shift_id → shifts.shift_id; employee_id → employees.employee_id; counterparty_store_id → stores.store_id; promotion_id → promotions.promotion_id
- **Cardinality / relationships:** Store 1:N Movement; SKU 1:N Movement; Shift 1:N Movement; transfer = 2 movements share transfer_id

| Field | Type | Req | Allowed values | Unit | Uniqueness | Validation rule |
|---|---|---|---|---|---|---|
| movement_id | STRING | Y |  | - | PK | ID_PATTERN MOV-2026-00000001; numbered in posted_ts order |
| store_id | STRING | Y |  | - | - | FK stores; (store_id, sku_id) must exist in store_skus |
| sku_id | STRING | Y |  | - | - | FK skus |
| movement_type | STRING | Y | 7 types | - | - | enum |
| quantity_signed | INTEGER | Y |  | units | - | SALE/TRANSFER_OUT/DAMAGE <0; RECEIPT/TRANSFER_IN/CUSTOMER_RETURN >0; ADJUSTMENT <>0 |
| reason_code | STRING | C | reason enum | - | - | REQUIRED for DAMAGE, CUSTOMER_RETURN, ADJUSTMENT (deliberate exceptions labelled in ground truth) |
| movement_ts | TIMESTAMP | Y |  | ts | - | when the stock physically moved |
| posted_ts | TIMESTAMP | Y |  | ts | - | when it was recorded; normally = movement_ts |
| shift_id | STRING | Y |  | - | - | FK shifts; shift covers posted_ts; shift.store_id = store_id (exceptions labelled) |
| employee_id | STRING | Y |  | - | - | FK employees; = shift.employee_id |
| transfer_id | STRING | N |  | - | - | set for TRANSFER_OUT/IN; each id has exactly one OUT and one IN |
| counterparty_store_id | STRING | N |  | - | - | FK stores; other end of a transfer |
| promotion_id | STRING | N |  | - | - | FK promotions; SALE only; sku in promo and date in window |
| reference_note | STRING | N |  | - | - | incident / document reference |

### `cycle_counts`
Cycle count of one SKU at one store; variance derived from book vs counted.

- **Primary key:** count_id
- **Foreign keys:** store_id → stores.store_id; sku_id → skus.sku_id; counted_by_employee_id → employees.employee_id; shift_id → shifts.shift_id
- **Cardinality / relationships:** Store 1:N CycleCount; SKU 1:N CycleCount

| Field | Type | Req | Allowed values | Unit | Uniqueness | Validation rule |
|---|---|---|---|---|---|---|
| count_id | STRING | Y |  | - | PK | ID_PATTERN CNT-2026-000001; numbered in count_ts order |
| store_id | STRING | Y |  | - | - | FK stores |
| sku_id | STRING | Y |  | - | - | FK skus |
| count_type | STRING | Y | SCHEDULED,SPOT_CHECK | - | - | enum |
| count_ts | TIMESTAMP | Y |  | ts | - | recorded time of count; book_qty is computed as-of this time |
| entered_ts | TIMESTAMP | Y |  | ts | - | >= count_ts |
| counted_by_employee_id | STRING | Y |  | - | - | FK employees; role can_perform_counts=1 |
| shift_id | STRING | Y |  | - | - | FK shifts |
| book_qty | INTEGER | Y |  | units | - | DERIVED = opening_qty + sum(quantity_signed where posted_ts <= count_ts) |
| counted_qty | INTEGER | Y |  | units | - | >= 0 |
| variance_units | INTEGER | Y |  | units | - | DERIVED = counted_qty - book_qty |
| variance_value | DECIMAL | Y |  | USD | - | DERIVED = variance_units * unit_cost |
| status | STRING | Y | MATCHED,WITHIN_TOLERANCE,OUT_OF_TOLERANCE | - | - | DERIVED: 0 -> MATCHED; |

### `returns`
Customer return (restocked or written off).

- **Primary key:** return_id
- **Foreign keys:** store_id → stores.store_id; sku_id → skus.sku_id; original_sale_movement_id → inventory_movements.movement_id; return_movement_id → inventory_movements.movement_id; processed_by_employee_id → employees.employee_id; approved_by_employee_id → employees.employee_id
- **Cardinality / relationships:** SALE movement 1:0..1 Return (original); Return 1:0..1 CUSTOMER_RETURN movement

| Field | Type | Req | Allowed values | Unit | Uniqueness | Validation rule |
|---|---|---|---|---|---|---|
| return_id | STRING | Y |  | - | PK | ID_PATTERN RET-2026-000001 |
| store_id | STRING | Y |  | - | - | FK stores |
| sku_id | STRING | Y |  | - | - | FK skus |
| quantity | INTEGER | Y |  | units | - | > 0; <= original sale quantity |
| original_sale_movement_id | STRING | N |  | - | - | FK movements (SALE); NULL only for NO_RECEIPT |
| return_movement_id | STRING | N |  | - | - | FK movements (CUSTOMER_RETURN); set iff disposition=RESTOCK |
| return_ts | TIMESTAMP | Y |  | ts | - | > original sale movement_ts |
| reason_code | STRING | Y | 5 return reasons | - | - | enum |
| disposition | STRING | Y | RESTOCK,WRITE_OFF | - | - | DERIVED: DEFECTIVE/DAMAGED_IN_TRANSIT -> WRITE_OFF else RESTOCK |
| status | STRING | Y | RESTOCKED,WRITTEN_OFF | - | - | consistent with disposition |
| refund_amount | DECIMAL | Y |  | USD | - | DERIVED = quantity * unit_price * (1 - promo discount of original sale) |
| customer_ref | STRING | Y |  | - | - | synthetic anonymous reference, no personal data |
| processed_by_employee_id | STRING | Y |  | - | - | FK employees (cashier on shift) |
| approved_by_employee_id | STRING | N |  | - | - | FK employees (manager); expected for NO_RECEIPT |

### `shrinkage_alerts`
Alert produced by the rule engine (decision + exception path). No ground-truth columns.

- **Primary key:** alert_id
- **Foreign keys:** store_id → stores.store_id; sku_id → skus.sku_id; employee_id → employees.employee_id; assigned_to_employee_id → employees.employee_id
- **Cardinality / relationships:** Alert 1:N alert_evidence; Alert N:M Investigation via investigation_alerts

| Field | Type | Req | Allowed values | Unit | Uniqueness | Validation rule |
|---|---|---|---|---|---|---|
| alert_id | STRING | Y |  | - | PK | ID_PATTERN SHR-2026-000001; numbered in created_ts order |
| alert_type | STRING | Y | 8 alert types | - | - | enum |
| rule_code | STRING | Y |  | - | - | R01..R08, see docs/ASSESSMENT.md |
| store_id | STRING | Y |  | - | - | FK stores |
| sku_id | STRING | N |  | - | - | FK skus |
| employee_id | STRING | N |  | - | - | FK employees (employee implicated by the evidence) |
| created_ts | TIMESTAMP | Y |  | ts | - | nightly batch 02:00 after the last evidence |
| estimated_loss_units | INTEGER | Y |  | units | - | DERIVED from evidence |
| estimated_loss_value | DECIMAL | Y |  | USD | - | DERIVED from evidence |
| severity | STRING | Y | LOW..CRITICAL | - | - | DERIVED from value: >=2000 CRITICAL, >=800 HIGH, >=250 MEDIUM |
| risk_score | INTEGER | Y | 0..100 | score | - | DERIVED |
| recommended_action | STRING | Y | INVESTIGATE,DATA_FIX,AUTO_CLOSE_BENIGN | - | - | decision |
| status | STRING | Y | 6 states | - | - | equals the last alert_status_events row |
| assigned_to_employee_id | STRING | Y |  | - | - | FK employees (MERCH_ANALYST triage) |
| reason_text | STRING | Y |  | - | - | evidence-based explanation citing record IDs |

### `alert_evidence`
Bridge Alert -> evidence record (polymorphic reference validated by type).

- **Primary key:** alert_id, evidence_type, evidence_id
- **Foreign keys:** alert_id → shrinkage_alerts.alert_id
- **Cardinality / relationships:** Alert 1:N Evidence

| Field | Type | Req | Allowed values | Unit | Uniqueness | Validation rule |
|---|---|---|---|---|---|---|
| alert_id | STRING | Y |  | - | PK part | FK shrinkage_alerts |
| evidence_type | STRING | Y | MOVEMENT,COUNT,RETURN,SHIFT,TRANSFER | - | PK part | enum |
| evidence_id | STRING | Y |  | - | PK part | must exist in the table implied by evidence_type |
| evidence_role | STRING | Y | PRIMARY,SUPPORTING,EXPLAINING | - | - | enum |

### `alert_status_events`
Append-only alert lifecycle history.

- **Primary key:** alert_event_id
- **Foreign keys:** alert_id → shrinkage_alerts.alert_id; actor_employee_id → employees.employee_id
- **Cardinality / relationships:** Alert 1:N events

| Field | Type | Req | Allowed values | Unit | Uniqueness | Validation rule |
|---|---|---|---|---|---|---|
| alert_event_id | STRING | Y |  | - | PK | ID_PATTERN ALE-2026-000001 |
| alert_id | STRING | Y |  | - | - | FK |
| from_status | STRING | N |  | - | - | NULL for the first event |
| to_status | STRING | Y | alert statuses | - | - | transition must be allowed |
| event_ts | TIMESTAMP | Y |  | ts | - | non-decreasing per alert, <= as-of |
| actor_employee_id | STRING | N |  | - | - | NULL = SYSTEM |
| note | STRING | N |  | - | - | - |

### `investigations`
Investigation case opened for escalated alerts.

- **Primary key:** investigation_id
- **Foreign keys:** store_id → stores.store_id; assigned_to_employee_id → employees.employee_id
- **Cardinality / relationships:** Investigation N:M Alert via investigation_alerts

| Field | Type | Req | Allowed values | Unit | Uniqueness | Validation rule |
|---|---|---|---|---|---|---|
| investigation_id | STRING | Y |  | - | PK | ID_PATTERN INV-2026-000001 |
| store_id | STRING | Y |  | - | - | FK stores |
| alert_family | STRING | Y | COUNT,ADJUSTMENT,RETURN,POLICY,DAMAGE | - | - | derived from alert types |
| opened_ts | TIMESTAMP | Y |  | ts | - | >= earliest linked alert created_ts |
| assigned_to_employee_id | STRING | Y |  | - | - | FK employees with can_investigate=1 |
| priority | STRING | Y | LOW..CRITICAL | - | - | max severity of linked alerts |
| status | STRING | Y | OPEN,IN_PROGRESS,CLOSED | - | - | equals last event |
| outcome | STRING | N | CONFIRMED_LOSS,POLICY_BREACH,CLEARED_NO_ISSUE | - | - | set iff CLOSED |
| confirmed_loss_units | INTEGER | N |  | units | - | set iff outcome CONFIRMED_LOSS |
| confirmed_loss_value | DECIMAL | N |  | USD | - | set iff outcome CONFIRMED_LOSS |
| closed_ts | TIMESTAMP | N |  | ts | - | set iff CLOSED; > opened_ts |
| summary | STRING | Y |  | - | - | - |

### `investigation_alerts`
Bridge Investigation N:M Alert.

- **Primary key:** investigation_id, alert_id
- **Foreign keys:** investigation_id → investigations.investigation_id; alert_id → shrinkage_alerts.alert_id
- **Cardinality / relationships:** Investigation N:M Alert

| Field | Type | Req | Allowed values | Unit | Uniqueness | Validation rule |
|---|---|---|---|---|---|---|
| investigation_id | STRING | Y |  | - | PK part | FK |
| alert_id | STRING | Y |  | - | PK part | FK; alert action must be INVESTIGATE |

### `investigation_events`
Append-only investigation lifecycle history.

- **Primary key:** investigation_event_id
- **Foreign keys:** investigation_id → investigations.investigation_id; actor_employee_id → employees.employee_id
- **Cardinality / relationships:** Investigation 1:N events

| Field | Type | Req | Allowed values | Unit | Uniqueness | Validation rule |
|---|---|---|---|---|---|---|
| investigation_event_id | STRING | Y |  | - | PK | ID_PATTERN IVE-2026-000001 |
| investigation_id | STRING | Y |  | - | - | FK |
| from_status | STRING | N |  | - | - | NULL for first event |
| to_status | STRING | Y | OPEN,IN_PROGRESS,CLOSED | - | - | transition must be allowed |
| event_ts | TIMESTAMP | Y |  | ts | - | non-decreasing, <= as-of |
| actor_employee_id | STRING | Y |  | - | - | FK employees |
| note | STRING | N |  | - | - | - |

## Ground-truth tables (separate folder, never used as features)

### `ground_truth_cases`
One row per planted anomaly / benign trap, with expected decision.

- **Primary key:** gt_id
- **Foreign keys:** store_id → stores.store_id
- **Cardinality / relationships:** GT case 1:N ground_truth_links

| Field | Type | Req | Allowed values | Unit | Uniqueness | Validation rule |
|---|---|---|---|---|---|---|
| gt_id | STRING | Y |  | - | PK | ID_PATTERN GT-000001 |
| issue_type | STRING | Y | 9 issue types | - | - | enum |
| case_group | STRING | Y | PLANTED_THEFT_PATTERN,DATA_QUALITY_EDGE_CASE,BENIGN_EXPLANATION | - | - | enum |
| store_id | STRING | Y |  | - | - | FK stores |
| sku_id | STRING | N |  | - | - | single SKU if applicable |
| employee_id | STRING | N |  | - | - | implicated employee if applicable |
| window_start_ts | TIMESTAMP | Y |  | ts | - | - |
| window_end_ts | TIMESTAMP | Y |  | ts | - | >= start |
| expected_decision | STRING | Y | INVESTIGATE,DATA_FIX,AUTO_CLOSE_BENIGN | - | - | documented rule per issue_type |
| true_loss_units | INTEGER | Y |  | units | - | real units lost / mis-stated |
| true_loss_value | DECIMAL | Y |  | USD | - | units * unit_cost |
| detectable | BOOLEAN | Y | 0,1 | - | - | 0 if no cycle count ever observed the loss |
| description | STRING | Y |  | - | - | - |

### `ground_truth_links`
Bridge GT case -> affected records.

- **Primary key:** gt_id, entity_type, entity_id
- **Foreign keys:** gt_id → ground_truth_cases.gt_id
- **Cardinality / relationships:** GT case 1:N links

| Field | Type | Req | Allowed values | Unit | Uniqueness | Validation rule |
|---|---|---|---|---|---|---|
| gt_id | STRING | Y |  | - | PK part | FK |
| entity_type | STRING | Y | MOVEMENT,COUNT,TRANSFER,STORE_SKU | - | PK part | enum |
| entity_id | STRING | Y |  | - | PK part | - |

### `ground_truth_count_causes`
Exact decomposition of every cycle-count variance into causes.

- **Primary key:** count_id
- **Foreign keys:** count_id → cycle_counts.count_id
- **Cardinality / relationships:** CycleCount 1:1 causes

| Field | Type | Req | Allowed values | Unit | Uniqueness | Validation rule |
|---|---|---|---|---|---|---|
| count_id | STRING | Y |  | - | PK | FK cycle_counts |
| variance_units | INTEGER | Y |  | units | - | copy of cycle_counts.variance_units |
| cause_unexplained_loss | INTEGER | Y |  | units | - | planted unrecorded loss |
| cause_background_shrink | INTEGER | Y |  | units | - | normal small shrink |
| cause_pre_adjustment_drift | INTEGER | Y |  | units | - | loss later booked by a legit adjustment |
| cause_movement_timing_or_posting | INTEGER | Y |  | units | - | posting-vs-physical differences (timing, wrong store, phantom return, concealment) |
| cause_count_noise | INTEGER | Y |  | units | - | miscount |
| cause_clipping | INTEGER | Y |  | units | - | counted qty floored at 0 |
| variance_explained | BOOLEAN | Y | 0,1 | - | - | 1 if the six causes sum exactly to variance_units |

### `ground_truth_alert_labels`
Label for every alert (derived by evidence overlap with ground_truth_links).

- **Primary key:** alert_id
- **Foreign keys:** alert_id → shrinkage_alerts.alert_id
- **Cardinality / relationships:** Alert 1:1 label

| Field | Type | Req | Allowed values | Unit | Uniqueness | Validation rule |
|---|---|---|---|---|---|---|
| alert_id | STRING | Y |  | - | PK | FK shrinkage_alerts |
| gt_id | STRING | N |  | - | - | FK ground_truth_cases |
| expected_decision | STRING | N |  | - | - | - |
| predicted_decision | STRING | Y |  | - | - | - |
| label | STRING | Y | TRUE_POSITIVE,MISCLASSIFIED,FALSE_POSITIVE,SPURIOUS_NON_ESCALATED | - | - | - |

## Lifecycle state machines

**Alert:** `{None: ['NEW'], 'NEW': ['AUTO_CLOSED', 'DATA_FIX_REQUESTED', 'UNDER_INVESTIGATION'], 'DATA_FIX_REQUESTED': ['DATA_FIXED'], 'UNDER_INVESTIGATION': ['CLOSED'], 'AUTO_CLOSED': [], 'DATA_FIXED': [], 'CLOSED': []}`

**Investigation:** `{None: ['OPEN'], 'OPEN': ['IN_PROGRESS'], 'IN_PROGRESS': ['CLOSED'], 'CLOSED': []}`
