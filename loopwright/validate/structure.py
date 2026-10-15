"""Structural checks on a loopwright/2 document, before any rule is checked.

Types, required keys from docs/schema-v2.json, finite numbers, no booleans used
as numbers, and no NaN or Infinity in the JSON. Needs no plan, so it runs on any
output file; rules.py then checks V00-V14 against the plan.
"""
from __future__ import annotations

import json
import math
from pathlib import Path


SCHEMA = "loopwright/2"
REQUIRED = (
    "schema",
    "plan_id",
    "frame",
    "rules",
    "weights",
    "rooms",
    "hubs",
    "nodes",
    "rings",
    "metrics",
    "ranking_key",
    "validation",
    "reviewer",
    "diagnostics",
)


class DesignValidationError(ValueError):
    def __init__(self, issues):
        self.issues = list(issues)
        super().__init__("; ".join(self.issues))


def _number(value):
    return isinstance(value, (int, float)) and not isinstance(value, bool) and math.isfinite(value)


def _object(value, name, issues):
    if not isinstance(value, dict):
        issues.append(f"{name} must be an object")
        return False
    return True


def _array(value, name, issues):
    if not isinstance(value, list):
        issues.append(f"{name} must be an array")
        return False
    return True


def _point(value, name, issues):
    if not isinstance(value, list) or len(value) != 2 or not all(_number(coord) for coord in value):
        issues.append(f"{name} must contain two finite numbers")


def _nonnegative(value, name, issues):
    if not _number(value) or value < 0:
        issues.append(f"{name} must be a finite non-negative number")


def _integer(value, name, issues, minimum=None):
    if type(value) is not int or minimum is not None and value < minimum:
        suffix = f" at least {minimum}" if minimum is not None else ""
        issues.append(f"{name} must be an integer{suffix}")


def _required_object_fields(value, name, required, issues):
    if not _object(value, name, issues):
        return False
    missing = [field for field in required if field not in value]
    if missing:
        issues.append(f"{name} missing required fields: {', '.join(missing)}")
    return True


def validate_design(document):
    issues = []
    if not isinstance(document, dict):
        return ["document must be an object"]

    missing = [field for field in REQUIRED if field not in document]
    if missing:
        issues.append(f"missing required fields: {', '.join(missing)}")
    if document.get("schema") != SCHEMA:
        issues.append("schema must be 'loopwright/2'")
    if "plan_id" in document and not (type(document["plan_id"]) is int or isinstance(document["plan_id"], str)):
        issues.append("plan_id must be an integer or string")

    frame = document.get("frame")
    if _required_object_fields(frame, "frame", ("units", "m_per_unit"), issues):
        if not isinstance(frame.get("units"), str) or not frame["units"]:
            issues.append("frame.units must be a non-empty string")
        if not _number(frame.get("m_per_unit")):
            issues.append("frame.m_per_unit must be a finite number")
        elif frame["m_per_unit"] <= 0:
            issues.append("frame.m_per_unit must be greater than zero")

    rules = document.get("rules")
    if _required_object_fields(rules, "rules", ("max_area_m2", "max_nodes", "zone_link", "axis_aligned"), issues):
        if not _number(rules.get("max_area_m2")):
            issues.append("rules.max_area_m2 must be a finite number")
        elif rules["max_area_m2"] <= 0:
            issues.append("rules.max_area_m2 must be greater than zero")
        if type(rules.get("max_nodes")) is not int:
            issues.append("rules.max_nodes must be an integer")
        elif rules["max_nodes"] < 1:
            issues.append("rules.max_nodes must be at least 1")
        if not isinstance(rules.get("zone_link"), str) or rules["zone_link"] not in {
            "strict",
            "circulation",
            "through_rooms",
            "none",
        }:
            issues.append("rules.zone_link is invalid")
        if type(rules.get("axis_aligned")) is not bool:
            issues.append("rules.axis_aligned must be a boolean")

    if "weights" in document and not isinstance(document["weights"], dict):
        issues.append("weights must be an object")
    if _array(document.get("rooms"), "rooms", issues):
        _validate_rooms(document["rooms"], issues)
    if _array(document.get("hubs"), "hubs", issues):
        _validate_hubs(document["hubs"], issues)
    if _array(document.get("nodes"), "nodes", issues):
        _validate_nodes(document["nodes"], issues)
    if _array(document.get("rings"), "rings", issues):
        _validate_rings(document["rings"], issues)

    metrics = document.get("metrics")
    if _required_object_fields(metrics, "metrics", ("hubs", "hub_lower_bound", "length_m", "bends", "J"), issues):
        for field in ("length_m", "J"):
            _nonnegative(metrics.get(field), f"metrics.{field}", issues)
        for field in ("hubs", "hub_lower_bound", "bends"):
            _integer(metrics.get(field), f"metrics.{field}", issues, minimum=0)

    if _array(document.get("ranking_key"), "ranking_key", issues) and len(document["ranking_key"]) < 2:
        issues.append("ranking_key must contain at least two values")
    validation = document.get("validation")
    if _required_object_fields(validation, "validation", ("valid", "checks"), issues):
        if type(validation.get("valid")) is not bool:
            issues.append("validation.valid must be a boolean")
        if not isinstance(validation.get("checks"), list):
            issues.append("validation.checks must be an array")
    if _array(document.get("reviewer"), "reviewer", issues):
        if not all(isinstance(note, str) for note in document["reviewer"]):
            issues.append("reviewer entries must be strings")
    if _array(document.get("diagnostics"), "diagnostics", issues):
        for index, diagnostic in enumerate(document["diagnostics"]):
            _required_object_fields(diagnostic, f"diagnostics[{index}]", ("code",), issues)

    return issues


