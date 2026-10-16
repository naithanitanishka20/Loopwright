# Phase 7 · Eval-01 fixes and cable efficiency

Tag: `phase-7`

At the Eval-01 review the organisers answered several open questions and showed how their checker computes each metric (slide 7). This phase brings the solver and the validator in line with both, then cuts cable cost.

## Exit check

| Check | Target | Result |
|---|---|---|
| Metrics exactly as slide 7 | every example on the slide | `tests/unit/test_metric_definitions.py` encodes each one |
| Every feasible plan valid under the stricter rules (new V15, V16) | all 17,000 | **16,556 of 16,556**; the other 444 each have a room over 100 m² |
| Hub count | as low as Phase 6 or lower | 29,377 against Phase 6's 29,421: 44 plans need one hub fewer (a scrap of room under 2 m² no longer counts), none more |
| Runtime target (assumptions Q12) | p95 under 2 s per plan | one process, test split: p50 0.38 s, p95 1.26 s |

## What the organisers said, and what changed

- **Metrics (slide 7).** A bend is any change of direction at a vertex, a node or the hub; a reversal counts once. Crossings and overlap count inside one ring as well as between rings, and a stretch covered by k legs counts k − 1 times its length. Within 1 mm is the same point or line. Our scorer had not counted turns at the hub, nor crossings and overlap inside a ring. It now follows the slide exactly, so J values are not comparable with earlier phases.
- **Nodes keep 0.5 m from the walls; their position is ours to choose.** New check V15. A room under 2 m², or too narrow to hold a node that far from its walls, gets no node (`ROOM_NEGLECTED`), as the organisers suggested for very small rooms.
- **A hub can't sit on a node.** It keeps 0.5 m from every node of its ring (new check V16). One test-split plan had a hub exactly on its node.
- **Bathrooms and stairs only when there is no other way.** Each zone is routed with them blocked first; only if that fails are they allowed, and the ring is reported (`THROUGH_EXCLUDED`).
- **Confirmed:** 5 nodes per hub; the test plans come from the ResPlan dataset itself; the output is the JSON and a drawing.

All answers are recorded in `docs/assumptions.md` (Q3 to Q8, Q17).

## Cable efficiency

Three changes, each kept only where it lowers J; the hub count never changes.

- **Nodes near the doors.** A ring has to reach every node through its room's doors, so each node now sits at the point at least 0.5 m from the walls with the least total distance to the room's openings: just inside the door of a one-door room. Before, nodes sat at room centres.
- **The cheapest of the equal-hub groupings.** When several groupings reach the minimum hub count, each zone is costed by the cheapest closed tour through its nodes and the cheapest grouping wins.
- **Separate lanes.** After the rings are built, each leg is routed again with every stretch already covered costing what J charges for overlap, and every meeting with placed cable costing a crossing. Legs move to a parallel lane where that is cheaper, and a ring keeps its new legs only if J drops.

Test split, each change on top of the last (same 2,834 hubs throughout, every feasible plan valid, all scored as slide 7):

| Step | J | Cable | Overlap | Crossings |
|---|---:|---:|---:|---:|
| Rule fixes, nodes at room centres | 88,912 | 55,016 m | 11,806 m | 1,128 |
| + nodes near the doors | 56,703 | 33,031 m | 8,204 m | 779 |
| + cheapest of the equal-hub groupings | 52,281 | 30,246 m | 7,515 m | 725 |
| + separate lanes | **42,409** | 30,628 m | 324 m | 1,513 |

J falls by 52%. Lanes trade overlap for crossings where that is cheaper: a crossing costs 3, overlap 2 per metre.

## Results (`bench/results.md`)

All 17,000 plans: **16,556 of 16,556 feasible plans valid**; 29,377 hubs against a lower bound of 23,893 and greedy's 31,046; 12,906 plans meet the bound. Cable 323,483 m against Phase 6's 581,587 m (−44%, the same measure in both). J = 446,668 under slide 7's rules.

Runtime: one process, test split, p50 0.38 s and p95 1.26 s; with 4 workers, p50 0.13 s and p95 0.47 s per plan across all 17,000. The laptop ran slower this afternoon than for Phase 6's figures; on the same 60 test plans back to back, Phase 6's code took a median 0.38 s per plan and Phase 7's 0.47 s (the lane pass and the grouping search).

## Run

```bash
loopwright batch --split test --workers 1 --report bench/latency-test.md
loopwright batch --split test --workers 4 --report bench/test-split.md     # and val, augmented, train
loopwright results bench/test-split.jsonl bench/val-split.jsonl bench/augmented-split.jsonl bench/train-split.jsonl
loopwright charts bench/test-split.jsonl bench/val-split.jsonl bench/augmented-split.jsonl bench/train-split.jsonl --runtime bench/latency-test.jsonl
python -m pytest -q                                                      # 259 tests
```

To compare with the earlier placement and routing in code: `Settings(node_rule="pole", separate_lanes=False)`.

## Known gaps

- Slide 5's test case still needs the room coordinates from the organisers' slide.
- The J weights (assumptions Q2) are still our assumption.
- A room whose only door is too narrow for two lanes still retraces it.
