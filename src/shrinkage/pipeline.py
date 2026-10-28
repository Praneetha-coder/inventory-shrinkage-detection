"""End-to-end pipeline: generate -> detect -> lifecycle -> label -> export (CSV + SQLite + SQL) -> validate -> evaluate -> manifest."""
from __future__ import annotations
import hashlib, json, os, platform, sqlite3, sys, time
import numpy as np
import pandas as pd

from .config import Config
from . import schema as S
from .generator import generate
from .detector import detect
from .groundtruth import match_alerts, label_alerts
from . import lifecycle


def sha256(path, chunk=1 << 20):
    h = hashlib.sha256()
    with open(path, "rb") as f:
        while b := f.read(chunk):
            h.update(b)
    return h.hexdigest()


def build_tables(cfg: Config):
    g = generate(cfg)
    t, gt = g["tables"], g["ground_truth"]
    alerts, evidence = detect(t)                         # detector sees operational tables only
    matches = match_alerts(alerts, evidence, gt["ground_truth_links"])
    life = lifecycle.build(cfg, alerts, matches, gt["ground_truth_cases"], g["meta"]["ops_ids"], g["meta"]["analyst_ids"])
    t.update(life); t["alert_evidence"] = evidence
    gt["ground_truth_alert_labels"] = label_alerts(life["shrinkage_alerts"], matches, gt["ground_truth_cases"])
    return t, gt


def write_csv(df, path):
    df.to_csv(path, index=False, lineterminator="\n")


def export(cfg: Config, out: str, quiet=False):
    t0 = time.time()
    os.makedirs(f"{out}/input", exist_ok=True); os.makedirs(f"{out}/ground_truth", exist_ok=True); os.makedirs(f"{out}/sql", exist_ok=True)
    t, gt = build_tables(cfg)
    for k, df in t.items(): write_csv(df[[f["name"] for f in S.TABLES[k]["fields"]]], f"{out}/input/{k}.csv")
    for k, df in gt.items(): write_csv(df[[f["name"] for f in S.GT_TABLES[k]["fields"]]], f"{out}/ground_truth/{k}.csv")
    json.dump({k: df.to_dict("records") for k, df in gt.items() if k == "ground_truth_cases"}, open(f"{out}/ground_truth/ground_truth_cases.json", "w"), indent=1, default=str)
    # SQL: schema + two separate SQLite databases (input vs ground truth)
    open(f"{out}/sql/schema.sql", "w").write(S.ddl())
    open(f"{out}/sql/schema_ground_truth.sql", "w").write(S.ddl(GT_ONLY := {k: S.GT_TABLES[k] for k in S.GT_TABLES}, include_fks=False))
    for dbname, tabs, src, order, fks in (("inventory.db", S.TABLES, "input", S.PARENT_FIRST, True),
                                          ("ground_truth.db", S.GT_TABLES, "ground_truth", list(S.GT_TABLES), False)):
        p = f"{out}/sql/{dbname}"
        if os.path.exists(p): os.remove(p)
        con = sqlite3.connect(p)
        con.executescript(S.ddl({k: tabs[k] for k in order}, include_fks=fks))
        for k in order:
            df = (t if src == "input" else gt)[k][[f["name"] for f in tabs[k]["fields"]]]
            df = df.astype(object).where(df.notna(), None)
            con.executemany(f"INSERT INTO {k} VALUES ({','.join('?' * df.shape[1])})", df.itertuples(index=False, name=None))
        con.commit()
        if src == "input" and cfg.n_movements <= 50_000:   # plain-text seed script only for small profiles
            open(f"{out}/sql/seed_data.sql", "w").write("\n".join(con.iterdump()))
        con.close()
        if dbname == "ground_truth.db" or cfg.n_movements > 50_000:
            pass
    from .validate import run_validation
    from .evaluate import run_evaluation
    v = run_validation(out); e = run_evaluation(out)
    write_manifest(cfg, out, v, e, time.time() - t0)
    if not quiet:
        print(f"[{out}] validation: {v['passed']}/{v['total']} checks passed; elapsed {time.time() - t0:.1f}s")
    return v, e


def write_manifest(cfg, out, v, e, secs):
    files = {}
    for root, _, fs in os.walk(out):
        for f in sorted(fs):
            p = os.path.join(root, f)
            if f.endswith(".db") or f in ("manifest.json",): continue
            rel = os.path.relpath(p, out).replace("\\", "/")
            files[rel] = dict(bytes=os.path.getsize(p), sha256=sha256(p),
                              rows=(sum(1 for _ in open(p, encoding="utf8")) - 1) if f.endswith(".csv") else None)
    prof = "full" if cfg.n_movements >= 1_000_000 else "starter"
    m = dict(generator_command=f"python run.py {prof}   (equivalent: cd src && python -m shrinkage generate --profile {prof} --out ../data/{prof})",
             config=cfg.to_dict(), fixed_seed=cfg.seed, python=sys.version.split()[0], numpy=np.__version__, pandas=pd.__version__,
             platform=platform.platform(), runtime_seconds=round(secs, 1),
             external_data_sources=[], provenance="100% synthetic. No external, public, personal or confidential data was used. "
             "Schema ideas are inspired by generic retail inventory-shrink concepts only (no licensed dataset ingested).",
             validation_passed=f"{v['passed']}/{v['total']}", files=files)
    json.dump(m, open(f"{out}/manifest.json", "w"), indent=1)
