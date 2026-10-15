# Phase 4 · Robust at scale

Tag: `phase-4`

## Exit check

| Check | Target | Result |
|---|---|---|
| Feasible plans valid on the ResPlan test split | at least 99% | **1,588 of 1,588 (100%)** |
| Every failure has a named cause | yes | yes: the 44 remaining are all `ROOM_OVER_CAP` (a room over 100 m², correctly reported as infeasible) |
| Hub count equals the exact minimum | every plan | yes: exact subset search, property-tested against brute force with and without door links |

Test split numbers (`bench/test-split.md`): hubs 3,038 against a lower bound of 2,438 and greedy's 3,187. Runtime per plan p50 0.24 s, p95 0.80 s with 15 workers on one laptop. A separate 1,000-plan random sample (`bench/phase4-sample1000.md`): 970 of 970 feasible plans valid.

## Delivered

- **Building outline repair** (assumptions Q16): in about 1.5% of ResPlan plans `inner` leaves out parts of rooms (plan 407696: 12 of the living room's 22 m²). The outline is widened to cover every room and door, and `INNER_REPAIRED` is reported. This was the main cause of unreachable legs.
- **Walkable zoning**: rooms share a hub only if their nodes lie in one walkable area; nodes and hubs are placed where cable can reach (`NODE_MOVED`, `ROOM_NOT_WALKABLE`).
- **Windows block passage** in the door graph and in the validator, so a window in a wall no longer reads as an open passage (assumptions Q15).
- **Validator v1, all 15 rules**: V13 (space changes only at doors or open passages at least two wall depths long) is new; doors through thick walls now link rooms; failing checks carry `where: [{ring, leg}]`.
- **Fault injection** for every rule family: V03-V14, including a crack in a wall that is neither a door nor a passage (V13).
- **Greedy baseline** in every result (`metrics.hubs_greedy`) and in batch reports.
- **Batch on ResPlan splits**: `loopwright batch --split test` (also `val`, `train`, `augmented`), using `data/split.json`.
- **Viewer v1**: `loopwright solve` also writes `<id>.html`, a self-contained page with layer toggles, ring-by-ring animation, the per-hub summary, the reviewer checklist, diagnostics and a validator panel. Clicking a failed rule highlights its legs. `loopwright index out/` writes `out/index.html` listing every solved plan.
- **Browser tests** with Playwright (`tests/e2e/`), including a script-injection test.
- `scripts/diagnose_unreachable.py` for the next failure investigation.

## Run

```bash
python scripts/fetch_resplan.py                       # ResPlan.zip and split.json
loopwright solve --id 16448 --out out/                 # JSON, SVG and the viewer page
loopwright index out/                                  # out/index.html
loopwright batch --split test --workers 8 --report bench/test-split.md
python -m pip install -e ".[e2e]"                      # Playwright for the browser tests
python -m pytest -q                                    # unit, golden, property and browser tests
```

## Testers: try to break

- **Batch**: run `--split val` and `--split train` (13,053 plans) and report any cause other than `ROOM_OVER_CAP`.
- **Viewer**: open `out/<id>.html` for a few plans; toggle layers, play rings, click every red rule. Try a narrow window and dark mode.
- **Security**: the viewer embeds plan data. Try to inject markup or script through an organisers' JSON (room keys, plan id) and through `--out`.
- **Properties**: moving a valid leg by a whole grid step inside the same room should never break V10-V14; any diagonal must fail V14.
- **Architecture**: the validator still imports nothing from `geometry`, `routing` or `optimize`; `solve.py` is now the biggest module.

## Open questions for the organisers

Q15 (interior windows) and Q16 (rooms outside `inner`) were added to `docs/assumptions.md`.

## Next (Phase 5)

Negotiated rerouting for crossings and overlaps, two lanes per door, hubs placed on their own ring, turns at nodes in the ring-order cost, top-five rescoring, viewer v2 (sliders, zone-rule switch, drag a hub, "why this many hubs"), the cable schedule, and the organisers' slide 5 layout as a test case.
