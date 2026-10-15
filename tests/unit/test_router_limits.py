import time

import pytest
from shapely.geometry import Point

from loopwright.config import DEFAULT
from loopwright.geometry.nodes import place_nodes
from loopwright.geometry.spaces import build_model
from loopwright.io.sketch import build_plan
from loopwright.routing.grid import INF, GridRouter
from loopwright.solve import solve
from tests.helpers import two_room_plan


def test_an_area_to_avoid_closes_the_door_it_covers():
    model = build_model(two_room_plan(), DEFAULT)
    stops = place_nodes(model, DEFAULT)
    assert GridRouter(model, stops, DEFAULT).cost("living_0", "bedroom_0") < INF
    blocked = GridRouter(model, stops, DEFAULT, avoid=Point(5.0, 1.95).buffer(0.6))  # covers the only door
    assert blocked.cost("living_0", "bedroom_0") == INF


def test_a_plan_kilometres_across_is_refused_quickly_instead_of_routed():
    # A drawing in millimetres read as metres: two rooms 5 km by 4 km each.
    plan = build_plan([{"type": "living", "polygon": [[0, 0], [5000, 0], [5000, 4000], [0, 4000]]},
                       {"type": "bedroom", "polygon": [[5000, 0], [10000, 0], [10000, 4000], [5000, 4000]]}],
                      doors=[(0, 1)])
    started = time.perf_counter()
    with pytest.raises(ValueError, match="check its units"):
        solve(plan, DEFAULT)
    assert time.perf_counter() - started < 10
