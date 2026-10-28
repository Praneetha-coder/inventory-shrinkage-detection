import hashlib, inspect, json, os
import pandas as pd
import pytest
from shrinkage.config import make_config
from shrinkage.pipeline import export, build_tables
from shrinkage import detector, schema


@pytest.fixture(scope="module")
def out(tmp_path_factory):
    d = str(tmp_path_factory.mktemp("starter"))
    v, _ = export(make_config("starter"), d, quiet=True)
    return d, v


def test_all_validation_checks_pass(out):
    _, v = out
    failed = [c for c in v["checks"] if not c["passed"]]
    assert not failed, failed


def test_same_seed_is_byte_identical(tmp_path):
    cfg = make_config("starter")
    for i in (1, 2): export(cfg, str(tmp_path / f"r{i}"), quiet=True)
    for f in os.listdir(tmp_path / "r1" / "input"):
        h = lambda r: hashlib.sha256(open(tmp_path / r / "input" / f, "rb").read()).hexdigest()
        assert h("r1") == h("r2"), f


def test_different_seed_changes_data(tmp_path):
    a, _ = build_tables(make_config("starter")); b, _ = build_tables(make_config("starter", seed=1))
    assert not a["inventory_movements"].equals(b["inventory_movements"])


def test_exact_volumes_full_profile_parameters():
    cfg = make_config("full")
    assert (cfg.n_stores, cfg.n_skus, cfg.n_movements, cfg.n_counts, cfg.seed) == (100, 5000, 1_000_000, 20_000, 20261022)


def test_starter_row_counts(out):
    d, _ = out
    assert len(pd.read_csv(f"{d}/input/inventory_movements.csv", low_memory=False)) == 20_000
    assert len(pd.read_csv(f"{d}/input/cycle_counts.csv")) == 500


def test_detector_signature_has_no_ground_truth():
    assert list(inspect.signature(detector.detect).parameters) == ["t"]
    assert "ground" not in inspect.getsource(detector).lower().replace("ground truth", "").replace("ground-truth", "")


def test_ground_truth_separate_and_complete(out):
    d, _ = out
    assert not any("ground" in f for f in os.listdir(f"{d}/input"))
    gt = pd.read_csv(f"{d}/ground_truth/ground_truth_cases.csv")
    assert set(gt.issue_type) == set(schema.ISSUE_TYPES)


def test_variance_fully_explained(out):
    d, _ = out
    assert pd.read_csv(f"{d}/ground_truth/ground_truth_count_causes.csv").variance_explained.all()


def test_detection_quality_thresholds(out):
    d, _ = out
    m = json.load(open(f"{d}/evaluation_metrics.json"))
    assert m["theft_case_recall_detectable"] >= .95 and m["investigate_alert_precision"] >= .8 and m["benign_cases_wrongly_escalated"] == 0
