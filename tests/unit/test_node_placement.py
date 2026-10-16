"""Nodes sit near their room's doors (still 0.5 m from the walls), so rings don't detour to room centres."""
import pytest
from shapely.geometry import Point

from loopwright.config import DEFAULT
from loopwright.io.sketch import build_plan
from loopwright.solve import solve


def square(x0, y0, x1, y1):
    return [[x0, y0], [x1, y0], [x1, y1], [x0, y1]]


FLAT = [{"type": "living", "polygon": square(0, 0, 6, 6)},
        {"type": "bedroom", "polygon": square(6, 0, 11, 5)},
        {"type": "kitchen", "polygon": square(0, 6, 4, 10)}]


def test_a_one_door_room_has_its_node_just_inside_the_door():
    plan = build_plan(FLAT, doors=[(0, 1), (0, 2)])
    out, model = solve(plan)
    node = Point(next(n["pos"] for n in out["nodes"] if n["room"] == "bedroom_0"))
    door = Point(6.0, 2.5)  # the middle of the living-bedroom wall
    assert node.distance(door) < 0.75
    assert model.space("bedroom_0").geom.boundary.distance(node) >= 0.5
    assert out["validation"]["valid"] is True


def test_nodes_near_doors_make_the_ring_cheaper_than_nodes_at_room_centres():
    plan = build_plan(FLAT, doors=[(0, 1), (0, 2)])
    near, _ = solve(plan)
    centre, _ = solve(plan, DEFAULT.with_overrides(node_rule="pole"))
    assert near["metrics"]["hubs"] == centre["metrics"]["hubs"] == 1
    assert near["metrics"]["J"] < centre["metrics"]["J"] - 3


def test_a_room_with_no_opening_keeps_its_node_at_the_centre():
    plan = build_plan([{"type": "living", "polygon": square(0, 0, 6, 6)}], doors=[])
    out, _ = solve(plan)
    assert out["nodes"][0]["pos"] == pytest.approx([3.0, 3.0], abs=0.05)
