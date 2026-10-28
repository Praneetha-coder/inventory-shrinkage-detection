"""Convenience launcher so no installation / PYTHONPATH is needed:

    python run.py starter      # 10 stores / 500 SKUs / 20k movements   (~3 s)
    python run.py full         # 100 stores / 5,000 SKUs / 1M movements (~1.5 min, ~3 GB RAM)
    python run.py reproduce    # regenerate STARTER twice, compare row counts + SHA-256
    python run.py reproduce-full
    python run.py docs         # rebuild docs/DATA_DICTIONARY.md + sql/schema.sql from schema.py
    python run.py test         # pytest
"""
import os, subprocess, sys

ROOT = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(ROOT, "src"))


def main():
    cmd = sys.argv[1] if len(sys.argv) > 1 else "starter"
    from shrinkage.cli import main as cli
    if cmd == "starter":   return cli(["generate", "--profile", "starter", "--out", os.path.join(ROOT, "data", "starter")])
    if cmd == "full":      return cli(["generate", "--profile", "full", "--out", os.path.join(ROOT, "data", "full")])
    if cmd == "reproduce": return cli(["reproduce", "--profile", "starter", "--out", os.path.join(ROOT, "data", "starter")])
    if cmd == "reproduce-full": return cli(["reproduce", "--profile", "full", "--out", os.path.join(ROOT, "data", "full")])
    if cmd == "docs":
        from shrinkage import schema
        open(os.path.join(ROOT, "docs", "DATA_DICTIONARY.md"), "w", encoding="utf8").write(schema.data_dictionary_md())
        print("docs/DATA_DICTIONARY.md written"); return 0
    if cmd == "test":      return subprocess.call([sys.executable, "-m", "pytest", "-q", os.path.join(ROOT, "tests")])
    print(__doc__); return 2


if __name__ == "__main__":
    sys.exit(main())
