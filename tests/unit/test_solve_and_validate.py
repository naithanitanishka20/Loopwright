import copy
import json
import pathlib

import pytest

from loopwright.config import DEFAULT
from loopwright.output.schema import digest
from loopwright.solve import solve
from loopwright.validate.rules import validate
from tests.helpers import two_room_plan

SCHEMA = json.loads((pathlib.Path(__file__).resolve().parents[2] / "docs" / "schema-v2.json").read_text(encoding="utf-8"))


@pytest.fixture()
def solved():
    plan = two_room_plan()
    out, _ = solve(plan)
    return plan, out


def failed(plan, out, settings=DEFAULT):
    return {c["id"] for c in validate(plan, out, settings)["checks"] if c["pass"] is False}


def test_two_rooms_share_one_hub_and_pass_every_checked_rule(solved):
    plan, out = solved
    assert out["metrics"]["hubs"] == 1 and out["metrics"]["hub_lower_bound"] == 1
    assert out["rings"][0]["sequence"][0] == out["rings"][0]["sequence"][-1] == "H1"
    assert out["validation"]["valid"] is True
    assert set(SCHEMA["required"]) <= set(out)


def test_output_is_deterministic():
    a, _ = solve(two_room_plan())
    b, _ = solve(two_room_plan())
    assert digest(a) == digest(b)


def test_diagonal_segment_fails_v14(solved):
    plan, out = solved
    bad = copy.deepcopy(out)
    leg = bad["rings"][0]["legs"][1]
    leg["path"] = [leg["path"][0], leg["path"][-1]]
    leg["path"][-1] = [leg["path"][-1][0], leg["path"][-1][1] + 0.5]
    assert "V14" in failed(plan, bad)


def test_skipped_node_fails_v08(solved):
    plan, out = solved
    bad = copy.deepcopy(out)
    bad["rings"][0]["sequence"].pop(1)
    assert "V08" in failed(plan, bad)


def test_ring_ending_at_another_hub_fails_v07(solved):
    plan, out = solved
    bad = copy.deepcopy(out)
    bad["rings"][0]["sequence"][-1] = "H9"
    assert "V07" in failed(plan, bad)


def test_run_through_a_wall_fails_v10(solved):
    plan, out = solved
    bad = copy.deepcopy(out)
    # Push the leg that crosses the middle wall up to y = 3.0, above the door (1.5 to 2.4).
    for leg in bad["rings"][0]["legs"]:
        xs = [p[0] for p in leg["path"]]
        if min(xs) < 4.95 < max(xs):
            leg["path"] = [[p[0], 3.0] for p in leg["path"]]
    assert "V10" in failed(plan, bad)


def test_hub_in_the_wrong_room_fails_v06(solved):
    plan, out = solved
    bad = copy.deepcopy(out)
    bad["hubs"][0]["zone"] = ["bedroom_0"]
    bad["hubs"][0]["pos"] = [2.0, 2.0]          # inside the living room, not the bedroom
    assert "V06" in failed(plan, bad)


def test_routes_go_through_the_door(solved):
    plan, out = solved
    crossing = [leg for leg in out["rings"][0]["legs"]
                if min(p[0] for p in leg["path"]) < 4.95 < max(p[0] for p in leg["path"])]
    assert crossing, "some leg must cross the middle wall"
    for leg in crossing:
        for (x0, y0), (x1, y1) in zip(leg["path"], leg["path"][1:]):
            if min(x0, x1) < 5.0 < max(x0, x1):
                assert 1.5 < y0 < 2.4, f"crossed the wall outside the door at y={y0}"


def test_walling_up_the_door_breaks_zone_contiguity(solved):
    plan, out = solved
    from shapely.ops import unary_union

    sealed = dict(plan, wall=unary_union([plan["wall"], plan["door"]]), door=None)
    assert "V05" in failed(sealed, out)


def test_caps_are_enforced(solved):
    plan, out = solved
    assert "V03" in failed(plan, out, DEFAULT.with_overrides(max_area_m2=20.0))
    assert "V04" in failed(plan, out, DEFAULT.with_overrides(max_nodes=1))
