# Walk-through cheat-sheet (be ready to explain)

**30-second pitch:** "I generate a realistic chain – stores, SKUs, shifts, employees, promotions, 1 M stock movements – while simulating *two* stock timelines: what the system recorded (book) and what is physically there. Cycle counts read the physical stock, so every variance has a known cause. I plant theft patterns and data-quality edge cases with ground-truth labels, then a separate rule engine, blind to the labels, raises evidence-based alerts that decide INVESTIGATE / DATA_FIX / AUTO-CLOSE. I validate with 203 checks, prove byte-identical reproducibility from seed 20261022 and score the detector against ground truth and a naive baseline."

## Likely questions
1. **Why two timelines?** Variance must be explainable. `variance = counted − book` and decomposes into unexplained loss + background shrink + drift + timing/posting + noise + clipping (`ground_truth_count_causes.csv`, always sums exactly).
2. **How do you avoid treating every variance as theft?** Benign explanations: documented damage incidents, in-transit transfers, legit adjustments/drift, returns, promo surges, miscount noise; detector checks them before escalating (see rule table in `detector.py`).
3. **How is ground truth kept out of features?** Separate folder/DB; `detect(t)` receives only operational tables; tests + validation check for leakage.
4. **How do you handle the 4 required edge cases?** Table in `ASSESSMENT.md` §3, each has a ground-truth label and a detection rule.
5. **What's not realistic?** Fixed planting formula, no seasonality, thresholds hand-set, only negative variances.
6. **Reproducibility?** One seeded `numpy.random.Generator`, stable sorts, no set/dict-order dependence, no timestamps in outputs → identical SHA-256 (`reproducibility_report.json`).
7. **What would you do next?** Learn thresholds / classifier on labelled alerts, add overage analysis, vendor-level receipts matching, streaming detection.
8. **Failures you hit and fixed:** see "Iterations" in `PROMPT_HISTORY.md`.
9. **Scale knobs:** `--n-stores --n-skus --n-movements --n-counts --skus-per-store --seed`.
