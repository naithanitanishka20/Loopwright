# Loopwright

Hub placement and closed-ring cable routing on residential floor plans.

Given a floor plan, Loopwright decides how many hubs, where each goes, which rooms and nodes each serves, the visiting order, and an axis-aligned cable route for every closed ring. Designs are ranked the organisers' way: fewest hubs first, then lowest cost J.

## Setup

```bash
python -m venv .venv
.venv/Scripts/activate            # Windows
source .venv/bin/activate         # macOS/Linux
python -m pip install -e ".[dev]"
python scripts/fetch_resplan.py   # downloads data/ResPlan.zip (~100 MB, not committed) and checks its SHA-256
python -m pytest -q
```

The download is refused unless its SHA-256 matches the pinned digest; pass `--sha256` or set `LOOPWRIGHT_RESPLAN_SHA256` to trust a different archive.

## Use

```bash
loopwright solve --id 14433 --out out/          # writes out/14433.json and out/14433.svg
loopwright validate out/14433.json --id 14433   # structure, then independent checks V00-V14
loopwright validate out/14433.json              # structure only: types, finite numbers, schema keys
loopwright solve --json plan.json --out out/    # an organisers' JSON file instead of a dataset id
loopwright config                               # the default settings as JSON
```

Options mirror `docs/assumptions.md`, for example `--zone-link through_rooms` or `--max-nodes 20`.

## Browser smoke test (optional)

```bash
python -m pip install -e ".[dev,e2e]"
python -m playwright install chromium
python -m pytest -m e2e -q
```

## Layout

| Path | What |
|------|------|
| `loopwright/config.py` | Every rule reading as a setting (Q1-Q14), each value checked |
| `loopwright/io/` | ResPlan loader (restricted unpickler) and the organisers' JSON adapter |
| `loopwright/geometry/` | Healing, scale, spaces, nodes |
| `loopwright/optimize/` | Lower bound, zones, exact hub count |
| `loopwright/routing/` | Leg routing |
| `loopwright/validate/` | Independent validator: structure checks, rules V00-V14, scorer |
| `loopwright/output/` | JSON (schema `loopwright/2`) and SVG overlay |
| `docs/` | Assumptions, schema, testing playbook, phase notes |

## Status

See `docs/phases/`. Each phase ends with a tag (`phase-1`, `phase-2`, ...) that is pushed and tested before the next merge.

## Credits

ResPlan dataset (Abouagour and Garyfallidis, 2025; CC BY 4.0).
