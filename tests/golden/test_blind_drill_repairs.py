"""Plans from blind drill 1 (val split) that failed before the repair pass."""
import pytest

from loopwright.config import DEFAULT
from loopwright.io.resplan import get_plan
from loopwright.solve import solve

pytestmark = pytest.mark.dataset


def test_rooms_the_router_cannot_join_get_separate_hubs(resplan_plans):
    # 1205: a bedroom whose only openings are interior windows touches the living room
    # through a crack too narrow to route; it used to share the living room's hub.
    out, _ = solve(get_plan(resplan_plans, 1205), DEFAULT)
    assert out["validation"]["valid"] is True
    unroutable = [d for d in out["diagnostics"] if d["code"] == "UNROUTABLE_LINK"]
    assert unroutable and all(len(d["rooms"]) == 2 for d in unroutable)
    assert not any(d["code"] == "ROUTE_UNREACHABLE" for d in out["diagnostics"])


def test_a_leg_the_validator_rejects_is_rerouted(resplan_plans):
    # 13606: the router crossed into an unlabelled pocket where the validator sees no passage.
    out, _ = solve(get_plan(resplan_plans, 13606), DEFAULT)
    assert out["validation"]["valid"] is True
    assert out["metrics"]["hubs"] == 2
    assert any(d["code"] == "REROUTED" for d in out["diagnostics"])
