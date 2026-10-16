"""The hosted copy's plan store: every plan, read one at a time, still through the restricted unpickler."""
import json
import os
import pathlib
import pickle
import runpy
import sqlite3
import sys
import zlib

import pytest

from loopwright.io.resplan import PlanStore, UnsafePickleError

SCRIPT = str(pathlib.Path(__file__).resolve().parents[2] / "scripts" / "plan_store.py")
EVERY = [{"id": i, "rooms": i % 7} for i in (0, 9, 2916, 999398)]
SPLIT = {"train": [0, 2916], "test": [9], "val": [999398], "augmented": []}


def build(tmp_path, monkeypatch):
    source = tmp_path / "ResPlan.pkl"
    source.write_bytes(pickle.dumps(EVERY, protocol=4))
    (tmp_path / "split.json").write_text(json.dumps(SPLIT), encoding="utf-8")
    target = tmp_path / "plans.sqlite"
    monkeypatch.setattr(sys, "argv", [SCRIPT, str(source), str(target)])
    runpy.run_path(SCRIPT, run_name="__main__")
    return target


def test_the_store_keeps_every_plan_and_the_split_and_reads_one_plan_at_a_time(tmp_path, monkeypatch):
    store = PlanStore(build(tmp_path, monkeypatch))
    assert store.ids() == [0, 9, 2916, 999398]
    assert store.split() == SPLIT
    assert store.get("2916") == EVERY[2] and store.get(999398) == EVERY[3]
    assert store.get("3") is None and store.get("not a number") is None


def test_a_tampered_row_is_refused_by_the_restricted_unpickler(tmp_path, monkeypatch):
    target = build(tmp_path, monkeypatch)
    db = sqlite3.connect(target)
    db.execute("UPDATE plans SET data = ? WHERE id = 9", (zlib.compress(pickle.dumps(os.system)),))
    db.commit()
    db.close()
    with pytest.raises(UnsafePickleError):
        PlanStore(target).get("9")
