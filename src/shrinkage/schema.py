"""Single source of truth for the data dictionary, SQL DDL and enum validation.

Field spec string:  name | TYPE | required(Y/N) | allowed values | unit | uniqueness | validation rule
Money is USD. Timestamps are naive local store time (ISO 'YYYY-MM-DD HH:MM:SS'). Booleans are 0/1.
"""

REGIONS = ["NORTH", "SOUTH", "EAST", "WEST", "CENTRAL"]
CATEGORIES = ["ELECTRONICS", "GROCERY", "BEAUTY", "APPAREL", "HOUSEHOLD", "TOYS", "PHARMACY_OTC",
              "ALCOHOL_TOBACCO", "SPORTS", "HARDWARE", "BABY", "PET"]
ROLE_CODES = ["STORE_MANAGER", "ASSISTANT_MANAGER", "CASHIER", "STOCK_CLERK", "TRAINEE",
              "OPERATIONS_MANAGER", "MERCH_ANALYST"]
MOVEMENT_TYPES = ["SALE", "RECEIPT", "TRANSFER_OUT", "TRANSFER_IN", "ADJUSTMENT", "DAMAGE", "CUSTOMER_RETURN"]
ADJ_REASONS = ["COUNT_CORRECTION", "DATA_ENTRY_FIX", "SYSTEM_ERROR", "EXPIRED", "FOUND_STOCK"]
DMG_REASONS = ["DROPPED", "EXPIRED", "DAMAGED_IN_TRANSIT", "CUSTOMER_DAMAGE", "WATER_DAMAGE", "POWER_OUTAGE_SPOILAGE"]
RET_REASONS = ["CHANGE_OF_MIND", "WRONG_ITEM", "DEFECTIVE", "DAMAGED_IN_TRANSIT", "NO_RECEIPT"]
REASON_CODES = sorted(set(ADJ_REASONS + DMG_REASONS + RET_REASONS))
ISSUE_TYPES = ["UNEXPLAINED_LOSS", "REPEATED_ADJUSTMENTS", "RETURN_WITHOUT_SALE_ABUSE", "UNAUTHORIZED_ADJUSTMENT",
               "MOVEMENT_WRONG_STORE", "ADJUSTMENT_NO_REASON", "COUNT_TIMESTAMP_PRECEDES_MOVEMENT",
               "TRANSFER_IN_TRANSIT_BOTH_ENDS", "LEGIT_DAMAGE_EVENT"]
ALERT_TYPES = ["COUNT_VARIANCE", "REPEATED_ADJUSTMENTS", "RETURN_WITHOUT_SALE", "DAMAGE_SPIKE",
               "UNAUTHORIZED_ADJUSTMENT", "WRONG_STORE_MOVEMENT", "ADJUSTMENT_NO_REASON",
               "COUNT_TIMESTAMP_INCONSISTENT"]
ACTIONS = ["INVESTIGATE", "DATA_FIX", "AUTO_CLOSE_BENIGN"]
ALERT_STATUSES = ["NEW", "AUTO_CLOSED", "DATA_FIX_REQUESTED", "DATA_FIXED", "UNDER_INVESTIGATION", "CLOSED"]
INV_STATUSES = ["OPEN", "IN_PROGRESS", "CLOSED"]

