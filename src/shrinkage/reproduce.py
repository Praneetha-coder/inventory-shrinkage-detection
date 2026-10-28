"""Step 10: regenerate twice with the same seed and compare row counts + SHA-256 checksums."""
import json, os, shutil
from .pipeline import export


def reproduce(cfg, out):
    runs = []
    for i in (1, 2):
        d = f"{out}_repro_run{i}"
        shutil.rmtree(d, ignore_errors=True)
        export(cfg, d, quiet=True)
        m = json.load(open(f"{d}/manifest.json"))["files"]
        runs.append({k: (v["rows"], v["sha256"]) for k, v in m.items() if k.endswith((".csv", ".json", ".sql")) and not k.startswith("manifest")})
    same = runs[0] == runs[1]
    rep = dict(seed=cfg.seed, identical=same, files_compared=len(runs[0]),
               files={k: dict(rows=runs[0][k][0], sha256_run1=runs[0][k][1], sha256_run2=runs[1][k][1], match=runs[0][k] == runs[1][k]) for k in runs[0]})
    os.makedirs(out, exist_ok=True)
    json.dump(rep, open(f"{out}/reproducibility_report.json", "w"), indent=1)
    for i in (1, 2): shutil.rmtree(f"{out}_repro_run{i}", ignore_errors=True)
    print(f"Reproducibility: {'IDENTICAL' if same else 'DIFFERENT'} across 2 runs ({len(runs[0])} files compared) -> {out}/reproducibility_report.json")
    return same
