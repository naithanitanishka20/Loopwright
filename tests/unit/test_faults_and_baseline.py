"""Remaining fault-injection cases for the validator, plus the greedy baseline."""
import copy

from loopwright.config import DEFAULT
from loopwright.optimize.baseline import greedy_zones
from loopwright.solve import solve
from loopwright.validate.rules import validate
from tests.helpers import two_room_plan


def _failed(plan, out):
    return {c["id"] for c in validate(plan, out, DEFAULT)["checks"] if c["pass"] is False}


def _solved():
    plan = two_room_plan()
    out, _ = solve(plan)
    return plan, out


def test_repeated_node_fails_v08():
    plan, out = _solved()
    bad = copy.deepcopy(out)
    seq = bad["rings"][0]["sequence"]
    seq.insert(2, seq[1])
    assert "V08" in _failed(plan, bad)


def test_gap_in_a_polyline_fails_v09():
    plan, out = _solved()
    bad = copy.deepcopy(out)
    leg = bad["rings"][0]["legs"][0]
    leg["path"][-1] = [leg["path"][-1][0] + 0.5, leg["path"][-1][1]]
    assert "V09" in _failed(plan, bad)


def test_run_through_a_window_fails_v11():
    plan, out = _solved()
    bad = copy.deepcopy(out)
    bad["rings"][0]["legs"][0]["path"] += [[2.5, 3.95], [2.5, 3.95]]
    assert "V11" in _failed(plan, bad)


def test_run_outside_the_building_fails_v12():
    plan, out = _solved()
    bad = copy.deepcopy(out)
    first = bad["rings"][0]["legs"][0]["path"][0]
    bad["rings"][0]["legs"][0]["path"][1:1] = [[first[0], -1.0], [first[0], first[1]]]
    assert "V12" in _failed(plan, bad)


def test_a_door_through_a_thick_wall_still_links_rooms():
    # Regression for plans 15258 and 11912: the wall at the door is thicker than
    # wall_depth says, so grown room outlines never meet, but the door joins them.
    from tests.helpers import thick_wall_plan

    plan = thick_wall_plan()
    out, _ = solve(plan)
    assert out["metrics"]["hubs"] == 1
    assert out["validation"]["valid"] is True, [c for c in out["validation"]["checks"] if c["pass"] is False]


def test_slipping_through_a_crack_that_is_no_door_fails_v13():
    # A 0.15 m crack in the middle wall is neither a door nor an open passage
    # (passages must be at least two wall depths, 0.2 m, long), so a run through
    # it changes space illegally even though it touches no wall.
    from shapely.geometry import box

    plan, out = _solved()
    cracked = dict(plan, wall=plan["wall"].difference(box(4.9, 3.0, 5.1, 3.15)))
    bad = copy.deepcopy(out)
    ring = bad["rings"][0]
    leg = next(l for l in ring["legs"] if min(p[0] for p in l["path"]) < 4.95 < max(p[0] for p in l["path"]))
    a, b = leg["path"][0], leg["path"][-1]
    leg["path"] = [a, [a[0], 3.075], [b[0], 3.075], b]
    failed = {c["id"] for c in validate(cracked, bad, DEFAULT)["checks"] if c["pass"] is False}
    assert "V13" in failed and "V10" not in failed


def test_failing_legs_are_located_for_the_viewer():
    plan, out = _solved()
    bad = copy.deepcopy(out)
    leg = bad["rings"][0]["legs"][1]
    leg["path"] = [leg["path"][0], [leg["path"][-1][0], leg["path"][-1][1] + 0.5]]
    check = next(c for c in validate(plan, bad, DEFAULT)["checks"] if c["id"] == "V14")
    assert check["pass"] is False and check["where"] == [{"ring": "H1", "leg": 2}]


def test_greedy_never_beats_exact_and_can_lose():
    # A star around the living room: bedrooms link only to it.
    adj = {"living": {"b1", "b2", "b3"}, "b1": {"living"}, "b2": {"living"}, "b3": {"living"}}
    ids, areas = ["living", "b1", "b2", "b3"], [55.0, 40.0, 20.0, 20.0]
    zones = greedy_zones(ids, areas, adj, DEFAULT)
    # Greedy pairs living with the largest bedroom (95 m²) and strands b2 and b3: 3 hubs.
    # Exact: living + b2 + b3 (95 m²) and b1 alone: 2 hubs.
    assert len(zones) == 3
    assert sorted(len(z) for z in zones) == [1, 1, 2]
