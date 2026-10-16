import pytest

from loopwright.io.resplan import get_plan
from loopwright.solve import solve


@pytest.mark.dataset
def test_plan_14433_end_to_end(resplan_plans):
    out, model = solve(get_plan(resplan_plans, 14433))
    assert abs(model.m_per_unit - 0.0512) < 0.0005
    assert len(model.eligible) == 5
    assert out["metrics"]["hubs"] == 2 == out["metrics"]["hub_lower_bound"]
    checks = {c["id"]: c["pass"] for c in out["validation"]["checks"]}
    for rule in ("V00", "V01", "V02", "V03", "V04", "V06", "V07", "V08", "V09", "V14"):
        assert checks[rule] is True, rule
