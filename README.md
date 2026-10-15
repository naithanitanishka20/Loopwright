# Loopwright

Hub placement and closed-ring cable routing on residential floor plans.

Given a floor plan, Loopwright decides how many hubs, where each goes, which rooms and nodes each serves, the visiting order, and an axis-aligned cable route for every closed ring. Designs are ranked the organisers' way: fewest hubs first, then lowest cost J. Every output is re-checked by an independent validator (rules V00-V14) that shares no code with the solver.

## Setup

```bash
python -m venv .venv
.venv/Scripts/activate                               # Windows
source .venv/bin/activate                            # macOS/Linux
python -m pip install -e ".[dev,import,serve]"
python scripts/fetch_resplan.py                      # data/ResPlan.zip (~100 MB, not committed) and split.json, SHA-256 checked
python -m pytest -q
```

Extras: `import` reads DXF, images and PDFs; `serve` runs the app; `e2e` adds Playwright for the browser tests. Each download is refused unless its SHA-256 matches the pinned digest; pass `--sha256` or set `LOOPWRIGHT_RESPLAN_SHA256` to trust a different archive.

## The app

```bash
loopwright serve                                     # http://127.0.0.1:8000/
```

- **Plan by id**: any ResPlan plan, under any zone rule.
- **Upload**: a PNG, JPEG or PDF of a clean, straight-on drawing, with its scale (metres per pixel, the PDF drawing ratio, or the flat's area); or a DXF in the layer convention below. Imported room types are guesses: check them in Edit mode.
- **Draw**: drag rooms on a 0.5 m grid, tick the doors between neighbours, solve.
- **Edit**: click a door to remove it, connect two rooms, change a room's type; every change is re-solved and re-validated.
- **Cut cable**: cut any leg of a ring and see which side feeds each device.
- **Why this many hubs?** names the binding constraint and outlines the rooms that force extra hubs.
- **Installer pack**: cable schedule, bill of materials, loop resistance, cost estimate and commissioning sheet.

The server listens on 127.0.0.1 only and refuses requests addressed to any other host.

### DXF layer convention

- `ROOMS`: one closed polyline per room, neighbouring outlines sharing their common edge, and a text label inside each naming its type (living, bedroom, kitchen, storage, bathroom, stair; "Bedroom 2", "WC" and "Lounge" are fine).
- `DOORS`: a line across the shared edge wherever two rooms connect.
- Units from the drawing's `$INSUNITS`.

## Command line

```bash
loopwright solve --id 14433 --out out/               # out/14433.json, .svg, .html (viewer), .installer.html and .installer.csv
loopwright solve --json plan.json --out out/         # an organisers' plan file instead of a ResPlan id
loopwright validate out/14433.json --id 14433        # structure, then the independent checks V00-V14
loopwright validate out/14433.json                   # structure only: types, finite numbers, schema keys
loopwright index out/                                # out/index.html listing every solved plan
loopwright batch --split test --workers 6            # a ResPlan split, failures grouped by cause
loopwright results bench/test-split.jsonl bench/val-split.jsonl   # bench/results.md
loopwright config                                    # the default settings as JSON
```

Options mirror `docs/assumptions.md`, for example `--zone-link through_rooms` or `--max-nodes 20`.

## Layout

| Path | What |
|------|------|
| `loopwright/config.py` | Every rule reading as a setting (Q1-Q14), each value checked |
| `loopwright/io/` | ResPlan loader (restricted unpickler), organisers' JSON, plan builder, plan edits, DXF, image and PDF import |
| `loopwright/geometry/` | Healing, scale, spaces, walkable area, door graph, nodes |
| `loopwright/optimize/` | Lower bound, zones, exact hub count, greedy baseline |
| `loopwright/routing/` | Axis-aligned grid router with exact bend costs |
| `loopwright/solve.py` | The pipeline, hub placement on the ring, and the repair pass |
| `loopwright/validate/` | Independent validator: structure checks, rules V00-V14, scorer |
| `loopwright/output/` | JSON (schema `loopwright/2`), SVG overlay, viewer, installer pack, cut analysis, explanations, app page |
| `loopwright/api/` | The local server behind the app |
| `loopwright/batch.py`, `results.py` | Batch runs and the results table |
| `docs/` | Assumptions, schema, testing playbook, phase notes |

## Status

See `docs/phases/`. Each phase ends with a tag (`phase-1`, `phase-2`, ...) that is pushed and tested before the next merge.

## Credits

ResPlan dataset (Abouagour and Garyfallidis, 2025; CC BY 4.0).
