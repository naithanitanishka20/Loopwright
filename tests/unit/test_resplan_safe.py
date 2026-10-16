import os
import pickle
import zipfile

import pytest
from shapely.geometry import box

import loopwright.io.resplan as resplan
from loopwright.io.resplan import UnsafePickleError, normalize_keys, safe_loads


class _Exploit:
    def __reduce__(self):
        return (os.system, ("echo pwned",))


def test_pickle_referencing_os_system_is_refused():
    with pytest.raises(UnsafePickleError):
        safe_loads(pickle.dumps(_Exploit()))


def test_plan_with_shapely_geometry_loads():
    plan = safe_loads(pickle.dumps([{"id": 7, "inner": box(0, 0, 2, 3)}]))
    assert plan[0]["id"] == 7 and plan[0]["inner"].area == 6


def test_balcony_typo_is_normalised():
    assert "balcony" in normalize_keys({"balacony": box(0, 0, 1, 1)})


@pytest.mark.parametrize("payload", [{"id": 7}, ["not a plan"]])
def test_loader_rejects_malformed_plan_collections(tmp_path, payload):
    source = tmp_path / "plans.pkl"
    source.write_bytes(pickle.dumps(payload))

    with pytest.raises(ValueError, match="list of plan mappings"):
        resplan.load_plans(source)


@pytest.mark.parametrize("suffix", [".pkl", ".zip"])
def test_loader_rejects_pickle_larger_than_the_limit(tmp_path, monkeypatch, suffix):
    source = tmp_path / f"plans{suffix}"
    if suffix == ".zip":
        with zipfile.ZipFile(source, "w") as archive:
            archive.writestr("plans.pkl", b"xx")
    else:
        source.write_bytes(b"xx")
    monkeypatch.setattr(resplan, "MAX_PICKLE_BYTES", 1)

    with pytest.raises(ValueError, match="maximum allowed size"):
        resplan.load_plans(source)
