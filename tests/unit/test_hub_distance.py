"""A hub never sits on a node: it keeps min_hub_node_m (0.5 m) from every node of its ring (Eval-01)."""
import copy

import pytest
from shapely.geometry import Point

from loopwright.config import DEFAULT
from loopwright.io.resplan import get_plan
from loopwright.io.sketch import build_plan
from loopwright.solve import solve
from loopwright.validate.rules import validate


def square(x0, y0, x1, y1):
    return [[x0, y0], [x1, y0], [x1, y1], [x0, y1]]


def closest_hub_node_m(out, s=1.0):
    pos = {h["id"]: Point(h["pos"]) for h in out["hubs"]}
    return min(pos[n["hub"]].distance(Point(n["pos"])) * s for n in out["nodes"])


def v16(plan, out):
    return next(c for c in validate(plan, out, DEFAULT)["checks"] if c["id"] == "V16")


def test_a_one_room_ring_puts_its_hub_exactly_the_minimum_away():
    out, _ = solve(build_plan([{"type": "living", "polygon": square(0, 0, 6, 6)}], doors=[]))
    assert closest_hub_node_m(out) == pytest.approx(0.5)
    assert out["rings"][0]["length_m"] == pytest.approx(1.0)  # 0.5 m out and back


def test_hubs_on_a_ring_keep_the_minimum_from_every_node():
    plan = build_plan([{"type": "living", "polygon": square(0, 0, 6, 6)},
                       {"type": "bedroom", "polygon": square(6, 2, 12, 8)},
                       {"type": "kitchen", "polygon": square(0, 6, 6, 9)}], doors=[(0, 1), (0, 2)])
    out, _ = solve(plan)
    assert closest_hub_node_m(out) >= 0.5
    assert v16(plan, out)["pass"] is True


def test_a_hub_on_its_node_fails_v16():
    plan = build_plan([{"type": "living", "polygon": square(0, 0, 6, 6)}], doors=[])
    out, _ = solve(plan)
    bad = copy.deepcopy(out)
    bad["hubs"][0]["pos"] = list(bad["nodes"][0]["pos"])
    assert v16(plan, bad)["pass"] is False


@pytest.mark.dataset
def test_plan_6733_no_longer_has_a_hub_on_a_node(resplan_plans):
    out, model = solve(get_plan(resplan_plans, 6733), DEFAULT)
    assert closest_hub_node_m(out, model.m_per_unit) >= 0.5 - DEFAULT.tolerance_m  # positions are rounded
    assert out["validation"]["valid"] is True


@pytest.mark.dataset
@pytest.mark.parametrize("plan_id", [15365, 10114])
def test_a_fallback_hub_keeps_clear_of_every_node_of_its_zone(resplan_plans, plan_id):
    # With nodes near doors, a node across the door from the main room's node ended up under
    # 0.5 m from a hub placed off the ring.
    out, model = solve(get_plan(resplan_plans, plan_id), DEFAULT)
    assert closest_hub_node_m(out, model.m_per_unit) >= 0.5 - DEFAULT.tolerance_m  # positions are rounded
    assert out["validation"]["valid"] is True
