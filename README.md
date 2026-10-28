# Inventory Shrinkage Detection – YottaFlex Round 2 Code Challenge

Detect **unusual inventory loss** by comparing receipts, sales, transfers, adjustments, returns and cycle counts.
End-to-end, fully synthetic, deterministic (seed **20261022**), Python + numpy/pandas only.

```
generate master data → baseline events → plant labelled anomalies → derive counts/variances
      → rule-based detector (blind to ground truth) → alerts + evidence → lifecycle history
      → validation (203 checks) → evaluation vs ground truth → export CSV/JSON/SQLite/SQL + manifest
```

| | Starter | Full (the brief) |
|---|---|---|
| Stores / SKUs | 10 / 500 | **100 / 5,000** |
| Movements / counts | 20,000 / 500 | **1,000,000 / 20,000** |
| Run time | ~3 s | ~75 s (needs ~3 GB RAM) |

Documents: [`docs/ASSESSMENT.md`](docs/ASSESSMENT.md) (what was asked, our approach, traceability) · [`docs/DATA_DICTIONARY.md`](docs/DATA_DICTIONARY.md) · [`docs/AI_USAGE.md`](docs/AI_USAGE.md) · [`docs/PROMPT_HISTORY.md`](docs/PROMPT_HISTORY.md) · [`docs/WALKTHROUGH.md`](docs/WALKTHROUGH.md)

---

## 1. Run it in VS Code (Windows / macOS / Linux)

Requirements: **Python 3.10+** (tested on 3.12; numpy 2.x, pandas 3.x tested; minimum numpy 1.26 / pandas 2.2).

