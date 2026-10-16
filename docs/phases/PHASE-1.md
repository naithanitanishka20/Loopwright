# Phase 1 · Kickoff

Tag: `phase-1`

## Delivered

- Package skeleton, `pyproject.toml` (Python 3.11+), editable install with `.[dev]`.
- `loopwright/config.py`: every rule reading from `docs/assumptions.md` as a setting, with validation.
- CI: GitHub Actions runs pytest on Python 3.11, 3.12 and 3.13.
- `docs/assumptions.md` (Q1-Q14 ledger), `docs/schema-v2.json` (output schema), `docs/TESTING.md` (tester playbook).
- `scripts/fetch_resplan.py` downloads the dataset into `data/` (ignored by git).

## Run

```bash
python -m pip install -e ".[dev]"
python -m pytest -q
```

## Testers: try to break

- Install from a clean clone on Windows, macOS and Linux; CI should go green on all three Python versions.
- `Settings(zone_link="sideways")` and `Settings(max_nodes=0)` must raise; unknown overrides must raise.
- Security: nothing should load untrusted files yet; check `scripts/fetch_resplan.py` downloads only from the ResPlan repo.

## Known gaps

No solver code yet; that is Phase 2.
