# Testing playbook (for the testers)

After each phase the builder pushes a tag (`phase-1`, `phase-2`, ...). Testers test that tag, fix what they find, and push the fixes on their own branch. The builder merges them into `main` while working on the next phase.

## Flow

```bash
git clone <repo-url> && cd loopwright
git checkout -b test/phase-N phase-N      # start from the phase tag, not from main
python -m venv .venv && .venv/Scripts/activate
python -m pip install -e ".[dev]"
python scripts/fetch_resplan.py
python -m pytest -q
# ...test, fix, commit with a clear message...
git push -u origin test/phase-N           # never push to main; open a PR into main
```

Each fix commit names the problem it fixes and, where possible, adds a test that failed before the fix.

## What to run after every phase

| Area | How | What to look for |
|------|-----|------------------|
| Unit and property tests | `python -m pytest -q` | Red tests; new invariants worth a property test |
| Bug fixes | A failing test at the public interface that exposed the bug, first | Every fix starts with a test that failed before it |
| Code review | Read the diff since the last tag | Correctness bugs, dead code, duplication |
| Architecture | Imports in `loopwright/validate/` | The validator must not import solver modules; CLI ergonomics |
| Security | Crafted pickle, JSON, geometry and `--out` paths | Unsafe loading of untrusted files, path handling in the CLI, NaN, Infinity or booleans accepted as numbers |
| Browser and visual | `python -m pytest -m e2e -q`, then open the SVG and viewer | The overlay renders, labels readable, no overlaps |
| Test quality | Read the tests | Tests that can't fail, duplicated tests |

Dataset tests carry the `dataset` marker and skip when `data/ResPlan.zip` is absent. Keep network tests deterministic: inject the opener and use a fixed payload, as `tests/unit/test_fetch_resplan.py` does.

## Phase-specific checks

See `docs/phases/PHASE-N.md` for what each phase delivered, how to run it, and what to try to break.

## Reporting

Open an issue or PR titled `[phase-N] <what broke>`, with the plan ID, the command, what happened and what you expected.
