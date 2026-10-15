# Loopwright

Phase 2 implementation for hub placement and closed-ring cable routing on residential floor plans.

## Install

```bash
python -m venv .venv
.venv/Scripts/activate
python -m pip install -e ".[dev]"
```

The optional dataset is fetched with a pinned SHA-256 check:

```bash
python scripts/fetch_resplan.py
```

## Commands

```bash
loopwright solve --id 14433 --out out
loopwright validate out/14433.json --id 14433
loopwright validate out/14433.json
loopwright config
```

An organiser JSON file can replace the dataset lookup with `--json`.

## Tests

```bash
python -m pytest -q
python -m pip install -e ".[dev,e2e]"
python -m playwright install chromium
python -m pytest -m e2e -q
```

Dataset tests skip when `data/ResPlan.zip` is absent. The downloader accepts only the pinned HTTPS host, enforces a size limit, and verifies the archive before replacing a file.

## Layout

- `loopwright/geometry`: geometry repair, scaling, spaces, and node placement
- `loopwright/io`: ResPlan and organiser JSON loaders
- `loopwright/optimize`: hub lower bound and zone search
- `loopwright/routing`: Phase 2 axis-aligned L legs
- `loopwright/validate`: structural checks, rules, and scoring
- `loopwright/output`: schema-v2 JSON and SVG overlay
- `scripts`: dataset download
- `docs`: assumptions, schema, testing, and phase notes

## Phase 2 limits

Phase 2 does not build the door graph. Zone connectivity checks V05 and V13 are reported as not checked, and the stand-in router can cross walls or windows. Wall-aware routing is planned for Phase 3.
