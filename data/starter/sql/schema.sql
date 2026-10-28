PRAGMA foreign_keys = ON;

CREATE TABLE stores (
  store_id TEXT NOT NULL,
  store_name TEXT NOT NULL,
  store_type TEXT NOT NULL,
  store_format TEXT NOT NULL,
  region TEXT NOT NULL,
  open_date TEXT NOT NULL,
  status TEXT NOT NULL,
  effective_from TEXT NOT NULL,
  effective_to TEXT,
  PRIMARY KEY (store_id)
);

CREATE TABLE skus (
  sku_id TEXT NOT NULL,
  sku_name TEXT NOT NULL,
  category TEXT NOT NULL,
  unit_cost REAL NOT NULL,
  unit_price REAL NOT NULL,
  case_qty INTEGER NOT NULL,
  is_perishable INTEGER NOT NULL,
  launch_date TEXT NOT NULL,
  status TEXT NOT NULL,
  PRIMARY KEY (sku_id)
);

CREATE TABLE employees (
  employee_id TEXT NOT NULL,
  home_store_id TEXT,
  hire_date TEXT NOT NULL,
  employment_status TEXT NOT NULL,
  PRIMARY KEY (employee_id),
  FOREIGN KEY (home_store_id) REFERENCES stores(store_id)
);

CREATE TABLE employee_roles (
  employee_role_id TEXT NOT NULL,
  employee_id TEXT NOT NULL,
  store_id TEXT,
  role_code TEXT NOT NULL,
  can_adjust_inventory INTEGER NOT NULL,
  can_perform_counts INTEGER NOT NULL,
  can_investigate INTEGER NOT NULL,
  effective_from TEXT NOT NULL,
  effective_to TEXT,
  PRIMARY KEY (employee_role_id),
  FOREIGN KEY (employee_id) REFERENCES employees(employee_id),
  FOREIGN KEY (store_id) REFERENCES stores(store_id)
);

CREATE TABLE store_skus (
  store_id TEXT NOT NULL,
  sku_id TEXT NOT NULL,
  opening_qty INTEGER NOT NULL,
  opening_as_of TEXT NOT NULL,
  min_stock_level INTEGER NOT NULL,
  status TEXT NOT NULL,
  effective_from TEXT NOT NULL,
  effective_to TEXT,
  PRIMARY KEY (store_id, sku_id),
  FOREIGN KEY (store_id) REFERENCES stores(store_id),
  FOREIGN KEY (sku_id) REFERENCES skus(sku_id)
);

CREATE TABLE shifts (
  shift_id TEXT NOT NULL,
  store_id TEXT NOT NULL,
  employee_id TEXT NOT NULL,
  shift_date TEXT NOT NULL,
  shift_type TEXT NOT NULL,
  role_on_shift TEXT NOT NULL,
  start_ts TEXT NOT NULL,
  end_ts TEXT NOT NULL,
  status TEXT NOT NULL,
  PRIMARY KEY (shift_id),
  FOREIGN KEY (store_id) REFERENCES stores(store_id),
  FOREIGN KEY (employee_id) REFERENCES employees(employee_id)
);

CREATE TABLE promotions (
  promotion_id TEXT NOT NULL,
  promotion_name TEXT NOT NULL,
  discount_pct INTEGER NOT NULL,
  start_date TEXT NOT NULL,
  end_date TEXT NOT NULL,
  status TEXT NOT NULL,
  owner_employee_id TEXT NOT NULL,
  PRIMARY KEY (promotion_id),
  FOREIGN KEY (owner_employee_id) REFERENCES employees(employee_id)
);

CREATE TABLE promotion_skus (
  promotion_id TEXT NOT NULL,
  sku_id TEXT NOT NULL,
  PRIMARY KEY (promotion_id, sku_id),
  FOREIGN KEY (promotion_id) REFERENCES promotions(promotion_id),
  FOREIGN KEY (sku_id) REFERENCES skus(sku_id)
);

CREATE TABLE inventory_movements (
  movement_id TEXT NOT NULL,
  store_id TEXT NOT NULL,
  sku_id TEXT NOT NULL,
  movement_type TEXT NOT NULL,
  quantity_signed INTEGER NOT NULL,
  reason_code TEXT,
  movement_ts TEXT NOT NULL,
  posted_ts TEXT NOT NULL,
  shift_id TEXT NOT NULL,
  employee_id TEXT NOT NULL,
  transfer_id TEXT,
  counterparty_store_id TEXT,
  promotion_id TEXT,
  reference_note TEXT,
  PRIMARY KEY (movement_id),
  FOREIGN KEY (store_id) REFERENCES stores(store_id),
  FOREIGN KEY (sku_id) REFERENCES skus(sku_id),
  FOREIGN KEY (shift_id) REFERENCES shifts(shift_id),
  FOREIGN KEY (employee_id) REFERENCES employees(employee_id),
  FOREIGN KEY (counterparty_store_id) REFERENCES stores(store_id),
  FOREIGN KEY (promotion_id) REFERENCES promotions(promotion_id)
);

