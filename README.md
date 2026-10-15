# Loopwright

Loopwright is the foundation for hub placement and closed-ring cable routing on residential floor plans.

This checkout contains the configuration model, output validator, schema, and safe ResPlan download helper. The full optimizer, geometry engine, and obstacle-aware routing engine are not implemented yet.

It also includes two small planning primitives: the hub-count lower bound and an obstacle-free axis-aligned path helper.

## Setup

```bash
python -m venv .venv
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

- `loopwright/config.py`: validated rule settings.
- `loopwright/validator.py`: structural output checks.
- `loopwright/cli.py`: config and validation commands.
- `loopwright/solver.py`: hub-count lower bound.
- `loopwright/routing.py`: basic axis-aligned path construction.
- `docs/schema-v2.json`: output schema.
- `docs/assumptions.md`: open rule decisions.
- `scripts/fetch_resplan.py`: timeout-limited, checksum-verified download.
