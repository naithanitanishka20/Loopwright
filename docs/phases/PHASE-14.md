# Phase 14 · Rooms a door joins share a hub

Tag: `phase-14`

Phase 13 left one known fault: on 10 ResPlan plans, and on a hand-drawn three-room image, rooms the door graph joins ended up in separate walkable areas, so each got a hub of its own. A survey of all 17,000 plans then listed every plan where walls cost hubs. Each is now either fixed or confirmed as right.

## What was wrong

- **Living rooms drawn in parts.** ResPlan draws some living rooms in pieces that walls separate (plans 1180, 8111). The living room's one node went to the larger piece while the bedrooms open onto the smaller. A room drawn in parts now puts its node in the part that lets the zones use the fewest hubs, and stays put on a tie; `NODE_MOVED` says why. A part too narrow to hold a node 0.5 m from its walls is never chosen.
- **Doors drawn short of their wall.** Some doors are drawn shallower than the wall they sit in (plan 4755: 3 cm short; 1205, 12736 and 9313 likewise), and on the hand-drawn image a door ends at x = 7.699999999999999 in a wall that ends at 7.7. Cutting the door out of the wall left a strip of wall across the doorway, which parted the rooms or narrowed the door to a crack the router could not use. A door now opens the wall it is drawn in from face to face (assumptions Q18): wall left within half a wall depth of its face, along its whole width, is doorway too. A wall that only meets the door's side keeps its end; a first version cut that too (plan 7857), which opened a gap no drawing has and moved nodes towards it.
- **Four copies of "walls minus doors".** The walkable area, the router, the node placer and the validator each cut doors out of walls their own way. The first three now share one helper (`open_walls`); the validator keeps its own copy, as it must, and reads doors the same way.
- **Greedy ignored walls.** The greedy baseline grouped any rooms the door graph links, so on plans like 5213 it reported fewer hubs than any design can have. It now joins only the rooms the exact search may: linked, in one walkable area, and routable.

## Plans that keep their extra hubs

Walls really part these rooms, so the solver is right:

- **5213**: the kitchen opens onto the living room only through an interior window (Q15).
- **12735**: the bedrooms open onto a 1 m² hallway that walls seal off from the rest; the drawing has no door into it.
- **2558, 2559, 5575**: a part of the living room, walled off from the rest, holds a bedroom's only door. Moving the living room's node there would strand the rooms on the other side.
- **14245**: bedroom 3's only way to the kitchen is a 12 cm slot where two walls fail to meet. No cable follows it, and the repair pass gives bedroom 3 its own hub.

## Exit check

| Check | Target | Result |
|---|---|---|
| The hand-drawn image | three rooms, one hub | passes; its expected-failure mark is gone |
| The ten plans | each fixed or explained | 1180, 8111, 4755, 12736 and 9313 now get the 1 hub their lower bound allows; the other five are listed above |
| Every plan | all feasible plans valid | **16,556 of 16,556**; the other 444 each have a room over 100 m² |
| Hubs | fewer than Phase 13's 29,377 | **29,369**, eight fewer: 1180 (4 to 1), 8111 (3 to 1), 4755, 9313 and 12736 (2 to 1); 12,911 plans meet the bound |
| Greedy | never below the exact search for want of walls | 31,052; level with or above the exact search on every plan (below on ten before) |
| Tests | each fix guarded | 7 new tests on ResPlan plans and 7 synthetic ones; 12 of 12 mutants caught, each by the test written for it |

## Results

| Run | Plans | Feasible | Valid | Hubs | Lower bound | Greedy | Above bound | Cable m | Bends | Crossings | Overlap m | J | p50 s | p95 s |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| test-split | 1,632 | 1,588 | 1,588 (100.0%) | 2,834 | 2,295 | 2,983 | 367 | 30,639.9 | 21,969 | 1,514 | 324.4 | 42,424.1 | 0.13 | 0.43 |
| val-split | 1,632 | 1,591 | 1,591 (100.0%) | 2,850 | 2,307 | 3,019 | 373 | 30,957.8 | 22,053 | 1,395 | 327.6 | 42,420.1 | 0.14 | 0.44 |
| augmented-split | 683 | 667 | 667 (100.0%) | 1,183 | 966 | 1,256 | 148 | 13,298.8 | 9,175 | 612 | 204.9 | 18,298.7 | 0.15 | 0.48 |
| train-split | 13,053 | 12,710 | 12,710 (100.0%) | 22,502 | 18,325 | 23,794 | 2,757 | 248,660.8 | 175,867 | 12,120 | 2,888.8 | 343,589.8 | 0.14 | 0.46 |
| all | 17,000 | 16,556 | 16,556 (100.0%) | 29,369 | 23,893 | 31,052 | 3,645 | 323,557.3 | 229,064 | 15,641 | 3,745.7 | 446,732.7 | 0.14 | 0.46 |

J rose by 64.8 in all (0.015%). The five plans that now need fewer hubs carry longer rings (45.3 of it), and on 64 plans with the same hub count the nodes moved: Q6 puts a node nearest its room's doors, and doors that were drawn short now count. Among groupings with the same hub count the solver picks by a cable estimate before routing, so a moved node can tip it to a grouping that routes worse (plan 15985: J 25.9 to 38.3) or better (plan 1205: 35.2 to 19.8). Runtime, one process on the test split: p50 0.15 s, p95 0.64 s.

## Run

```bash
python -m pytest -q
loopwright batch --split test --workers 4 --report bench/test-split.md     # and val, augmented, train
loopwright batch --split test --workers 1 --report bench/latency-test.md
loopwright results bench/test-split.jsonl bench/val-split.jsonl bench/augmented-split.jsonl bench/train-split.jsonl
loopwright charts bench/test-split.jsonl bench/val-split.jsonl bench/augmented-split.jsonl bench/train-split.jsonl --runtime bench/latency-test.jsonl
loopwright site
```
