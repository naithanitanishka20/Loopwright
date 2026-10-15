import os
import pickle

import pytest
from shapely.geometry import box

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
