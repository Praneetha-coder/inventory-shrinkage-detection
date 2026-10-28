# Assessment of the task and our approach

## 1. What YottaFlex asked for

**Round 2 – 72-hour code challenge: "Detect unusual inventory loss by comparing receipts, sales, transfers, adjustments, returns and counts."**
Role: Associate AI Forward Deployed Engineer.

| Area | Requirement (from the brief) |
|---|---|
| Deliverable | A *working, end-to-end* solution of medium complexity: multiple related entities, conditional rules, ≥1 exception path, meaningful evaluation metrics; exposes decisions & exceptions, preserves traceability, produces measurable outputs |
| Entities | Store, SKU, InventoryMovement, CycleCount, EmployeeRole, Shift, Promotion, Return, ShrinkageAlert, Investigation – each with PK, FKs, cardinality, optional relationships, effective dates, lifecycle states; bridge tables for M:N; history kept (no overwrites) |
| IDs | `STORE-000001`, `SKU-000001`, `MOV-2026-00000001`, `CNT-2026-000001`, `SHR-2026-000001`, `INV-2026-000001`; zero-padded, immutable, consistent across files |
| Data generation | 10 documented steps: data dictionary → parents before children → deterministic IDs → **100 stores / 5,000 SKUs / 1 M movements / 20,000 counts** with fixed seed (e.g. 20261022) and scale parameters → valid baseline first, then labelled edge cases → derived values computed from source records → separate ground truth → validation → export CSV/JSON/SQL + README, dictionary, command, seed, manifest, validation summary → regenerate twice and compare checksums |
| Required edge cases | movement refers to wrong store; adjustment lacks reason; count timestamp precedes stock movements; transfer counted as shrinkage at both ends |
| Acceptance | stock equation reconciles; alert reasons are evidence-based; planted patterns can be evaluated; benign explanations are represented (damage, returns) |
| Evaluation focus | realistic distributions; consistent IDs/valid joins; lifecycle consistency; correct derived values; normal/boundary/failure/exception coverage; separate ground truth; reproducibility, documentation, lawful provenance |
| Lawful data | External data optional; if used record URL/version/licence/etc. Otherwise synthetic |

**Submission rules (Guidelines + FAQ):** 72 h from the send timestamp; new *public* GitHub repo; runnable code with setup steps; meaningful commits; **full prompt history** for every AI tool and an explanation of where AI helped; reasoning, assumptions, trade-offs, testing and limitations must be visible; work must be individual; no secrets/personal data; no hosted demo or automated tests mandatory (we provide tests anyway); be ready to walk through the solution.

## 2. Our approach in one paragraph

We built a **synthetic-data generator + rule-based shrinkage detector + validator + evaluator** in Python (numpy/pandas only). The generator keeps two stock timelines for every store/SKU: the **book** (what the system recorded) and the **physical** stock (what is really on the shelf, including unrecorded losses). A cycle count observes the physical stock, so every variance is *derived* and decomposes exactly into causes. Planted patterns and edge cases are created by reserving rows of the matching baseline type, rewriting them, and logging a labelled ground-truth case. A separate detector – which cannot see ground truth – applies eight rules with benign-explanation checks, raises alerts with evidence, and a lifecycle builder produces append-only alert / investigation histories. The evaluator then scores decisions against ground truth and against a naive baseline.

## 3. Requirement → implementation traceability

