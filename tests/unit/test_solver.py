import math

import pytest

from loopwright.config import Settings
from loopwright.solver import lower_bound_hubs


def test_lower_bound_uses_area_and_node_caps():
    settings = Settings(max_area_m2=100, max_nodes=5)
    assert lower_bound_hubs(201, 11, settings) == 3
    assert lower_bound_hubs(0, 0, settings) == 1


@pytest.mark.parametrize(
    ("area", "nodes"),
    [(math.nan, 1), (math.inf, 1), (-1, 1), (1, -1), (1, True)],
)
def test_lower_bound_rejects_invalid_inputs(area, nodes):
    with pytest.raises(ValueError):
        lower_bound_hubs(area, nodes)
