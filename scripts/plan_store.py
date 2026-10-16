"""Write the plan store a hosted copy of the app serves: every ResPlan plan, read back one at a time.

All 17,000 plans take about 1.4 GB once loaded; in the store they stay on disk and the server reads the
one each request names. The split goes inside, so the server needs no other file.
Usage: python scripts/plan_store.py data/ResPlan.zip data/plans.sqlite  (split.json beside the source)
"""
import json
import pathlib
import sys

from loopwright.io.resplan import load_plans, write_store


def main(source, target):
    source = pathlib.Path(source)
    split = json.loads(source.with_name("split.json").read_text(encoding="utf-8"))
    plans = load_plans(source)
    write_store(plans, split, target)
    print(f"wrote {len(plans)} plans to {target}")


if __name__ == "__main__":
    main(*sys.argv[1:3])
