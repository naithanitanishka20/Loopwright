# Phase 13 · Every plan on the hosted copy

Tag: `phase-13`

On the hosted playground most plan numbers answered "plan not found". Three causes, all fixed.

## What was wrong

- **Only a tenth of the plans were there.** To save memory the hosted copy kept the test split and three more plans, 1,635 of 17,000.
- **ResPlan numbers its plans with gaps.** Its 17,000 plans run from 0 to 999398, so most numbers a person types are not plans at all (there is no plan 3).
- **The plan list failed on the server.** The download script writes through a temporary file, which is readable by root only, and the server runs as its own user, so reading `split.json` failed and `/api/plans` answered 500. The playground then fell back to drawing without saying why, and did not open on a solved plan.

## Exit check

| Check | Target | Result |
|---|---|---|
| Every plan | all 17,000 solvable on the hosted copy | a SQLite store of every plan, read one per request through the restricted unpickler (`PlanStore`, `scripts/plan_store.py`); rehearsed with the container's command: plans 0, 999398, 2916 and 16448 solve, about 80 MB of memory |
| No dead numbers | a number that is not a plan never reaches the server as a failed solve | the playground lists the real numbers as you type, offers the three nearest when a number is not a plan, and has Random and Next; the server's own 404 names the nearest too |
| Nothing the server cannot read | the store carries the split | the image deletes the downloads and opens the store to the server's user; a failing plan list now shows its reason |

## Run

```bash
python scripts/plan_store.py data/ResPlan.zip data/plans.sqlite
loopwright serve --site site --data data/plans.sqlite
```
