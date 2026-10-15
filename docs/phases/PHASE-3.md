# Phase 3 · Correct routes

Tag: `phase-3`

## Delivered

- `loopwright/geometry/portals.py`: door graph from doors, open passages and unlabelled corridor pockets.
- Zones follow the zone rule (`--zone-link strict | circulation | through_rooms`, assumptions Q1). The hub count is the exact minimum under that rule; `EXTRA_HUB` diagnostics name every room stranded in its own zone, and `NO_LINK` names rooms with no detected door.
- `loopwright/routing/grid.py`: axis-aligned router on a grid through every stop's exact coordinates, with exact bend costs (search over vertex and heading). No grid edge can cross a wall.
- Ring order is exact: every permutation of a zone's nodes (120 at most) is costed with the router.
- Validator V05: zone connectivity checked with the validator's own passage test (independent of the solver's door graph).
- `loopwright batch`: runs a sample or all plans in parallel and writes a report grouped by cause.

## Results (100 random plans, seed 7, strict rule)

| | |
|---|---|
| Valid | 97 of 100 |
| Hubs | 171 against a lower bound of 143 |
| Runtime per plan | p50 0.19 s, p95 0.60 s |

Report: `bench/phase3-sample100.md`. Failures, one each: `16789` (room with no detected door, fallback leg crosses a wall), `1364` (solver and validator disagree on a passage, V05), `423284` (a leg the router can't reach).

## Run

```bash
loopwright solve --id 16448 --out out/                          # 4 hubs, strict rule
loopwright solve --id 16448 --zone-link through_rooms --out out/  # 2 hubs
loopwright batch --sample 100 --seed 7 --workers 8 --report bench/report.md
python -m pytest -q                                             # 28 tests
```

## Known gaps (next phases)

- The organisers' slide 5 layout isn't typed in yet, so "slide 5 solved with 2 hubs" is still open.
- V13 (space changes only at portals) is not checked yet.
- Hubs still sit 0.6 m from the main room's node; placing them on their own ring comes later.
- Ring order ignores turns at nodes; doors don't yet carry two separate lanes, so a ring can reuse its own path through a door.
- No crossing or overlap refinement between rings (Phase 5).

## Testers: try to break

- Batch: `loopwright batch --sample 300 --seed <your own>`; group the failures.
- The three failing plans above: is each a detector bug, a router bug or a validator bug? Write the failing test first.
- Properties: every returned path is axis-aligned, starts and ends on its stops, and stays inside the walkable region; cost(a, b) equals cost(b, a).
- Visual: open `out/16448.svg` with both zone rules; check routes pass only through door gaps.
- Security: `batch` loads the whole dataset; check memory and time limits on a crafted or huge file.
- Architecture: is `solve.py` getting too big? Should routing sit behind an interface so the planned Hanan-grid router can replace this one?