ENUMS = {
    ("stores", "store_type"): ["STORE", "WAREHOUSE"],
    ("stores", "store_format"): ["EXPRESS", "STANDARD", "SUPERSTORE", "DISTRIBUTION_CENTER"],
    ("stores", "region"): REGIONS,
    ("stores", "status"): ["ACTIVE", "TEMP_CLOSED", "CLOSED"],
    ("skus", "category"): CATEGORIES,
    ("skus", "status"): ["ACTIVE", "DISCONTINUED"],
    ("store_skus", "status"): ["ACTIVE", "DELISTED"],
    ("employees", "employment_status"): ["ACTIVE", "TERMINATED"],
    ("employee_roles", "role_code"): ROLE_CODES,
    ("shifts", "shift_type"): ["DAY", "EVENING"],
    ("shifts", "role_on_shift"): ROLE_CODES,
    ("shifts", "status"): ["COMPLETED"],
    ("promotions", "status"): ["PLANNED", "ACTIVE", "ENDED", "CANCELLED"],
    ("inventory_movements", "movement_type"): MOVEMENT_TYPES,
    ("inventory_movements", "reason_code"): REASON_CODES,
    ("cycle_counts", "count_type"): ["SCHEDULED", "SPOT_CHECK"],
    ("cycle_counts", "status"): ["MATCHED", "WITHIN_TOLERANCE", "OUT_OF_TOLERANCE"],
    ("returns", "reason_code"): RET_REASONS,
    ("returns", "disposition"): ["RESTOCK", "WRITE_OFF"],
    ("returns", "status"): ["RESTOCKED", "WRITTEN_OFF"],
    ("shrinkage_alerts", "alert_type"): ALERT_TYPES,
    ("shrinkage_alerts", "severity"): ["LOW", "MEDIUM", "HIGH", "CRITICAL"],
    ("shrinkage_alerts", "recommended_action"): ACTIONS,
    ("shrinkage_alerts", "status"): ALERT_STATUSES,
    ("alert_evidence", "evidence_type"): ["MOVEMENT", "COUNT", "RETURN", "SHIFT", "TRANSFER"],
    ("alert_evidence", "evidence_role"): ["PRIMARY", "SUPPORTING", "EXPLAINING"],
    ("alert_status_events", "to_status"): ALERT_STATUSES,
    ("investigations", "alert_family"): ["COUNT", "ADJUSTMENT", "RETURN", "POLICY", "DAMAGE"],
    ("investigations", "priority"): ["LOW", "MEDIUM", "HIGH", "CRITICAL"],
    ("investigations", "status"): INV_STATUSES,
    ("investigations", "outcome"): ["CONFIRMED_LOSS", "POLICY_BREACH", "CLEARED_NO_ISSUE"],
    ("investigation_events", "to_status"): INV_STATUSES,
    ("ground_truth_cases", "issue_type"): ISSUE_TYPES,
    ("ground_truth_cases", "case_group"): ["PLANTED_THEFT_PATTERN", "DATA_QUALITY_EDGE_CASE", "BENIGN_EXPLANATION"],
    ("ground_truth_cases", "expected_decision"): ACTIONS,
}

ALERT_TRANSITIONS = {None: ["NEW"], "NEW": ["AUTO_CLOSED", "DATA_FIX_REQUESTED", "UNDER_INVESTIGATION"],
                     "DATA_FIX_REQUESTED": ["DATA_FIXED"], "UNDER_INVESTIGATION": ["CLOSED"],
                     "AUTO_CLOSED": [], "DATA_FIXED": [], "CLOSED": []}
INV_TRANSITIONS = {None: ["OPEN"], "OPEN": ["IN_PROGRESS"], "IN_PROGRESS": ["CLOSED"], "CLOSED": []}

ID_PATTERNS = {
    "stores.store_id": r"^STORE-\d{6}$", "skus.sku_id": r"^SKU-\d{6}$",
    "employees.employee_id": r"^EMP-\d{6}$", "employee_roles.employee_role_id": r"^ERL-\d{6}$",
    "shifts.shift_id": r"^SHIFT-\d{7}$", "promotions.promotion_id": r"^PROMO-\d{6}$",
    "inventory_movements.movement_id": r"^MOV-2026-\d{8}$", "inventory_movements.transfer_id": r"^XFR-2026-\d{6}$",
    "cycle_counts.count_id": r"^CNT-2026-\d{6}$", "returns.return_id": r"^RET-2026-\d{6}$",
    "shrinkage_alerts.alert_id": r"^SHR-2026-\d{6}$", "investigations.investigation_id": r"^INV-2026-\d{6}$",
    "alert_status_events.alert_event_id": r"^ALE-2026-\d{6}$",
    "investigation_events.investigation_event_id": r"^IVE-2026-\d{6}$",
    "ground_truth_cases.gt_id": r"^GT-\d{6}$",
}


def _t(desc, pk, fks, card, fields):
    return dict(desc=desc, pk=pk, fks=fks, cardinality=card, fields=[dict(zip(
        ["name", "type", "required", "allowed", "unit", "unique", "rule"], [x.strip() for x in f.split("|")]))
        for f in fields])


