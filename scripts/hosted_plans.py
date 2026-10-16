"""Write the plans a hosted copy of the app serves: the test split, and the plans the site and the app open.

All 17,000 plans take about 1.4 GB once loaded; this subset takes about a tenth of that.
Usage: python scripts/hosted_plans.py data/ResPlan.zip data/hosted.pkl  (split.json beside the source)
"""
import json
import pathlib
import pickle
import sys

from loopwright.io.resplan import load_plans

OPENED = {2916, 11282, 16448}  # the site's figures; 16448 is also the app's starting plan


def main(source, target):
    source, target = pathlib.Path(source), pathlib.Path(target)
    keep = {int(i) for i in json.loads(source.with_name("split.json").read_text(encoding="utf-8"))["test"]} | OPENED
    plans = [p for p in load_plans(source) if int(p["id"]) in keep]
    target.write_bytes(pickle.dumps(plans, protocol=4))
    print(f"wrote {len(plans)} plans to {target}")


if __name__ == "__main__":
    main(*sys.argv[1:3])
