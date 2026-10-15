# Phase 4 · Robust at scale (in progress, not tagged)

## Done so far

- Greedy zoning baseline (`loopwright/optimize/baseline.py`); every result carries `metrics.hubs_greedy`, and the batch report sums it.
- Fault injection now also covers a repeated node (V08), a gap in a polyline (V09), a run through a window (V11) and a run outside the building (V12), on top of the earlier cases (V03-V07, V10, V14).
- Routing retry: a zone the main grid can't route is retried on a 0.1 m grid without clearance (`ROUTER_FALLBACK` diagnostic). It rescued only 1 plan, so clearance isn't the main cause (see below).

- Windows now block passage in the door graph and in the validator's own link test. Before, a window in a wall read as an open passage, so rooms reachable only through a window were zoned with neighbours they can't be cabled to. This fixed 10 of the 1,000 plans.

## 1,000 random plans (seed 11, strict rule)

| | |
|---|---|
| Valid on feasible plans | 949 of 970 (97.8%), up from 939 before the window fix |
| Infeasible, correctly flagged (room over 100 m²) | 30 |
| Hubs | 1,849 exact against a bound of 1,496 and greedy's 1,959 |
| Runtime per plan | p50 1.01 s, p95 4.58 s with 15 parallel workers on one laptop |

Report: `bench/phase4-sample1000.md`, rows in `bench/phase4-sample1000.jsonl`.

## Fix list, biggest first

| Cause | Plans | Examples | First guess |
|---|---|---|---|
| A leg can't be routed, even on the fallback grid (was 23 before the window fix) | 15 | 407696, 742848, 1180, 384263 | Checked 11160 with `scripts/diagnose_unreachable.py`: every door cuts its wall fully, but the walkable area splits in two and the kitchen (7.3 m²) sits alone. Its only link is probably an interior "window", which ResPlan's tools treat as a misclassified door. Rule question, logged as Q15 in `docs/assumptions.md`; until answered, report these rooms as unreachable instead of emitting an invalid leg |
| V10 or V12 on plans that also need extra hubs | 5 | 624783, 557925, 3328, 682851 | Same as above, or a stranded room reached through a wall |
| Solver and validator disagree on a passage (V05) | 2 | 15258, 11912 | Align the two passage tests or log the disagreement |
| Room with no detected door | 1 | 10216 | Door detector miss |

## Still to do

- Work through the fix list above (`/investigate`, test first).
- V13 (space changes only at portals).
- Two lanes per door; hubs placed on their own ring; turns at nodes in the ring-order cost.
- The organisers' slide 5 layout as a test case.
- Viewer v1.
- Fetch ResPlan's `split.json` and run the test split (1,632 plans) every four hours.