TABLES = {
    "stores": _t("Store or warehouse (inventory location). Master data.", ["store_id"], [], "root entity",
                 ["store_id|STRING|Y||-|PK|ID_PATTERN STORE-000001",
                  "store_name|STRING|Y||-|-|non-empty",
                  "store_type|STRING|Y|STORE,WAREHOUSE|-|-|warehouses never record SALE or CUSTOMER_RETURN",
                  "store_format|STRING|Y|EXPRESS,STANDARD,SUPERSTORE,DISTRIBUTION_CENTER|-|-|DISTRIBUTION_CENTER iff WAREHOUSE",
                  "region|STRING|Y|NORTH,SOUTH,EAST,WEST,CENTRAL|-|-|enum",
                  "open_date|DATE|Y||date|-|<= effective_from",
                  "status|STRING|Y|ACTIVE,TEMP_CLOSED,CLOSED|-|-|lifecycle state (all ACTIVE in window)",
                  "effective_from|DATE|Y||date|-|= open_date",
                  "effective_to|DATE|N||date|-|NULL = current; >= effective_from"]),
    "skus": _t("Stock-keeping unit. Master data.", ["sku_id"], [], "root entity",
               ["sku_id|STRING|Y||-|PK|ID_PATTERN SKU-000001",
                "sku_name|STRING|Y||-|-|non-empty",
                "category|STRING|Y|12 categories|-|-|enum",
                "unit_cost|DECIMAL|Y||USD|-|> 0",
                "unit_price|DECIMAL|Y||USD|-|> unit_cost",
                "case_qty|INTEGER|Y||units per case|-|> 0; receipts/transfers are multiples of it",
                "is_perishable|BOOLEAN|Y|0,1|-|-|-",
                "launch_date|DATE|Y||date|-|<= window start",
                "status|STRING|Y|ACTIVE,DISCONTINUED|-|-|enum"]),
    "store_skus": _t("Bridge Store N:M SKU (assortment) holding the OPENING BALANCE per store/SKU.",
                     ["store_id", "sku_id"], [("store_id", "stores", "store_id"), ("sku_id", "skus", "sku_id")],
                     "Store 1:N store_skus N:1 SKU",
                     ["store_id|STRING|Y||-|PK part|FK stores",
                      "sku_id|STRING|Y||-|PK part|FK skus",
                      "opening_qty|INTEGER|Y||units|-|>= 0; sized so book AND physical stock never go negative",
                      "opening_as_of|DATE|Y||date|-|= window start",
                      "min_stock_level|INTEGER|Y||units|-|>= 1; DERIVED = ceil(weekly sales units)",
                      "status|STRING|Y|ACTIVE,DELISTED|-|-|enum",
                      "effective_from|DATE|Y||date|-|-",
                      "effective_to|DATE|N||date|-|NULL = current"]),
    "employees": _t("Employee master (synthetic, no personal data).", ["employee_id"],
                    [("home_store_id", "stores", "store_id")], "Store 1:N Employee (HQ staff have no store)",
                    ["employee_id|STRING|Y||-|PK|ID_PATTERN EMP-000001",
                     "home_store_id|STRING|N||-|-|FK stores; NULL for HQ staff",
                     "hire_date|DATE|Y||date|-|-",
                     "employment_status|STRING|Y|ACTIVE,TERMINATED|-|-|enum"]),
    "employee_roles": _t("EmployeeRole: role assignment with effective dates and authorisations (history preserved).",
                         ["employee_role_id"], [("employee_id", "employees", "employee_id"), ("store_id", "stores", "store_id")],
                         "Employee 1:N EmployeeRole (non-overlapping effective ranges)",
                         ["employee_role_id|STRING|Y||-|PK|ID_PATTERN ERL-000001",
                          "employee_id|STRING|Y||-|part of UNIQUE|FK employees",
                          "store_id|STRING|N||-|-|FK stores; NULL for HQ roles",
                          "role_code|STRING|Y|7 role codes|-|-|enum",
                          "can_adjust_inventory|BOOLEAN|Y|0,1|-|-|1 only for STORE_MANAGER, ASSISTANT_MANAGER",
                          "can_perform_counts|BOOLEAN|Y|0,1|-|-|-",
                          "can_investigate|BOOLEAN|Y|0,1|-|-|1 only for OPERATIONS_MANAGER",
                          "effective_from|DATE|Y||date|UNIQUE(employee_id, effective_from)|-",
                          "effective_to|DATE|N||date|-|NULL = current; no overlap per employee"]),
    "shifts": _t("Shift roster entry: one employee on one shift slot at one store.", ["shift_id"],
                 [("store_id", "stores", "store_id"), ("employee_id", "employees", "employee_id")],
                 "Store 1:N Shift; Employee 1:N Shift; Shift 1:N InventoryMovement",
                 ["shift_id|STRING|Y||-|PK|ID_PATTERN SHIFT-0000001",
                  "store_id|STRING|Y||-|-|FK stores",
                  "employee_id|STRING|Y||-|-|FK employees; must work at store_id",
                  "shift_date|DATE|Y||date|-|within activity window",
                  "shift_type|STRING|Y|DAY,EVENING|-|-|DAY 06-14, EVENING 14-22",
                  "role_on_shift|STRING|Y|role codes|-|-|equals the employee's effective role on shift_date",
                  "start_ts|TIMESTAMP|Y||ts|-|< end_ts",
                  "end_ts|TIMESTAMP|Y||ts|-|= start_ts + 8h",
                  "status|STRING|Y|COMPLETED|-|-|enum"]),
    "promotions": _t("Chain-wide price promotion (drives legitimate sales surges).", ["promotion_id"],
                     [("owner_employee_id", "employees", "employee_id")], "Promotion N:M SKU via promotion_skus",
                     ["promotion_id|STRING|Y||-|PK|ID_PATTERN PROMO-000001",
                      "promotion_name|STRING|Y||-|-|non-empty",
                      "discount_pct|INTEGER|Y|10..40|percent|-|1..90",
                      "start_date|DATE|Y||date|-|<= end_date",
                      "end_date|DATE|Y||date|-|-",
                      "status|STRING|Y|PLANNED,ACTIVE,ENDED,CANCELLED|-|-|derived from dates vs as-of date",
                      "owner_employee_id|STRING|Y||-|-|FK employees with role MERCH_ANALYST"]),
    "promotion_skus": _t("Bridge Promotion N:M SKU.", ["promotion_id", "sku_id"],
                         [("promotion_id", "promotions", "promotion_id"), ("sku_id", "skus", "sku_id")],
                         "Promotion 1:N promotion_skus N:1 SKU",
                         ["promotion_id|STRING|Y||-|PK part|FK promotions", "sku_id|STRING|Y||-|PK part|FK skus"]),
    "inventory_movements": _t("Immutable stock-movement event ledger (never updated; corrections are new rows).",
                              ["movement_id"],
                              [("store_id", "stores", "store_id"), ("sku_id", "skus", "sku_id"),
                               ("shift_id", "shifts", "shift_id"), ("employee_id", "employees", "employee_id"),
                               ("counterparty_store_id", "stores", "store_id"),
                               ("promotion_id", "promotions", "promotion_id")],
                              "Store 1:N Movement; SKU 1:N Movement; Shift 1:N Movement; transfer = 2 movements share transfer_id",
                              ["movement_id|STRING|Y||-|PK|ID_PATTERN MOV-2026-00000001; numbered in posted_ts order",
                               "store_id|STRING|Y||-|-|FK stores; (store_id, sku_id) must exist in store_skus",
                               "sku_id|STRING|Y||-|-|FK skus",
                               "movement_type|STRING|Y|7 types|-|-|enum",
                               "quantity_signed|INTEGER|Y||units|-|SALE/TRANSFER_OUT/DAMAGE <0; RECEIPT/TRANSFER_IN/CUSTOMER_RETURN >0; ADJUSTMENT <>0",
                               "reason_code|STRING|C|reason enum|-|-|REQUIRED for DAMAGE, CUSTOMER_RETURN, ADJUSTMENT (deliberate exceptions labelled in ground truth)",
                               "movement_ts|TIMESTAMP|Y||ts|-|when the stock physically moved",
                               "posted_ts|TIMESTAMP|Y||ts|-|when it was recorded; normally = movement_ts",
                               "shift_id|STRING|Y||-|-|FK shifts; shift covers posted_ts; shift.store_id = store_id (exceptions labelled)",
                               "employee_id|STRING|Y||-|-|FK employees; = shift.employee_id",
                               "transfer_id|STRING|N||-|-|set for TRANSFER_OUT/IN; each id has exactly one OUT and one IN",
                               "counterparty_store_id|STRING|N||-|-|FK stores; other end of a transfer",
                               "promotion_id|STRING|N||-|-|FK promotions; SALE only; sku in promo and date in window",
                               "reference_note|STRING|N||-|-|incident / document reference"]),
    "cycle_counts": _t("Cycle count of one SKU at one store; variance derived from book vs counted.", ["count_id"],
                       [("store_id", "stores", "store_id"), ("sku_id", "skus", "sku_id"),
                        ("counted_by_employee_id", "employees", "employee_id"), ("shift_id", "shifts", "shift_id")],
                       "Store 1:N CycleCount; SKU 1:N CycleCount",
                       ["count_id|STRING|Y||-|PK|ID_PATTERN CNT-2026-000001; numbered in count_ts order",
                        "store_id|STRING|Y||-|-|FK stores", "sku_id|STRING|Y||-|-|FK skus",
                        "count_type|STRING|Y|SCHEDULED,SPOT_CHECK|-|-|enum",
                        "count_ts|TIMESTAMP|Y||ts|-|recorded time of count; book_qty is computed as-of this time",
                        "entered_ts|TIMESTAMP|Y||ts|-|>= count_ts",
                        "counted_by_employee_id|STRING|Y||-|-|FK employees; role can_perform_counts=1",
                        "shift_id|STRING|Y||-|-|FK shifts",
                        "book_qty|INTEGER|Y||units|-|DERIVED = opening_qty + sum(quantity_signed where posted_ts <= count_ts)",
                        "counted_qty|INTEGER|Y||units|-|>= 0",
                        "variance_units|INTEGER|Y||units|-|DERIVED = counted_qty - book_qty",
                        "variance_value|DECIMAL|Y||USD|-|DERIVED = variance_units * unit_cost",
                        "status|STRING|Y|MATCHED,WITHIN_TOLERANCE,OUT_OF_TOLERANCE|-|-|DERIVED: 0 -> MATCHED; |var|<=max(2,3% book) and |value|<50 -> WITHIN_TOLERANCE; else OUT_OF_TOLERANCE"]),
    "returns": _t("Customer return (restocked or written off).", ["return_id"],
                  [("store_id", "stores", "store_id"), ("sku_id", "skus", "sku_id"),
                   ("original_sale_movement_id", "inventory_movements", "movement_id"),
                   ("return_movement_id", "inventory_movements", "movement_id"),
                   ("processed_by_employee_id", "employees", "employee_id"),
                   ("approved_by_employee_id", "employees", "employee_id")],
                  "SALE movement 1:0..1 Return (original); Return 1:0..1 CUSTOMER_RETURN movement",
                  ["return_id|STRING|Y||-|PK|ID_PATTERN RET-2026-000001",
                   "store_id|STRING|Y||-|-|FK stores", "sku_id|STRING|Y||-|-|FK skus",
                   "quantity|INTEGER|Y||units|-|> 0; <= original sale quantity",
                   "original_sale_movement_id|STRING|N||-|-|FK movements (SALE); NULL only for NO_RECEIPT",
                   "return_movement_id|STRING|N||-|-|FK movements (CUSTOMER_RETURN); set iff disposition=RESTOCK",
                   "return_ts|TIMESTAMP|Y||ts|-|> original sale movement_ts",
                   "reason_code|STRING|Y|5 return reasons|-|-|enum",
                   "disposition|STRING|Y|RESTOCK,WRITE_OFF|-|-|DERIVED: DEFECTIVE/DAMAGED_IN_TRANSIT -> WRITE_OFF else RESTOCK",
                   "status|STRING|Y|RESTOCKED,WRITTEN_OFF|-|-|consistent with disposition",
                   "refund_amount|DECIMAL|Y||USD|-|DERIVED = quantity * unit_price * (1 - promo discount of original sale)",
                   "customer_ref|STRING|Y||-|-|synthetic anonymous reference, no personal data",
                   "processed_by_employee_id|STRING|Y||-|-|FK employees (cashier on shift)",
                   "approved_by_employee_id|STRING|N||-|-|FK employees (manager); expected for NO_RECEIPT"]),
    "shrinkage_alerts": _t("Alert produced by the rule engine (decision + exception path). No ground-truth columns.",
                           ["alert_id"],
                           [("store_id", "stores", "store_id"), ("sku_id", "skus", "sku_id"),
                            ("employee_id", "employees", "employee_id"),
                            ("assigned_to_employee_id", "employees", "employee_id")],
                           "Alert 1:N alert_evidence; Alert N:M Investigation via investigation_alerts",
                           ["alert_id|STRING|Y||-|PK|ID_PATTERN SHR-2026-000001; numbered in created_ts order",
                            "alert_type|STRING|Y|8 alert types|-|-|enum",
                            "rule_code|STRING|Y||-|-|R01..R08, see docs/ASSESSMENT.md",
                            "store_id|STRING|Y||-|-|FK stores", "sku_id|STRING|N||-|-|FK skus",
                            "employee_id|STRING|N||-|-|FK employees (employee implicated by the evidence)",
                            "created_ts|TIMESTAMP|Y||ts|-|nightly batch 02:00 after the last evidence",
                            "estimated_loss_units|INTEGER|Y||units|-|DERIVED from evidence",
                            "estimated_loss_value|DECIMAL|Y||USD|-|DERIVED from evidence",
                            "severity|STRING|Y|LOW..CRITICAL|-|-|DERIVED from value: >=2000 CRITICAL, >=800 HIGH, >=250 MEDIUM",
                            "risk_score|INTEGER|Y|0..100|score|-|DERIVED",
                            "recommended_action|STRING|Y|INVESTIGATE,DATA_FIX,AUTO_CLOSE_BENIGN|-|-|decision",
                            "status|STRING|Y|6 states|-|-|equals the last alert_status_events row",
                            "assigned_to_employee_id|STRING|Y||-|-|FK employees (MERCH_ANALYST triage)",
                            "reason_text|STRING|Y||-|-|evidence-based explanation citing record IDs"]),
    "alert_evidence": _t("Bridge Alert -> evidence record (polymorphic reference validated by type).",
                         ["alert_id", "evidence_type", "evidence_id"], [("alert_id", "shrinkage_alerts", "alert_id")],
                         "Alert 1:N Evidence",
                         ["alert_id|STRING|Y||-|PK part|FK shrinkage_alerts",
                          "evidence_type|STRING|Y|MOVEMENT,COUNT,RETURN,SHIFT,TRANSFER|-|PK part|enum",
                          "evidence_id|STRING|Y||-|PK part|must exist in the table implied by evidence_type",
                          "evidence_role|STRING|Y|PRIMARY,SUPPORTING,EXPLAINING|-|-|enum"]),
    "alert_status_events": _t("Append-only alert lifecycle history.", ["alert_event_id"],
                              [("alert_id", "shrinkage_alerts", "alert_id"), ("actor_employee_id", "employees", "employee_id")],
                              "Alert 1:N events",
                              ["alert_event_id|STRING|Y||-|PK|ID_PATTERN ALE-2026-000001",
                               "alert_id|STRING|Y||-|-|FK", "from_status|STRING|N||-|-|NULL for the first event",
                               "to_status|STRING|Y|alert statuses|-|-|transition must be allowed",
                               "event_ts|TIMESTAMP|Y||ts|-|non-decreasing per alert, <= as-of",
                               "actor_employee_id|STRING|N||-|-|NULL = SYSTEM", "note|STRING|N||-|-|-"]),
    "investigations": _t("Investigation case opened for escalated alerts.", ["investigation_id"],
                         [("store_id", "stores", "store_id"), ("assigned_to_employee_id", "employees", "employee_id")],
                         "Investigation N:M Alert via investigation_alerts",
                         ["investigation_id|STRING|Y||-|PK|ID_PATTERN INV-2026-000001",
                          "store_id|STRING|Y||-|-|FK stores",
                          "alert_family|STRING|Y|COUNT,ADJUSTMENT,RETURN,POLICY,DAMAGE|-|-|derived from alert types",
                          "opened_ts|TIMESTAMP|Y||ts|-|>= earliest linked alert created_ts",
                          "assigned_to_employee_id|STRING|Y||-|-|FK employees with can_investigate=1",
                          "priority|STRING|Y|LOW..CRITICAL|-|-|max severity of linked alerts",
                          "status|STRING|Y|OPEN,IN_PROGRESS,CLOSED|-|-|equals last event",
                          "outcome|STRING|N|CONFIRMED_LOSS,POLICY_BREACH,CLEARED_NO_ISSUE|-|-|set iff CLOSED",
                          "confirmed_loss_units|INTEGER|N||units|-|set iff outcome CONFIRMED_LOSS",
                          "confirmed_loss_value|DECIMAL|N||USD|-|set iff outcome CONFIRMED_LOSS",
                          "closed_ts|TIMESTAMP|N||ts|-|set iff CLOSED; > opened_ts",
                          "summary|STRING|Y||-|-|-"]),
    "investigation_alerts": _t("Bridge Investigation N:M Alert.", ["investigation_id", "alert_id"],
                               [("investigation_id", "investigations", "investigation_id"),
                                ("alert_id", "shrinkage_alerts", "alert_id")], "Investigation N:M Alert",
                               ["investigation_id|STRING|Y||-|PK part|FK", "alert_id|STRING|Y||-|PK part|FK; alert action must be INVESTIGATE"]),
    "investigation_events": _t("Append-only investigation lifecycle history.", ["investigation_event_id"],
                               [("investigation_id", "investigations", "investigation_id"),
                                ("actor_employee_id", "employees", "employee_id")], "Investigation 1:N events",
                               ["investigation_event_id|STRING|Y||-|PK|ID_PATTERN IVE-2026-000001",
                                "investigation_id|STRING|Y||-|-|FK", "from_status|STRING|N||-|-|NULL for first event",
                                "to_status|STRING|Y|OPEN,IN_PROGRESS,CLOSED|-|-|transition must be allowed",
                                "event_ts|TIMESTAMP|Y||ts|-|non-decreasing, <= as-of",
                                "actor_employee_id|STRING|Y||-|-|FK employees", "note|STRING|N||-|-|-"]),
}

