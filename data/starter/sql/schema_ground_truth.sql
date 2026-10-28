PRAGMA foreign_keys = ON;

CREATE TABLE ground_truth_cases (
  gt_id TEXT NOT NULL,
  issue_type TEXT NOT NULL,
  case_group TEXT NOT NULL,
  store_id TEXT NOT NULL,
  sku_id TEXT,
  employee_id TEXT,
  window_start_ts TEXT NOT NULL,
  window_end_ts TEXT NOT NULL,
  expected_decision TEXT NOT NULL,
  true_loss_units INTEGER NOT NULL,
  true_loss_value REAL NOT NULL,
  detectable INTEGER NOT NULL,
  description TEXT NOT NULL,
  PRIMARY KEY (gt_id)
);

CREATE TABLE ground_truth_links (
  gt_id TEXT NOT NULL,
  entity_type TEXT NOT NULL,
  entity_id TEXT NOT NULL,
  PRIMARY KEY (gt_id, entity_type, entity_id)
);

CREATE TABLE ground_truth_count_causes (
  count_id TEXT NOT NULL,
  variance_units INTEGER NOT NULL,
  cause_unexplained_loss INTEGER NOT NULL,
  cause_background_shrink INTEGER NOT NULL,
  cause_pre_adjustment_drift INTEGER NOT NULL,
  cause_movement_timing_or_posting INTEGER NOT NULL,
  cause_count_noise INTEGER NOT NULL,
  cause_clipping INTEGER NOT NULL,
  variance_explained INTEGER NOT NULL,
  PRIMARY KEY (count_id)
);

CREATE TABLE ground_truth_alert_labels (
  alert_id TEXT NOT NULL,
  gt_id TEXT,
  expected_decision TEXT,
  predicted_decision TEXT NOT NULL,
  label TEXT NOT NULL,
  PRIMARY KEY (alert_id)
);
