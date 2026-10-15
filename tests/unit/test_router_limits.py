import time

import pytest

from loopwright.config import DEFAULT
from loopwright.io.sketch import build_plan
from loopwright.solve import solve


def test_a_plan_kilometres_across_is_refused_quickly_instead_of_routed():
    # A drawing in millimetres read as metres: two rooms 5 km by 4 km each.
    plan = build_plan([{"type": "living", "polygon": [[0, 0], [5000, 0], [5000, 4000], [0, 4000]]},
                       {"type": "bedroom", "polygon": [[5000, 0], [10000, 0], [10000, 4000], [5000, 4000]]}],
                      doors=[(0, 1)])
    started = time.perf_counter()
    with pytest.raises(ValueError, match="check its units"):
        solve(plan, DEFAULT)
    assert time.perf_counter() - started < 10