# Ground truth lives in a SEPARATE folder/database and is never read by the detector.
GT_TABLES = {
    "ground_truth_cases": _t("One row per planted anomaly / benign trap, with expected decision.", ["gt_id"],
                             [("store_id", "stores", "store_id")], "GT case 1:N ground_truth_links",
                             ["gt_id|STRING|Y||-|PK|ID_PATTERN GT-000001",
                              "issue_type|STRING|Y|9 issue types|-|-|enum",
                              "case_group|STRING|Y|PLANTED_THEFT_PATTERN,DATA_QUALITY_EDGE_CASE,BENIGN_EXPLANATION|-|-|enum",
                              "store_id|STRING|Y||-|-|FK stores", "sku_id|STRING|N||-|-|single SKU if applicable",
                              "employee_id|STRING|N||-|-|implicated employee if applicable",
                              "window_start_ts|TIMESTAMP|Y||ts|-|-", "window_end_ts|TIMESTAMP|Y||ts|-|>= start",
                              "expected_decision|STRING|Y|INVESTIGATE,DATA_FIX,AUTO_CLOSE_BENIGN|-|-|documented rule per issue_type",
                              "true_loss_units|INTEGER|Y||units|-|real units lost / mis-stated",
                              "true_loss_value|DECIMAL|Y||USD|-|units * unit_cost",
                              "detectable|BOOLEAN|Y|0,1|-|-|0 if no cycle count ever observed the loss",
                              "description|STRING|Y||-|-|-"]),
    "ground_truth_links": _t("Bridge GT case -> affected records.", ["gt_id", "entity_type", "entity_id"],
                             [("gt_id", "ground_truth_cases", "gt_id")], "GT case 1:N links",
                             ["gt_id|STRING|Y||-|PK part|FK", "entity_type|STRING|Y|MOVEMENT,COUNT,TRANSFER,STORE_SKU|-|PK part|enum",
                              "entity_id|STRING|Y||-|PK part|-"]),
    "ground_truth_count_causes": _t("Exact decomposition of every cycle-count variance into causes.", ["count_id"],
                                    [("count_id", "cycle_counts", "count_id")], "CycleCount 1:1 causes",
                                    ["count_id|STRING|Y||-|PK|FK cycle_counts",
                                     "variance_units|INTEGER|Y||units|-|copy of cycle_counts.variance_units",
                                     "cause_unexplained_loss|INTEGER|Y||units|-|planted unrecorded loss",
                                     "cause_background_shrink|INTEGER|Y||units|-|normal small shrink",
                                     "cause_pre_adjustment_drift|INTEGER|Y||units|-|loss later booked by a legit adjustment",
                                     "cause_movement_timing_or_posting|INTEGER|Y||units|-|posting-vs-physical differences (timing, wrong store, phantom return, concealment)",
                                     "cause_count_noise|INTEGER|Y||units|-|miscount",
                                     "cause_clipping|INTEGER|Y||units|-|counted qty floored at 0",
                                     "variance_explained|BOOLEAN|Y|0,1|-|-|1 if the six causes sum exactly to variance_units"]),
    "ground_truth_alert_labels": _t("Label for every alert (derived by evidence overlap with ground_truth_links).",
                                    ["alert_id"], [("alert_id", "shrinkage_alerts", "alert_id")], "Alert 1:1 label",
                                    ["alert_id|STRING|Y||-|PK|FK shrinkage_alerts", "gt_id|STRING|N||-|-|FK ground_truth_cases",
                                     "expected_decision|STRING|N||-|-|-", "predicted_decision|STRING|Y||-|-|-",
                                     "label|STRING|Y|TRUE_POSITIVE,MISCLASSIFIED,FALSE_POSITIVE,SPURIOUS_NON_ESCALATED|-|-|-"]),
}

