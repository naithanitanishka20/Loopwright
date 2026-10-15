# Loopwright

Hub placement and closed-ring cable routing on residential floor plans (Problem IA, UR Hackathon 2026H2). Confidential under Rule 6(a): keep this repository private.

Given a floor plan, Loopwright decides how many hubs, where each goes, which rooms and nodes each serves, the visiting order, and an axis-aligned cable route for every closed ring. Designs are ranked the organisers' way: fewest hubs first, then lowest cost J.

## Setup

```bash
python -m venv .venv
.venv/Scripts/activate        # Windows; use .venv/bin/activate on macOS/Linux
python -m pip install -e ".[dev]"
python scripts/fetch_resplan.py   # downloads data/ResPlan.zip (~100 MB, not committed)
python -m pytest -q
```

## Use

```bash
loopwright solve --id 14433 --out out/          # writes out/14433.json and out/14433.svg
loopwright validate out/14433.json --id 14433   # independent checks V00-V14
```

Options mirror `docs/assumptions.md`, for example `--zone-link through_rooms` or `--max-nodes 20`.

## Layout

| Path | What |
|------|------|
| `loopwright/config.py` | Every rule reading as a setting (Q1-Q14) |
| `loopwright/io/` | ResPlan loader (restricted unpickler) and the organisers' JSON adapter |
| `loopwright/geometry/` | Healing, scale, spaces, nodes |
| `loopwright/optimize/` | Lower bound, zones, exact hub count |
| `loopwright/routing/` | Leg routing |
| `loopwright/validate/` | Independent validator and scorer |
| `loopwright/output/` | JSON (schema `loopwright/2`) and SVG overlay |
| `docs/` | Assumptions, schema, testing playbook, phase notes |

## Status

See `docs/phases/`. Each phase ends with a tag (`phase-1`, `phase-2`, ...) that is pushed and tested before the next merge.

## Credits

ResPlan dataset (Abouagour and Garyfallidis, 2025; CC BY 4.0).
