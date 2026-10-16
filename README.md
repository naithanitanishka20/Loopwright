# Loopwright

<<<<<<< HEAD
Loopwright is the foundation for hub placement and closed-ring cable routing on residential floor plans.

This checkout contains the configuration model, output validator, schema, and safe ResPlan download helper. The full optimizer, geometry engine, and obstacle-aware routing engine are not implemented yet.

It also includes two small planning primitives: the hub-count lower bound and an obstacle-free axis-aligned path helper.
=======
Hub placement and closed-ring cable routing on residential floor plans.

Given a floor plan, Loopwright decides how many hubs, where each goes, which rooms and nodes each serves, the visiting order, and an axis-aligned cable route for every closed ring. Designs are ranked the organisers' way: fewest hubs first, then lowest cost J. Every output is re-checked by an independent validator (rules V00-V16) that rebuilds rooms, walls and doors from the raw plan and imports nothing from the solver.

## Results

Every ResPlan plan, all 17,000 (`bench/results.md`, written by `loopwright results` from the batch records in `bench/`):

- **Valid**: 16,556 of 16,556 feasible plans. The other 444 each have a room over 100 m², which no design can satisfy; they are flagged infeasible.
- **Hubs**: 29,377 against a lower bound of 23,893; the greedy baseline needs 31,046. 12,906 plans meet the bound exactly. The rest are held above it by the door rule or by rooms that don't pack into zones of at most 100 m² and 5 nodes; "Why this many hubs?" names the reason on any plan.
- **Cable**: 323,483 m in all; J = 446,668, 27.0 per plan, scored exactly as the organisers' slide 7 defines the metrics (bends at nodes and the hub, crossings and overlap inside and between rings). Nodes sit by the doors and legs keep to separate lanes, so a ring rarely runs over itself.
- **Time**: one process on a laptop, test split: p50 0.38 s, p95 1.26 s per plan.

![Hubs above the lower bound per plan, exact against greedy](docs/figures/extra-hubs.svg)

![Share of plans solved within each time](docs/figures/runtime.svg)
>>>>>>> e93d1bc4ec002a5c7592ba84d9672f2712ba5fd4

## Setup

```bash
python -m venv .venv
<<<<<<< HEAD
.venv/Scripts/activate       # Windows
.venv/bin/activate           # macOS/Linux
python -m pip install -e ".[dev]"
python -m pytest -q
```

Install browser tooling only when running the optional smoke test:

```bash
python -m pip install -e ".[dev,e2e]"
playwright install chromium
python -m pytest -m e2e -q
=======
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
loopwright validate out/14433.json --id 14433        # structure, then the independent checks V00-V16
loopwright validate out/14433.json                   # structure only: types, finite numbers, schema keys
loopwright index out/                                # out/index.html listing every solved plan
loopwright batch --split test --workers 4            # a ResPlan split, failures grouped by cause
loopwright results bench/test-split.jsonl bench/val-split.jsonl   # bench/results.md
loopwright charts bench/test-split.jsonl --runtime bench/latency-test.jsonl   # docs/figures/*.svg
loopwright config                                    # the default settings as JSON
>>>>>>> e93d1bc4ec002a5c7592ba84d9672f2712ba5fd4
```

## Commands

```bash
loopwright config
loopwright validate path/to/design.json
```

The validator accepts schema `loopwright/2` and rejects malformed structure, non-finite numbers, and boolean values used as numbers.

The dataset helper requires a trusted SHA-256 digest. Set `LOOPWRIGHT_RESPPLAN_SHA256` or pass `--sha256` before downloading:

```bash
python scripts/fetch_resplan.py --sha256 <trusted-digest>
```

## Layout

<<<<<<< HEAD
- `loopwright/config.py`: validated rule settings.
- `loopwright/validator.py`: structural output checks.
- `loopwright/cli.py`: config and validation commands.
- `loopwright/solver.py`: hub-count lower bound.
- `loopwright/routing.py`: basic axis-aligned path construction.
- `docs/schema-v2.json`: output schema.
- `docs/assumptions.md`: open rule decisions.
- `scripts/fetch_resplan.py`: timeout-limited, checksum-verified download.
=======
| Path | What |
|------|------|
| `loopwright/config.py` | Every rule reading as a setting (Q1-Q14), each value checked |
| `loopwright/io/` | ResPlan loader (restricted unpickler), organisers' JSON, plan builder, plan edits, DXF, image and PDF import |
| `loopwright/geometry/` | Healing, scale, spaces, walkable area, door graph, nodes |
| `loopwright/optimize/` | Lower bound, zones, exact hub count, greedy baseline |
| `loopwright/routing/` | Axis-aligned grid router with exact bend costs |
| `loopwright/solve.py` | The pipeline, hub placement on the ring, and the repair pass |
| `loopwright/validate/` | Independent validator: structure checks, rules V00-V16, scorer (metrics as the organisers define them) |
| `loopwright/output/` | JSON (schema `loopwright/2`), SVG overlay, viewer, installer pack, cut analysis, explanations, app page |
| `loopwright/api/` | The local server behind the app |
| `loopwright/batch.py`, `results.py`, `charts.py` | Batch runs, the results table and the slide figures |
| `bench/` | Batch records (`.jsonl`) and reports for every ResPlan split, and `results.md` |
| `docs/` | Assumptions, schema, testing playbook, demo script, phase notes, figures |

## Status

See `docs/phases/`. Each phase ends with a tag (`phase-1`, `phase-2`, ...) that is pushed and tested before the next merge.

## Credits

ResPlan dataset (Abouagour and Garyfallidis, 2025; CC BY 4.0).
>>>>>>> e93d1bc4ec002a5c7592ba84d9672f2712ba5fd4
