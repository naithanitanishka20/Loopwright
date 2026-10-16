"""Plans where walls cost hubs they shouldn't have until Phase 14, and plans where walls rightly do."""
import pytest

from loopwright.io.resplan import get_plan
from loopwright.solve import solve

# Each now gets the one hub its lower bound allows
JOINED = [
    (1180, "the living room is drawn in two parts that walls separate, and the bedrooms open onto the smaller one"),
    (8111, "as 1180, on a smaller home"),
    (4755, "bedroom_0's door is drawn 3 cm short of its wall's far face"),
    (12736, "a door drawn short of its wall closed under the router's clearance"),
    (9313, "as 12736"),
]
# Each keeps its extra hubs: walls really part the rooms
APART = [
    (5213, 2, "the kitchen opens onto the living room only through an interior window (assumptions Q15)"),
    (12735, 3, "the bedrooms open onto a hallway that walls seal off; the drawing has no door into it"),
]


@pytest.mark.dataset
@pytest.mark.parametrize("plan_id,why", JOINED)
def test_rooms_a_door_joins_share_a_hub(resplan_plans, plan_id, why):
    out, _ = solve(get_plan(resplan_plans, plan_id))
    assert out["metrics"]["hubs"] == out["metrics"]["hub_lower_bound"] == 1, why
    assert out["validation"]["valid"] is True, [c for c in out["validation"]["checks"] if c["pass"] is False]


@pytest.mark.dataset
@pytest.mark.parametrize("plan_id,hubs,why", APART)
def test_rooms_walls_part_keep_their_own_hubs(resplan_plans, plan_id, hubs, why):
    out, _ = solve(get_plan(resplan_plans, plan_id))
    assert out["metrics"]["hubs"] == hubs, why
    assert out["metrics"]["hubs_greedy"] == hubs, "greedy can't join rooms walls part either"
    assert out["validation"]["valid"] is True
