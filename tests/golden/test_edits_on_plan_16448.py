"""Plan edits on a real ResPlan plan: the demo's "remove a door, connect two rooms" moments."""
import pytest

from loopwright.config import DEFAULT
from loopwright.io.edits import apply_edits
from loopwright.io.resplan import get_plan
from loopwright.solve import solve

pytestmark = pytest.mark.dataset


def hubs_valid_unlinked(plan, settings):
    out, _ = solve(plan, settings)
    return out["metrics"]["hubs"], out["validation"]["valid"], [d["room"] for d in out["diagnostics"] if d["code"] == "NO_LINK"]


def test_connecting_two_bedrooms_saves_a_hub_under_the_strict_rule(resplan_plans):
    plan = get_plan(resplan_plans, 16448)
    joined = apply_edits(plan, [{"op": "connect", "rooms": ["bedroom_0", "bedroom_1"]}])
    assert hubs_valid_unlinked(plan, DEFAULT)[:2] == (4, True)
    assert hubs_valid_unlinked(joined, DEFAULT)[:2] == (3, True)


def test_removing_a_bedroom_door_strands_it_under_the_through_rooms_rule(resplan_plans):
    settings = DEFAULT.with_overrides(zone_link="through_rooms")
    plan = get_plan(resplan_plans, 16448)
    assert hubs_valid_unlinked(plan, settings) == (2, True, [])
    assert hubs_valid_unlinked(apply_edits(plan, [{"op": "remove_door", "door": 2}]), settings) == (3, True, ["bedroom_0"])


def test_rooms_that_do_not_touch_cannot_be_connected(resplan_plans):
    with pytest.raises(ValueError, match="not next to each other"):
        apply_edits(get_plan(resplan_plans, 16448), [{"op": "connect", "rooms": ["kitchen_0", "bedroom_0"]}])
