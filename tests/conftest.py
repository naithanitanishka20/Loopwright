import os
import pathlib

import pytest

ROOT = pathlib.Path(__file__).resolve().parent.parent
DATA = pathlib.Path(os.environ.get("LOOPWRIGHT_DATA", ROOT / "data" / "ResPlan.zip"))


def pytest_collection_modifyitems(config, items):
    if DATA.exists():
        return
    skip = pytest.mark.skip(reason=f"dataset not found at {DATA}; run scripts/fetch_resplan.py")
    for item in items:
        if "dataset" in item.keywords:
            item.add_marker(skip)


@pytest.fixture(scope="session")
def resplan_plans():
    from loopwright.io.resplan import load_plans

    return load_plans(DATA)
