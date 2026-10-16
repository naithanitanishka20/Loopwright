"""Nodes keep 0.5 m from their room's walls, and very small rooms get none (Eval-01 meeting)."""
import copy

from shapely.geometry import Point

from loopwright.config import DEFAULT
from loopwright.io.sketch import build_plan
from loopwright.solve import solve
from loopwright.validate.rules import validate


def square(x0, y0, x1, y1):
    return [[x0, y0], [x1, y0], [x1, y1], [x0, y1]]


def flat(side_room):
    """A 5 m x 4 m living room with one more room on its right, joined by a door."""
    return build_plan([{"type": "living", "polygon": square(0, 0, 5, 4)}, side_room], doors=[(0, 1)])


def checks(out):
    return {c["id"]: c for c in out["validation"]["checks"]}


def neglected(out):
    return {d["room"]: d["reason"] for d in out["diagnostics"] if d["code"] == "ROOM_NEGLECTED"}


def test_a_room_under_2_m2_gets_no_node():
    out, _ = solve(flat({"type": "storage", "polygon": square(5, 0, 6.2, 1.5)}))  # 1.1 m x 1.4 m inside
    assert [n["room"] for n in out["nodes"]] == ["living_0"]
    assert "storage_0" in neglected(out) and "2 m²" in neglected(out)["storage_0"]
    assert out["validation"]["valid"] is True


def test_a_room_too_narrow_for_a_node_0_5_m_from_its_walls_gets_none():
    out, _ = solve(flat({"type": "storage", "polygon": square(5, 0, 5.9, 4)}))  # 0.8 m wide, 3.1 m² inside
    assert [n["room"] for n in out["nodes"]] == ["living_0"]
    assert "0.5 m from its walls" in neglected(out)["storage_0"]
    assert out["validation"]["valid"] is True


def test_every_node_keeps_0_5_m_from_its_room_walls():
    plan = flat({"type": "bedroom", "polygon": square(5, 0, 9, 4)})
    out, model = solve(plan)
    for n in out["nodes"]:
        room = model.space(n["room"]).geom
        assert room.boundary.distance(Point(n["pos"])) >= 0.5
    assert checks(out)["V15"]["pass"] is True


def test_a_node_moved_next_to_a_wall_fails_v15():
    plan = flat({"type": "bedroom", "polygon": square(5, 0, 9, 4)})
    out, _ = solve(plan)
    bad = copy.deepcopy(out)
    node = next(n for n in bad["nodes"] if n["room"] == "bedroom_0")
    node["pos"] = [5.35, 2.0]  # 0.3 m from the bedroom's west wall face at x = 5.05
    assert checks({"validation": validate(plan, bad, DEFAULT)})["V15"]["pass"] is False
