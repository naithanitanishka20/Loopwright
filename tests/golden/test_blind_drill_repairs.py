"""Plans from blind drill 1 (val split) that failed before the repair pass."""
import pytest

from loopwright.config import DEFAULT
from loopwright.io.resplan import get_plan
from loopwright.solve import solve

pytestmark = pytest.mark.dataset


def test_a_zone_the_router_cannot_join_is_split_by_the_repair_pass(resplan_plans):
    # 14245: the door graph joins bedroom_3 to the kitchen, but the only way between them is a 12 cm slot where
    # two walls fail to meet. The fewest-hub grouping puts them together; the repair pass gives each its own hub.
    # (Plans 1205 and 9313 were the examples until Phase 14 opened their doors drawn short of the wall.)
    out, _ = solve(get_plan(resplan_plans, 14245), DEFAULT)
    assert out["validation"]["valid"] is True
    unroutable = [d for d in out["diagnostics"] if d["code"] == "UNROUTABLE_LINK"]
    assert [d["rooms"] for d in unroutable] == [["bedroom_3", "kitchen_0"]]
    zone_of = {r: h["id"] for h in out["hubs"] for r in h["zone"]}
    assert zone_of["bedroom_3"] != zone_of["kitchen_0"]
    assert not any(d["code"] == "ROUTE_UNREACHABLE" for d in out["diagnostics"])


@pytest.mark.parametrize("plan_id", [9313, 12736, 529])
def test_fallback_routes_cannot_jump_thin_walls(resplan_plans, plan_id):
    # Blind drill 2 (train split): legs on the zero-clearance fallback grid jumped walls
    # thinner than half a grid step.
    out, _ = solve(get_plan(resplan_plans, plan_id), DEFAULT)
    assert out["validation"]["valid"] is True


def test_a_zone_just_under_the_area_cap_passes_the_validator(resplan_plans):
    # Blind drill 2: plan 15080's zone is 99.9997 m². The output's scale, rounded to 6 decimals,
    # made the validator measure it just over 100 m².
    out, _ = solve(get_plan(resplan_plans, 15080), DEFAULT)
    assert out["validation"]["valid"] is True


def test_a_leg_the_validator_rejects_is_rerouted(resplan_plans):
    # 7683: the router crossed into a pocket where the validator sees no passage.
    out, _ = solve(get_plan(resplan_plans, 7683), DEFAULT)
    assert out["validation"]["valid"] is True
    assert any(d["code"] == "REROUTED" for d in out["diagnostics"])


def test_scraps_labelled_as_rooms_get_no_node(resplan_plans):
    # 13606: two 'bedrooms' of 1.8 m² and 1.2 m² are left out (Eval-01: very small rooms get no node),
    # so the flat needs one hub, its lower bound.
    out, _ = solve(get_plan(resplan_plans, 13606), DEFAULT)
    assert out["validation"]["valid"] is True
    assert out["metrics"]["hubs"] == out["metrics"]["hub_lower_bound"] == 1
    assert sorted(d["room"] for d in out["diagnostics"] if d["code"] == "ROOM_NEGLECTED") == ["bedroom_1", "bedroom_3"]