| Requirement | Where / how |
|---|---|
| 10-entity model, PK/FK, cardinality, bridge tables | `src/shrinkage/schema.py` (single source) → `docs/DATA_DICTIONARY.md`, `sql/schema.sql`. Extra tables: `employees`, `store_skus` (Store N:M SKU + opening balance), `promotion_skus`, `alert_evidence`, `investigation_alerts`, `alert_status_events`, `investigation_events` |
| Effective dates & lifecycle | `employee_roles` (trainee → role history), `store_skus`, `stores`, promotions; alert and investigation state machines with event tables |
| No overwritten history | movements are an immutable ledger; corrections/adjustments are new rows; status changes are event rows |
| Deterministic IDs | `ids()` helper; movements/counts/alerts numbered in posted/count/created time order; validation checks contiguity & regex |
| Volumes + seed + scale parameters | `config.py` (`starter` vs `full`, same generator); seed 20261022 |
| Master → child order | stores, SKUs, employees/roles, shifts, assortment, promotions → movements → counts/returns → alerts → investigations |
| Opening balances, sales/movement events, counts, variances | opening qty sized in a planning pass so neither book nor physical stock goes negative; counts derived from the two timelines |
| Movements linked to roles & shifts | every movement has `shift_id` + `employee_id`; shift roster rotates 8 employees/store; adjustments require manager-level roles |
| Patterns injected | UNEXPLAINED_LOSS, REPEATED_ADJUSTMENTS, RETURN_WITHOUT_SALE_ABUSE, UNAUTHORIZED_ADJUSTMENT |
| 4 required edge cases | MOVEMENT_WRONG_STORE, ADJUSTMENT_NO_REASON, COUNT_TIMESTAMP_PRECEDES_MOVEMENT, TRANSFER_IN_TRANSIT_BOTH_ENDS |
| Benign explanations | recorded damage, documented damage incidents, customer returns (restock + write-off, approved no-receipt), promotions surges, in-transit transfers, normal background shrink & miscounts, legit adjustments |
| Derived values from source | book qty, variance, value, status, refund, min stock level, severity, risk score, alert loss, investigation totals – all recomputed independently in `validate.py` |
| Ground truth separate, never leaked | `ground_truth/` folder + `ground_truth.db`; detector signature takes only operational tables; validation + tests assert no leakage |
| Validation (Step 8) | `validate.py` – 203 checks (PK, FK, enums, date order, arithmetic, lifecycle, duplicates, anomaly reconciliation) |
| Exports (Step 9) | CSV, JSON (ground-truth cases), SQLite DBs, `schema.sql`, `seed_data.sql` (starter), README, data dictionary, `manifest.json` (command, seed, versions, SHA-256) |
| Reproducibility (Step 10) | `python run.py reproduce[-full]` → `reproducibility_report.json` |
| Evidence-based alerts | `alert_evidence` rows + `reason_text` quoting record IDs and numbers |
| Provenance | 100 % synthetic; no external data; stated in `manifest.json` |

## 4. Key assumptions & design decisions

1. **Book vs physical timelines** instead of random variances – makes the stock equation reconcile and lets us *prove* each count variance cause.
2. **Assortment:** each store carries 1,000 of the 5,000 SKUs (warehouses 2,000) so that 1 M movements give ≈10 movements per store/SKU – enough history for meaningful counts.
3. **Opening balance sizing:** computed in a planning pass from the planned events (documented deviation from the literal "opening first" order); it guarantees no negative stock and is stored as a master/bridge field.
4. **Anomalies consume baseline budget**: totals stay exactly 1,000,000 movements; each altered row has a ground-truth link, so unrelated rows are never silently corrupted.
5. **Transfer "shrinkage at both ends"** is modelled as goods in transit: OUT posted late at the source, IN posted early at the destination, counts taken in between → both ends short by the same quantity. The detector recognises it by the posted-vs-movement timestamp straddling the count time.
6. **Count-timestamp anomaly:** the recorded `count_ts` is 1–3 h earlier than a sale the physical count already reflected; detected through `entered_ts − count_ts` and a movement posted in between.
7. **Alert decisions**: `INVESTIGATE`, `DATA_FIX` (exception path), `AUTO_CLOSE_BENIGN`. Data-quality alerts do not become theft allegations.
8. **Investigation outcomes** are simulated from the true cause of the matched case (documented in `lifecycle.py`); the detector never sees them.
9. Currency USD; timestamps naive local store time; all people are synthetic (no PII).

## 5. Known limitations / next steps (honest)

- Rules are threshold-based (no ML). Thresholds are in `detector.TH`; a next step is learning them or adding a classifier trained on `ground_truth_alert_labels`.
- Only negative variances are escalated; overages are not analysed.
- Planted-case volumes are fixed by formula; real shrink is messier (seasonality, vendor fraud, ORC).
- A small number of INVESTIGATE false positives remain by design (miscounts, drift) – they show realistic precision < 100 %.
- ID prefixes `XFR-`, `EMP-`, `ERL-`, `SHIFT-`, `PROMO-`, `RET-`, `GT-` are our own, following the same zero-padded convention, because the brief defined only six.
- Automated tests are included but the brief did not require them; no hosted demo.
