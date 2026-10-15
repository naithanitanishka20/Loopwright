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


def test_greedy_never_beats_exact_and_can_lose():
    # A star around the living room: bedrooms link only to it.
    adj = {"living": {"b1", "b2", "b3"}, "b1": {"living"}, "b2": {"living"}, "b3": {"living"}}
    ids, areas = ["living", "b1", "b2", "b3"], [55.0, 40.0, 20.0, 20.0]
    zones = greedy_zones(ids, areas, adj, DEFAULT)
    # Greedy pairs living with the largest bedroom (95 m²) and strands b2 and b3: 3 hubs.
    # Exact: living + b2 + b3 (95 m²) and b1 alone: 2 hubs.
    assert len(zones) == 3
    assert sorted(len(z) for z in zones) == [1, 1, 2]