def _validate_rooms(rooms, issues):
    ids = set()
    for index, room in enumerate(rooms):
        name = f"rooms[{index}]"
        if not _required_object_fields(room, name, ("id", "type", "area_m2", "eligible"), issues):
            continue
        if not isinstance(room.get("id"), str) or not room["id"]:
            issues.append(f"{name}.id must be a non-empty string")
        elif room["id"] in ids:
            issues.append(f"{name}.id is duplicated")
        if isinstance(room.get("id"), str):
            ids.add(room["id"])
        if not isinstance(room.get("type"), str):
            issues.append(f"{name}.type must be a string")
        _nonnegative(room.get("area_m2"), f"{name}.area_m2", issues)
        if type(room.get("eligible")) is not bool:
            issues.append(f"{name}.eligible must be a boolean")


def _validate_hubs(hubs, issues):
    for index, hub in enumerate(hubs):
        name = f"hubs[{index}]"
        if not _required_object_fields(hub, name, ("id", "pos", "room", "zone", "area_m2", "nodes"), issues):
            continue
        if not isinstance(hub.get("id"), str) or not hub["id"]:
            issues.append(f"{name}.id must be a non-empty string")
        _point(hub.get("pos"), f"{name}.pos", issues)
        if not isinstance(hub.get("room"), str):
            issues.append(f"{name}.room must be a string")
        if not isinstance(hub.get("zone"), list) or not all(isinstance(zone, str) for zone in hub.get("zone", [])):
            issues.append(f"{name}.zone must be an array of strings")
        _nonnegative(hub.get("area_m2"), f"{name}.area_m2", issues)
        _integer(hub.get("nodes"), f"{name}.nodes", issues, minimum=0)


def _validate_nodes(nodes, issues):
    for index, node in enumerate(nodes):
        name = f"nodes[{index}]"
        if not _required_object_fields(node, name, ("id", "room", "pos", "hub", "order"), issues):
            continue
        for field in ("id", "room", "hub"):
            if not isinstance(node.get(field), str) or not node[field]:
                issues.append(f"{name}.{field} must be a non-empty string")
        _point(node.get("pos"), f"{name}.pos", issues)
        _integer(node.get("order"), f"{name}.order", issues, minimum=1)


def _validate_rings(rings, issues):
    for index, ring in enumerate(rings):
        name = f"rings[{index}]"
        if not _required_object_fields(ring, name, ("hub", "sequence", "legs", "length_m", "bends"), issues):
            continue
        if not isinstance(ring.get("hub"), str) or not ring["hub"]:
            issues.append(f"{name}.hub must be a non-empty string")
        if not isinstance(ring.get("sequence"), list) or not all(isinstance(node, str) for node in ring.get("sequence", [])):
            issues.append(f"{name}.sequence must be an array of strings")
        _nonnegative(ring.get("length_m"), f"{name}.length_m", issues)
        _integer(ring.get("bends"), f"{name}.bends", issues, minimum=0)
        if not _array(ring.get("legs"), f"{name}.legs", issues):
            continue
        for leg_index, leg in enumerate(ring["legs"]):
            leg_name = f"{name}.legs[{leg_index}]"
            if not _required_object_fields(leg, leg_name, ("n", "from", "to", "path", "length_m", "bends"), issues):
                continue
            _integer(leg.get("n"), f"{leg_name}.n", issues, minimum=1)
            for field in ("from", "to"):
                if not isinstance(leg.get(field), str):
                    issues.append(f"{leg_name}.{field} must be a string")
            if _array(leg.get("path"), f"{leg_name}.path", issues):
                if len(leg["path"]) < 2:
                    issues.append(f"{leg_name}.path must contain at least two points")
                for point_index, point in enumerate(leg["path"]):
                    _point(point, f"{leg_name}.path[{point_index}]", issues)
            _nonnegative(leg.get("length_m"), f"{leg_name}.length_m", issues)
            _integer(leg.get("bends"), f"{leg_name}.bends", issues, minimum=0)


def load_design(path):
    path = Path(path)
    try:
        document = json.loads(path.read_text(encoding="utf-8-sig"), parse_constant=_reject_constant)
    except (OSError, UnicodeError) as exc:
        raise DesignValidationError([f"cannot read design: {exc}"]) from exc
    except json.JSONDecodeError as exc:
        raise DesignValidationError([f"invalid JSON: {exc.msg}"]) from exc
    except ValueError as exc:
        raise DesignValidationError([f"invalid JSON: {exc}"]) from exc
    issues = validate_design(document)
    if issues:
        raise DesignValidationError(issues)
    return document


def _reject_constant(value):
    raise ValueError(f"non-standard number {value}")