1. `File → Open Folder…` → select the folder **`inventory-shrinkage-detection`**.
2. Open the terminal: `` Ctrl+` `` (View → Terminal).
3. Create & activate a virtual environment, install dependencies:

**Windows (PowerShell)**
```powershell
python -m venv .venv
.venv\Scripts\Activate.ps1          # if blocked:  Set-ExecutionPolicy -Scope Process Bypass
pip install -r requirements.txt
```
**macOS / Linux**
```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```
4. In VS Code press `Ctrl+Shift+P → Python: Select Interpreter` → choose `.venv`.
5. Run:

```bash
python run.py starter           # small dataset (≈3 s)  -> data/starter
python run.py full              # 100 stores / 5,000 SKUs / 1 M movements / 20 k counts -> data/full
python run.py reproduce         # regenerate starter twice, compare row counts + SHA-256
python run.py reproduce-full    # same for the full dataset (≈4 min)
python run.py test              # 9 pytest tests
```
(Windows: use `python`; macOS/Linux: `python3` if `python` is not found.)
You can also use **Run and Debug (▶, Ctrl+Shift+D)** – launch configurations are in `.vscode/launch.json`.

Direct CLI (same thing, with scale overrides):
```bash
cd src
python -m shrinkage generate --profile full --out ../data/full
python -m shrinkage generate --profile starter --seed 42 --n-movements 50000 --out ../data/custom
python -m shrinkage validate --out ../data/full
```

## 2. What you get (`data/<profile>/`)

| Path | Content |
|---|---|
| `input/*.csv` | 17 operational tables (stores, skus, store_skus, employees, employee_roles, shifts, promotions, promotion_skus, **inventory_movements**, **cycle_counts**, returns, **shrinkage_alerts**, alert_evidence, alert_status_events, **investigations**, investigation_alerts, investigation_events) |
| `ground_truth/` | `ground_truth_cases.csv/.json`, `ground_truth_links.csv`, `ground_truth_alert_labels.csv`, `ground_truth_count_causes.csv` – **never used by the detector** |
| `sql/` | `schema.sql`, `inventory.db` (SQLite with PK/FK), `ground_truth.db`, `seed_data.sql` (starter only) |
| `validation_summary.md/.json` | 203 PASS/FAIL checks + row counts |
| `evaluation_metrics.md/.json` | detector vs ground truth, per issue type, vs naive baseline |
| `manifest.json` | generator command, seed, versions, file sizes, row counts, SHA-256, provenance |
| `reproducibility_report.json` | two-run comparison (after `reproduce`) |

Try it in SQL after running `python run.py starter` (`sqlite3 data/starter/sql/inventory.db`; the .db files are built on every run):
```sql
-- alerts to investigate, newest first, with their evidence
SELECT a.alert_id, a.alert_type, a.severity, a.estimated_loss_value, a.reason_text
FROM shrinkage_alerts a WHERE recommended_action='INVESTIGATE' ORDER BY created_ts DESC LIMIT 5;
-- stock equation for one store/SKU
SELECT s.opening_qty + SUM(m.quantity_signed) AS closing
FROM store_skus s JOIN inventory_movements m USING(store_id, sku_id)
WHERE s.store_id='STORE-000002' AND s.sku_id=(SELECT sku_id FROM store_skus WHERE store_id='STORE-000002' LIMIT 1);
```

## 3. Design in brief

* **Two timelines per store/SKU.** *Book* = opening + recorded movements (by `posted_ts`). *Physical* = opening + physical effect of movements (by `movement_ts`) + **unrecorded** events. A cycle count reads the physical stock; `variance = counted − book`. Every variance is therefore *derived* and decomposes exactly into causes (`ground_truth_count_causes.csv`).
* **Planted patterns** (expected decision `INVESTIGATE`): `UNEXPLAINED_LOSS`, `REPEATED_ADJUSTMENTS`, `RETURN_WITHOUT_SALE_ABUSE`, `UNAUTHORIZED_ADJUSTMENT`.
* **Required edge cases** (`DATA_FIX` / benign): `MOVEMENT_WRONG_STORE`, `ADJUSTMENT_NO_REASON`, `COUNT_TIMESTAMP_PRECEDES_MOVEMENT`, `TRANSFER_IN_TRANSIT_BOTH_ENDS`; plus benign trap `LEGIT_DAMAGE_EVENT`.
* **Benign explanations modelled everywhere:** recorded damage, documented incidents, customer returns (restock / write-off / manager-approved no-receipt), promotion surges, goods in transit, small background shrink, miscounts, legitimate adjustments.
* **Detector rules R01–R08** (`src/shrinkage/detector.py`) → decision `INVESTIGATE` / `DATA_FIX` / `AUTO_CLOSE_BENIGN`, each alert with evidence rows and a reason text quoting record IDs.
* **Lifecycles** are append-only event tables (alerts, investigations); the status column always equals the last event.

IDs follow the brief (`STORE-000001`, `SKU-000001`, `MOV-2026-00000001`, `CNT-2026-000001`, `SHR-2026-000001`, `INV-2026-000001`) plus the same zero-padded style for the extra entities (`EMP-`, `ERL-`, `SHIFT-`, `PROMO-`, `XFR-`, `RET-`, `GT-`).

## 4. Results on the full dataset (seed 20261022)

| Metric | Value |
|---|---|
| Movements / counts / alerts | 1,000,000 / 20,000 / 735 (490 DATA_FIX, 187 INVESTIGATE, 58 AUTO_CLOSE_BENIGN) |
| Validation | **203 / 203** checks pass |
| Precision of INVESTIGATE alerts | **96.8 %** |
| Recall of planted theft cases | **100 %** (all 12 + 10 + 6 + 60 cases) |
| Benign traps wrongly escalated | **0 of 33** |
| Edge cases routed to DATA_FIX | **490 / 490** |
| Naive baseline ("every count ≤ −3 units is theft") | 51 % precision, flags 78 benign-trap counts |
| Reproducibility | identical row counts and SHA-256 across 2 runs |

See `data/full_summary/` for the committed summary files (the 150 MB CSVs are regenerated with one command and are git-ignored).

## 5. Assumptions & limitations
Documented in [`docs/ASSESSMENT.md`](docs/ASSESSMENT.md) §4–5. Highlights: threshold-based rules (no ML); only negative variances escalated; planted volumes are formula-driven; opening balances are sized in a planning pass so stock never goes negative; all data are synthetic (no external sources, no personal data).

## 6. Submission checklist
- [ ] Create a **new public GitHub repo**, push this folder (`git init && git add . && git commit -m "Initial submission" && git remote add origin <url> && git push -u origin main`).
- [ ] Edit `docs/AI_USAGE.md` and `docs/PROMPT_HISTORY.md` with your own prompts/notes.
- [ ] Send the repo link from the email address you used during recruitment, before the 72-hour deadline.
- [ ] Re-read `docs/WALKTHROUGH.md` and be ready to explain your decisions.