SQL_TYPES = {"STRING": "TEXT", "INTEGER": "INTEGER", "DECIMAL": "REAL", "BOOLEAN": "INTEGER", "DATE": "TEXT", "TIMESTAMP": "TEXT"}
PARENT_FIRST = ["stores", "skus", "employees", "employee_roles", "store_skus", "shifts", "promotions", "promotion_skus",
                "inventory_movements", "cycle_counts", "returns", "shrinkage_alerts", "alert_evidence",
                "alert_status_events", "investigations", "investigation_alerts", "investigation_events"]


def ddl(tables=None, include_fks=True):
    tables = tables or {k: TABLES[k] for k in PARENT_FIRST}
    out = ["PRAGMA foreign_keys = ON;"]
    for name, t in tables.items():
        cols = []
        for f in t["fields"]:
            nn = " NOT NULL" if f["required"] == "Y" else ""
            cols.append(f"  {f['name']} {SQL_TYPES[f['type']]}{nn}")
        cols.append(f"  PRIMARY KEY ({', '.join(t['pk'])})")
        if include_fks:
            for c, rt, rc in t["fks"]:
                cols.append(f"  FOREIGN KEY ({c}) REFERENCES {rt}({rc})")
        out.append(f"CREATE TABLE {name} (\n" + ",\n".join(cols) + "\n);")
    return "\n\n".join(out) + "\n"


