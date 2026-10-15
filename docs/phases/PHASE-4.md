# Phase 4 · Robust at scale (in progress, not tagged)

## Done so far

- Greedy zoning baseline (`loopwright/optimize/baseline.py`); every result carries `metrics.hubs_greedy`, and the batch report sums it.
- Fault injection now also covers a repeated node (V08), a gap in a polyline (V09), a run through a window (V11) and a run outside the building (V12), on top of the earlier cases (V03-V07, V10, V14).
- Routing retry: a zone the main grid can't route is retried on a 0.1 m grid without clearance (`ROUTER_FALLBACK` diagnostic). It rescued only 1 plan, so clearance isn't the main cause (see below).

## 1,000 random plans (seed 11, strict rule)

| | |
|---|---|
| Valid on feasible plans | 939 of 970 (96.8%) |
| Infeasible, correctly flagged (room over 100 m²) | 30 |
| Hubs | 1,839 exact against a bound of 1,496 and greedy's 1,951 |
| Runtime per plan | p50 1.33 s, p95 5.42 s with 15 parallel workers on one laptop |

Report: `bench/phase4-sample1000.md`, rows in `bench/phase4-sample1000.jsonl`.

## Fix list, biggest first

| Cause | Plans | Examples | First guess |
|---|---|---|---|
| A leg can't be routed, even on the fallback grid | 23 | 11160, 407696, 742848, 384263 | Door polygons that don't fully cut their wall in the data; check `wall − door` around these doors |
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