CREATE TABLE cycle_counts (
  count_id TEXT NOT NULL,
  store_id TEXT NOT NULL,
  sku_id TEXT NOT NULL,
  count_type TEXT NOT NULL,
  count_ts TEXT NOT NULL,
  entered_ts TEXT NOT NULL,
  counted_by_employee_id TEXT NOT NULL,
  shift_id TEXT NOT NULL,
  book_qty INTEGER NOT NULL,
  counted_qty INTEGER NOT NULL,
  variance_units INTEGER NOT NULL,
  variance_value REAL NOT NULL,
  status TEXT NOT NULL,
  PRIMARY KEY (count_id),
  FOREIGN KEY (store_id) REFERENCES stores(store_id),
  FOREIGN KEY (sku_id) REFERENCES skus(sku_id),
  FOREIGN KEY (counted_by_employee_id) REFERENCES employees(employee_id),
  FOREIGN KEY (shift_id) REFERENCES shifts(shift_id)
);

CREATE TABLE returns (
  return_id TEXT NOT NULL,
  store_id TEXT NOT NULL,
  sku_id TEXT NOT NULL,
  quantity INTEGER NOT NULL,
  original_sale_movement_id TEXT,
  return_movement_id TEXT,
  return_ts TEXT NOT NULL,
  reason_code TEXT NOT NULL,
  disposition TEXT NOT NULL,
  status TEXT NOT NULL,
  refund_amount REAL NOT NULL,
  customer_ref TEXT NOT NULL,
  processed_by_employee_id TEXT NOT NULL,
  approved_by_employee_id TEXT,
  PRIMARY KEY (return_id),
  FOREIGN KEY (store_id) REFERENCES stores(store_id),
  FOREIGN KEY (sku_id) REFERENCES skus(sku_id),
  FOREIGN KEY (original_sale_movement_id) REFERENCES inventory_movements(movement_id),
  FOREIGN KEY (return_movement_id) REFERENCES inventory_movements(movement_id),
  FOREIGN KEY (processed_by_employee_id) REFERENCES employees(employee_id),
  FOREIGN KEY (approved_by_employee_id) REFERENCES employees(employee_id)
);

CREATE TABLE shrinkage_alerts (
  alert_id TEXT NOT NULL,
  alert_type TEXT NOT NULL,
  rule_code TEXT NOT NULL,
  store_id TEXT NOT NULL,
  sku_id TEXT,
  employee_id TEXT,
  created_ts TEXT NOT NULL,
  estimated_loss_units INTEGER NOT NULL,
  estimated_loss_value REAL NOT NULL,
  severity TEXT NOT NULL,
  risk_score INTEGER NOT NULL,
  recommended_action TEXT NOT NULL,
  status TEXT NOT NULL,
  assigned_to_employee_id TEXT NOT NULL,
  reason_text TEXT NOT NULL,
  PRIMARY KEY (alert_id),
  FOREIGN KEY (store_id) REFERENCES stores(store_id),
  FOREIGN KEY (sku_id) REFERENCES skus(sku_id),
  FOREIGN KEY (employee_id) REFERENCES employees(employee_id),
  FOREIGN KEY (assigned_to_employee_id) REFERENCES employees(employee_id)
);

CREATE TABLE alert_evidence (
  alert_id TEXT NOT NULL,
  evidence_type TEXT NOT NULL,
  evidence_id TEXT NOT NULL,
  evidence_role TEXT NOT NULL,
  PRIMARY KEY (alert_id, evidence_type, evidence_id),
  FOREIGN KEY (alert_id) REFERENCES shrinkage_alerts(alert_id)
);

CREATE TABLE alert_status_events (
  alert_event_id TEXT NOT NULL,
  alert_id TEXT NOT NULL,
  from_status TEXT,
  to_status TEXT NOT NULL,
  event_ts TEXT NOT NULL,
  actor_employee_id TEXT,
  note TEXT,
  PRIMARY KEY (alert_event_id),
  FOREIGN KEY (alert_id) REFERENCES shrinkage_alerts(alert_id),
  FOREIGN KEY (actor_employee_id) REFERENCES employees(employee_id)
);

CREATE TABLE investigations (
  investigation_id TEXT NOT NULL,
  store_id TEXT NOT NULL,
  alert_family TEXT NOT NULL,
  opened_ts TEXT NOT NULL,
  assigned_to_employee_id TEXT NOT NULL,
  priority TEXT NOT NULL,
  status TEXT NOT NULL,
  outcome TEXT,
  confirmed_loss_units INTEGER,
  confirmed_loss_value REAL,
  closed_ts TEXT,
  summary TEXT NOT NULL,
  PRIMARY KEY (investigation_id),
  FOREIGN KEY (store_id) REFERENCES stores(store_id),
  FOREIGN KEY (assigned_to_employee_id) REFERENCES employees(employee_id)
);

CREATE TABLE investigation_alerts (
  investigation_id TEXT NOT NULL,
  alert_id TEXT NOT NULL,
  PRIMARY KEY (investigation_id, alert_id),
  FOREIGN KEY (investigation_id) REFERENCES investigations(investigation_id),
  FOREIGN KEY (alert_id) REFERENCES shrinkage_alerts(alert_id)
);

CREATE TABLE investigation_events (
  investigation_event_id TEXT NOT NULL,
  investigation_id TEXT NOT NULL,
  from_status TEXT,
  to_status TEXT NOT NULL,
  event_ts TEXT NOT NULL,
  actor_employee_id TEXT NOT NULL,
  note TEXT,
  PRIMARY KEY (investigation_event_id),
  FOREIGN KEY (investigation_id) REFERENCES investigations(investigation_id),
  FOREIGN KEY (actor_employee_id) REFERENCES employees(employee_id)
);
