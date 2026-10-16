# Phase 2 · Walking skeleton

Tag: `phase-2`

## Delivered

- `loopwright/io/resplan.py`: ResPlan loader with a restricted unpickler (only `shapely.io.from_wkb` and two numpy helpers may load).
- `loopwright/io/organiser.py`: adapter for the organisers' JSON (WKT, GeoJSON or coordinate lists; key aliases). Schema still pending (Q5).
- `loopwright/geometry/`: healing, scale (`sqrt(area / inner.area)`), spaces with merged living rooms, nodes at the pole of inaccessibility.
- `loopwright/optimize/zones.py`: lower bound and the exact minimum hub count (subset search over bitmasks; property-tested against brute force).
- `loopwright/routing/straight.py`: stand-in router, one horizontal-then-vertical L per leg.
- `loopwright/validate/`: independent validator (V00-V04, V06-V12, V14; V05 and V13 wait for the door graph) and scorer (length, bends incl. turns at nodes, crossings and overlap between rings, J, slide 5 reviewer lines).
- `loopwright/output/`: deterministic JSON with a SHA-256 digest; SVG overlay in the organisers' slide 5 style.
- CLI: `loopwright solve`, `loopwright validate` and `loopwright config`.

## From the Phase 1 test round

- `loopwright/config.py`: every setting is checked on creation (finite numbers, exact bool and int types, known choices, `pass_through` normalised to a tuple).
- `loopwright/validate/structure.py`: structural checks against `docs/schema-v2.json` (all 14 required keys, types, finite numbers, no booleans as numbers, no NaN or Infinity in the JSON). `loopwright validate` runs it before the rules; without `--id` or `--json` it checks structure only.
- `scripts/fetch_resplan.py`: HTTPS to the pinned host only, 30 s timeout, 200 MB cap, written atomically, SHA-256 checked against a pinned digest.
- `optimize.zones.lower_bound` rejects non-finite, negative and boolean inputs.
- The tester's stand-ins (`loopwright/routing.py`, `solver.py`, `validator.py`) were folded into the Phase 2 packages; `living_pieces` accepts `"split"`, the value `geometry/spaces.py` uses.

## From the Phase 2 test round

- Inputs are checked before use. `geometry.spaces.scale` needs a finite positive `m_per_unit` or `area`. The organisers' JSON adapter rejects a non-object document, non-string keys, booleans and non-finite coordinates, and reports unreadable geometry as `invalid geometry`. `feasible_zones`, `l_leg` and `nearest_order` reject non-finite and boolean values, and the fetcher rejects a timeout that isn't a finite positive number.
- JSON output refuses NaN and Infinity. `write_json` builds the text before it opens the file, so a bad value leaves no half-written file.
- `ranking_key` must hold exactly two finite numbers.
- `geometry.heal.valid` falls back to `buffer(0)` only on GEOS and value errors.
- New tests: `tests/unit/test_phase2_adversarial.py`, solve-then-validate on an organisers' JSON file through the CLI, the fetcher's timeout check and partial-file cleanup, and a browser test that renders a real overlay.

## Run

```bash
loopwright solve --id 14433 --out out/      # hubs 2 (bound 2), writes out/14433.json and out/14433.svg
loopwright validate out/14433.json --id 14433
python -m pytest -q                         # 58 tests; the golden test needs data/ResPlan.zip
```

## Known limits (by design, fixed in Phase 3)

- Zones ignore door links (`rules.zone_link` is `"none"` and a `ZONE_LINK_NOT_CHECKED` diagnostic is emitted).
- Legs are straight L shapes that ignore walls, so most real plans fail V10 (and often V11 and V12). That is expected at this phase.
- Ring order is nearest-neighbour, not exact; hubs sit 0.6 m from the main room's node.

## Testers: try to break

- Security: try to make `load_plans` execute code with a crafted pickle or zip; try path tricks in `--out` and `--json`.
- TDD: for each bug, write the failing test first under `tests/unit/`.
- Properties: e.g. reversing a ring never changes length; the hub minimum never drops below the bound.
- Validator: inject faults into `out/14433.json` by hand (diagonal segment, skipped node, ring ending at another hub) and confirm `loopwright validate` names the right rule.
- Visual: open `out/<id>.svg` for a few plans; labels must stay readable and inside the drawing.
- Architecture: check `loopwright/validate` imports nothing from `geometry`, `routing` or `optimize`.
- Edge cases: plans with a room over 100 m² (444 exist), plans with one eligible room, the organisers' JSON adapter with odd keys.
