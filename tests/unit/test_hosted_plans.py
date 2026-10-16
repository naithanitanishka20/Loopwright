"""The hosted copy's plans: the test split and the plans the site and the app open, nothing else."""
import json
import pathlib
import pickle
import runpy
import sys

from loopwright.io.resplan import load_plans

SCRIPT = str(pathlib.Path(__file__).resolve().parents[2] / "scripts" / "hosted_plans.py")


def test_the_hosted_subset_keeps_the_test_split_and_the_plans_the_site_opens(tmp_path, monkeypatch):
    every = [{"id": i, "rooms": i % 7} for i in (1, 8, 59, 100, 2916, 11282, 16448, 20000)]
    source = tmp_path / "ResPlan.pkl"
    source.write_bytes(pickle.dumps(every, protocol=4))
    (tmp_path / "split.json").write_text(json.dumps({"test": [1, 59], "train": [8, 100, 20000]}), encoding="utf-8")
    target = tmp_path / "hosted.pkl"
    monkeypatch.setattr(sys, "argv", [SCRIPT, str(source), str(target)])
    runpy.run_path(SCRIPT, run_name="__main__")
    kept = load_plans(target)  # the restricted loader reads it back
    assert sorted(p["id"] for p in kept) == [1, 59, 2916, 11282, 16448]
    assert kept[0] == every[0]
