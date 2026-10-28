# data/

* `starter/` – committed small dataset (10 stores, 500 SKUs, 20 k movements) produced by `python run.py starter`.
* `full_summary/` – validation, evaluation, manifest (with SHA-256 of every file) and reproducibility report of the **full** dataset (100 stores, 5,000 SKUs, 1 M movements, 20 k counts). The 150 MB CSVs are not committed; regenerate with `python run.py full` (~75 s) – the checksums in `full_summary/manifest.json` let you verify you got identical files.
* `full/` – created locally by `python run.py full` (git-ignored).
