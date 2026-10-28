"""Command line:  python -m shrinkage.cli {generate|reproduce|validate} ..."""
import argparse, shutil, sys
from .config import make_config


def main(argv=None):
    ap = argparse.ArgumentParser(prog="shrinkage")
    sub = ap.add_subparsers(dest="cmd", required=True)
    for name in ("generate", "reproduce"):
        p = sub.add_parser(name)
        p.add_argument("--profile", choices=["starter", "full"], default="starter")
        p.add_argument("--out", default=None)
        p.add_argument("--seed", type=int, default=None)
        for k in ("n_stores", "n_skus", "n_movements", "n_counts", "skus_per_store"):
            p.add_argument("--" + k.replace("_", "-"), type=int, default=None, dest=k)
    v = sub.add_parser("validate"); v.add_argument("--out", required=True)
    a = ap.parse_args(argv)
    if a.cmd == "validate":
        from .validate import run_validation
        r = run_validation(a.out); print(f"{r['passed']}/{r['total']} checks passed"); return 0 if r["passed"] == r["total"] else 1
    ov = {k: getattr(a, k) for k in ("seed", "n_stores", "n_skus", "n_movements", "n_counts", "skus_per_store")}
    cfg = make_config(a.profile, **ov)
    out = a.out or f"data/{a.profile}"
    if a.cmd == "generate":
        from .pipeline import export
        v, e = export(cfg, out); return 0 if v["passed"] == v["total"] else 1
    from .reproduce import reproduce
    return 0 if reproduce(cfg, out) else 1


if __name__ == "__main__":
    sys.exit(main())
