# AI usage disclosure

The brief allows any LLM tool provided usage is transparent. **Fill in / adjust this file with your own experience before submitting – you must be able to explain every part.**

| Area | AI assistance | What I (the candidate) must personally review / validate |
|---|---|---|
| Problem analysis & requirement matrix | Claude (Anthropic) drafted the breakdown of the brief | Re-read the brief and confirm every row of `ASSESSMENT.md` |
| Architecture (book vs physical timelines, rule set) | Claude proposed; heavily relied on | Be able to explain why variances are derived, not random |
| Code (`generator.py`, `detector.py`, `validate.py`, …) | Claude wrote the first versions; the code was run, debugged and tuned in several iterations (see `PROMPT_HISTORY.md`) | Run it, read it, change a threshold and watch the metrics move |
| Debugging / tuning | Claude diagnosed three failing validation checks and two detector weaknesses (warehouse damage baseline, ground-truth links for incidental counts) | Understand each fix (see "Iterations" in `WALKTHROUGH.md`) |
| Documentation | Claude drafted README, dictionary, assessment | Edit for your own voice and verify numbers against `data/*/evaluation_metrics.md` |

Validation of AI output: executed the pipeline at starter and full scale, 203 automated checks, 9 pytest tests, double-run checksum comparison, and manual inspection of metrics/false positives.
