# Phase 6 · Results and demo

Tag: `phase-6`

## Exit check

| Check | Target | Result |
|---|---|---|
| Every ResPlan plan solved and checked | all 17,000 | **16,556 of 16,556 feasible plans valid**, in every split; the other 444 each have a room over 100 m² and are flagged infeasible |
| Results table from the batch records | yes | `bench/results.md`: one row per split and one for all 17,000 |
| Figures for the slides | yes | `docs/figures/extra-hubs.svg` and `docs/figures/runtime.svg`, from `loopwright charts` |
| Runtime against the planning target (assumptions Q12) | p95 under 2 s per plan | one process, test split: p50 0.13 s, p95 0.54 s |
| Demo script with numbers from the results table | yes | `docs/DEMO.md` |

## Results

All 17,000 plans (`bench/results.md`):

- **Hubs**: 29,421 against a lower bound of 23,920 and greedy's 31,111. 12,893 plans meet the bound; 3,663 need more.
- **Cable** over the valid plans: 581,587 m and 212,361 bends, J = 645,322.
- Rings cross on 7 plans and share 2.9 m of route on 5; J counts both.
- Hub totals in `results.md` count feasible plans only. The per-split batch reports (`bench/*-split.md`) also count the relaxed designs of infeasible plans, so their totals are higher (test split: 3,038 against 2,835).
- The batch records were made with 4 workers on one laptop on mains power. The runtime figure comes from a separate one-process run of the test split (`bench/latency-test.jsonl`), so parallel workers don't inflate it.

## Delivered

- `loopwright charts` writes the two slide figures from batch records: plans by hubs above the lower bound, exact against greedy; and the share of plans solved within each time, with p50 and p95 marked. The time axis stops just above the 99th percentile and names the slowest plan, so one outlier can't flatten the curve.
- `loopwright results` adds a row for all runs together.
- Batch records and reports for every split in `bench/`, all from the final code.
- `docs/DEMO.md`: the five-minute demo, what to have ready, and what to do if something fails.
- README: the results and both figures. Its claim about the validator is now exact: the validator imports nothing from the solver (the solver does reuse the validator's scorer).

## Run

```bash
loopwright batch --split test --workers 1 --report bench/latency-test.md
loopwright batch --split test --workers 4 --report bench/test-split.md     # and val, augmented, train
loopwright results bench/test-split.jsonl bench/val-split.jsonl bench/augmented-split.jsonl bench/train-split.jsonl
loopwright charts bench/test-split.jsonl bench/val-split.jsonl bench/augmented-split.jsonl bench/train-split.jsonl --runtime bench/latency-test.jsonl
python -m pytest -q                                                      # 223 tests
```

## Known gaps

- Slide 5's test case still needs the room coordinates from the organisers' slide.
- Rerouting one ring around another would remove the crossings and overlap on those 12 plans, worth about 27 m of J across all 17,000; it was left for now.
- The slides and the backup video are made by the team.
