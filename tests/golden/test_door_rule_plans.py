import pytest

from loopwright.config import DEFAULT
from loopwright.io.resplan import get_plan
from loopwright.solve import solve

# Hub counts measured on 15 Oct 2026 across all plans (see docs/assumptions.md, Q1).
CASES = [
    (16448, "strict", 4),
    (16448, "through_rooms", 2),
    (14877, "strict", 3),
    (14433, "strict", 2),
]


@pytest.mark.dataset
@pytest.mark.parametrize("plan_id,zone_link,hubs", CASES)
def test_hub_count_follows_the_zone_rule(resplan_plans, plan_id, zone_link, hubs):
    out, _ = solve(get_plan(resplan_plans, plan_id), DEFAULT.with_overrides(zone_link=zone_link))
    assert out["metrics"]["hubs"] == hubs
    assert out["metrics"]["hub_lower_bound"] == 2
    assert out["validation"]["valid"] is True, [c for c in out["validation"]["checks"] if c["pass"] is False]


@pytest.mark.dataset
def test_extra_hubs_are_explained(resplan_plans):
    out, _ = solve(get_plan(resplan_plans, 16448))
    # Strict rule: the living zone holds the living room and one bedroom; the kitchen and the
    # two other bedrooms open only onto the living room, so each is stranded in its own zone.
    extra = [d for d in out["diagnostics"] if d["code"] == "EXTRA_HUB"]
    assert sorted(d["room"] for d in extra) == ["bedroom_0", "bedroom_2", "kitchen_0"]
    assert all("joins only through living_0" in d["reason"] for d in extra)
