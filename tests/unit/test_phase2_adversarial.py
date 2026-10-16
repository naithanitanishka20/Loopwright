import math

import pytest
from shapely.geometry import Polygon

from loopwright.geometry.spaces import scale
from loopwright.io.organiser import from_dict, parse_geometry
from loopwright.optimize.zones import feasible_zones
from loopwright.output.schema import canonical_json, write_json
from loopwright.routing.straight import l_leg
from loopwright.solve import solve
from tests.helpers import two_room_plan


@pytest.mark.parametrize("value", [math.nan, math.inf, -math.inf, 0.0, -1.0, True])
def test_scale_rejects_invalid_explicit_scale(value):
    inner = type("Inner", (), {"area": 1.0})()

    with pytest.raises(ValueError, match="m_per_unit"):
        scale({"m_per_unit": value}, inner)


@pytest.mark.parametrize("value", [math.nan, math.inf, -math.inf, 0.0, -1.0, True])
def test_scale_rejects_invalid_area(value):
    inner = type("Inner", (), {"area": 1.0})()

    with pytest.raises(ValueError, match="area"):
        scale({"area": value}, inner)


def test_organiser_rejects_non_object_input():
    with pytest.raises(ValueError, match="object"):
        from_dict([])


def test_organiser_rejects_boolean_coordinates():
    with pytest.raises(ValueError, match="coordinates"):
        parse_geometry([[True, 0], [0, 1], [1, 0]])


def test_organiser_accepts_negative_coordinates():
    geometry = parse_geometry([[-2, -1], [0, -1], [0, 1], [-2, 1], [-2, -1]])

    assert geometry.bounds == (-2.0, -1.0, 0.0, 1.0)


@pytest.mark.parametrize("value", [math.nan, math.inf, -math.inf, 0.0, -1.0, True])
def test_organiser_rejects_invalid_wall_depth(value):
    with pytest.raises(ValueError, match="wall_depth"):
        from_dict({
            "area": 1.0,
            "wall_depth": value,
            "inner": "POLYGON ((0 0, 1 0, 1 1, 0 1, 0 0))",
        })


@pytest.mark.parametrize("value", [math.nan, math.inf, -math.inf, 0.0, -1.0, True])
def test_solver_rejects_invalid_wall_depth(value):
    plan = two_room_plan()
    plan["wall_depth"] = value

    with pytest.raises(ValueError, match="wall_depth"):
        solve(plan)


@pytest.mark.parametrize("area", [[math.nan], [math.inf], [-1.0], [True]])
def test_feasible_zones_reject_invalid_areas(area):
    with pytest.raises(ValueError, match="areas"):
        feasible_zones(area)


@pytest.mark.parametrize("point", [(math.nan, 0), (math.inf, 0), (True, 0)])
def test_l_leg_rejects_non_finite_or_boolean_coordinates(point):
    with pytest.raises(ValueError, match="point"):
        l_leg(point, (1.0, 1.0))


def test_output_serialization_rejects_non_finite_numbers(tmp_path):
    with pytest.raises(ValueError, match="Out of range float values"):
        canonical_json({"value": math.nan})

    with pytest.raises(ValueError, match="Out of range float values"):
        write_json({"value": math.inf}, tmp_path / "design.json")


def test_self_intersecting_room_is_repaired_before_solving():
    plan = two_room_plan()
    plan["living"] = Polygon([
        (0.1, 0.1), (4.9, 3.9), (4.9, 0.1), (0.1, 3.9), (0.1, 0.1)
    ])

    output, _ = solve(plan)

    assert output["metrics"]["hubs"] == 1
    assert any(item["code"] == "REPAIRED_GEOMETRY" for item in output["diagnostics"])


def test_disconnected_zone_callback_is_honored():
    feasible = feasible_zones([20.0, 20.0], connected=lambda mask: mask == 1 or mask == 2)

    assert feasible[1] is True
    assert feasible[2] is True
    assert feasible[3] is False


def test_schema_v2_ranking_key_must_have_two_finite_numbers():
    document = {
        "schema": "loopwright/2",
        "plan_id": "demo",
        "frame": {"units": "drawing", "m_per_unit": 1},
        "rules": {"max_area_m2": 100, "max_nodes": 5, "zone_link": "strict", "axis_aligned": True},
        "weights": {}, "rooms": [], "hubs": [], "nodes": [], "rings": [],
        "metrics": {"hubs": 0, "hub_lower_bound": 0, "length_m": 0, "bends": 0, "J": 0},
        "ranking_key": [0, math.nan, 1],
        "validation": {"valid": True, "checks": []}, "reviewer": [], "diagnostics": [],
    }

    from loopwright.validate.structure import validate_design

    issues = validate_design(document)

    assert "ranking_key must contain exactly two finite numbers" in issues