def data_dictionary_md():
    lines = ["# Data Dictionary", "",
             "Generated from `src/shrinkage/schema.py` (single source of truth). Money = USD, timestamps = naive local store time, booleans = 0/1.",
             "Required: Y = always, N = optional, C = conditionally required (see rule).", ""]
    for group, tabs in (("Input / operational tables", TABLES), ("Ground-truth tables (separate folder, never used as features)", GT_TABLES)):
        lines += [f"## {group}", ""]
        for name, t in tabs.items():
            lines += [f"### `{name}`", t["desc"], "",
                      f"- **Primary key:** {', '.join(t['pk'])}",
                      "- **Foreign keys:** " + ("; ".join(f"{c} → {rt}.{rc}" for c, rt, rc in t["fks"]) or "none"),
                      f"- **Cardinality / relationships:** {t['cardinality']}", "",
                      "| Field | Type | Req | Allowed values | Unit | Uniqueness | Validation rule |", "|---|---|---|---|---|---|---|"]
            for f in t["fields"]:
                lines.append("| " + " | ".join(f[k].replace("|", "/") for k in
                             ["name", "type", "required", "allowed", "unit", "unique", "rule"]) + " |")
            lines.append("")
    lines += ["## Lifecycle state machines", "", "**Alert:** `" + str(ALERT_TRANSITIONS) + "`", "",
              "**Investigation:** `" + str(INV_TRANSITIONS) + "`", ""]
    return "\n".join(lines)
