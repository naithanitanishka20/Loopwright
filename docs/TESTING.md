# Testing

Run the fast suite from the repository root:

```bash
<<<<<<< HEAD
=======
git clone <repo-url> && cd loopwright
git checkout -b test/phase-N phase-N      # start from the phase tag, not from main
python -m venv .venv && .venv/Scripts/activate
python -m pip install -e ".[dev,import,serve,e2e]"
python scripts/fetch_resplan.py
>>>>>>> e93d1bc4ec002a5c7592ba84d9672f2712ba5fd4
python -m pytest -q
```

Run browser smoke coverage when the e2e extra and Chromium are installed:

```bash
python -m pytest -m e2e -q
```

<<<<<<< HEAD
Tests cover settings validation, schema boundaries, the CLI, and the dataset downloader. Dataset-specific tests should use the `dataset` marker and skip when `data/ResPlan.zip` is absent.

Every new bug should get a failing regression test at the public interface that exposed it. Keep network tests deterministic by injecting the opener and using a fixed payload.
=======
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

## Browser tests (Playwright)

```bash
python -m pip install -e ".[dev,import,serve,e2e]"
python -m pytest -m e2e -q
```

They use Playwright's own Chromium if you ran `python -m playwright install chromium`, otherwise your installed Edge or Chrome. Without Playwright they skip. The app tests start a real `loopwright serve` on a free local port and drive it like a user: drawing rooms, clicking doors, cutting legs, uploading a plan image.

## Phase-specific checks

See `docs/phases/PHASE-N.md` for what each phase delivered, how to run it, and what to try to break.

## Reporting

Open an issue or PR titled `[phase-N] <what broke>`, with the plan ID, the command, what happened and what you expected.
>>>>>>> e93d1bc4ec002a5c7592ba84d9672f2712ba5fd4
