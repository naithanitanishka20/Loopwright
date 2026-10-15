import json

import pytest

from loopwright.validate.structure import DesignValidationError, load_design, validate_design


def test_validate_design_accepts_minimal_valid_document():
    document = {
        "schema": "loopwright/2",
        "plan_id": "demo",
        "frame": {"units": "drawing", "m_per_unit": 1},
        "rules": {"max_area_m2": 100, "max_nodes": 5, "zone_link": "strict", "axis_aligned": True},
        "weights": {},
        "rooms": [],
        "hubs": [],
        "nodes": [],
        "rings": [],
        "metrics": {"hubs": 0, "hub_lower_bound": 0, "length_m": 0, "bends": 0, "J": 0},
        "ranking_key": [0, 0],
        "validation": {"valid": True, "checks": []},
        "reviewer": [],
        "diagnostics": [],
    }

    assert validate_design(document) == []


def test_validate_design_rejects_malformed_top_level_document():
    issues = validate_design({"schema": "wrong"})
    assert "schema must be 'loopwright/2'" in issues
    assert any(issue.startswith("missing required fields:") for issue in issues)


def test_load_design_rejects_invalid_json(tmp_path):
    path = tmp_path / "design.json"
    path.write_text("{not json", encoding="utf-8")

    with pytest.raises(DesignValidationError, match="invalid JSON"):
        load_design(path)


def test_validate_design_rejects_nan_and_boolean_numbers():
    document = {
        "schema": "loopwright/2",
        "plan_id": "demo",
        "frame": {"units": "drawing", "m_per_unit": float("nan")},
        "rules": {"max_area_m2": True, "max_nodes": 5, "zone_link": "strict", "axis_aligned": True},
        "rooms": [],
        "hubs": [],
        "nodes": [],
        "rings": [],
        "metrics": {"hubs": 0, "hub_lower_bound": 0, "length_m": 0, "bends": 0, "J": 0},
        "ranking_key": [0, 0],
        "validation": {"valid": False, "checks": []},
        "reviewer": [],
        "diagnostics": [],
    }

    issues = validate_design(document)

    assert "frame.m_per_unit must be a finite number" in issues
    assert "rules.max_area_m2 must be a finite number" in issues


def test_validate_design_rejects_negative_bounds_and_zero_capacity():
    document = {
        "schema": "loopwright/2",
        "plan_id": "demo",
        "frame": {"units": "drawing", "m_per_unit": 1},
        "rules": {"max_area_m2": -1, "max_nodes": 0, "zone_link": "strict", "axis_aligned": True},
        "weights": {},
        "rooms": [],
        "hubs": [],
        "nodes": [],
        "rings": [],
        "metrics": {"hubs": 0, "hub_lower_bound": 0, "length_m": 0, "bends": 0, "J": 0},
        "ranking_key": [0, 0],
        "validation": {"valid": False, "checks": []},
        "reviewer": [],
        "diagnostics": [],
    }

    issues = validate_design(document)

    assert "rules.max_area_m2 must be greater than zero" in issues
    assert "rules.max_nodes must be at least 1" in issues


def test_validate_design_reports_unhashable_schema_values_without_crashing():
    document = {
        "schema": "loopwright/2",
        "plan_id": "demo",
        "frame": {"units": "drawing", "m_per_unit": 1},
        "rules": {"max_area_m2": 100, "max_nodes": 5, "zone_link": [], "axis_aligned": True},
        "weights": {},
        "rooms": [{"id": [], "type": "living", "area_m2": 10, "eligible": True}],
        "hubs": [],
        "nodes": [],
        "rings": [],
        "metrics": {"hubs": 0, "hub_lower_bound": 0, "length_m": 0, "bends": 0, "J": 0},
        "ranking_key": [0, 0],
        "validation": {"valid": False, "checks": []},
        "reviewer": [],
        "diagnostics": [],
    }

    issues = validate_design(document)

    assert "rules.zone_link is invalid" in issues
    assert "rooms[0].id must be a non-empty string" in issues


def test_load_design_rejects_non_standard_json_numbers(tmp_path):
    path = tmp_path / "nan.json"
    path.write_text('{"value": NaN}', encoding="utf-8")

    with pytest.raises(DesignValidationError, match="invalid JSON"):
        load_design(path)
