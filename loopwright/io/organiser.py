import json
import math
import pathlib

import shapely
from shapely.errors import GEOSException
from shapely.geometry import MultiPolygon, Polygon, shape

ALIASES = {
    "living": "living", "livingroom": "living", "living_room": "living", "lounge": "living",
    "bedroom": "bedroom", "bed": "bedroom", "bedrooms": "bedroom",
    "kitchen": "kitchen",
    "storage": "storage", "store": "storage", "storeroom": "storage",
    "bathroom": "bathroom", "bath": "bathroom", "wc": "bathroom", "toilet": "bathroom",
    "balcony": "balcony", "balacony": "balcony",
    "stair": "stair", "stairs": "stair",
    "wall": "wall", "walls": "wall",
    "door": "door", "doors": "door",
    "window": "window", "windows": "window",
    "front_door": "front_door", "entrance": "front_door",
    "inner": "inner", "boundary": "inner",
    "garden": "garden", "pool": "pool", "parking": "parking", "land": "land",
}
SCALARS = {"id", "area", "net_area", "wall_depth", "m_per_unit"}


def _check_coordinates(value):
    if isinstance(value, (list, tuple)):
        for part in value:
            _check_coordinates(part)
        return
    if isinstance(value, bool) or not isinstance(value, (int, float)) or not math.isfinite(value):
        raise ValueError("geometry coordinates must be finite numbers")


def _check_geometry(geom):
    if geom is not None and not geom.is_empty and not all(math.isfinite(v) for v in geom.bounds):
        raise ValueError("geometry coordinates must be finite numbers")
    return geom


def parse_geometry(value):
    if value is None:
        return None
    try:
        if isinstance(value, str):
            return _check_geometry(shapely.from_wkt(value))
        if isinstance(value, dict) and "type" in value:
            if "coordinates" in value:
                _check_coordinates(value["coordinates"])
            return _check_geometry(shape(value))
        if isinstance(value, (list, tuple)) and value:
            if all(isinstance(v, (list, tuple)) and len(v) == 2 for v in value):
                _check_coordinates(value)
                return _check_geometry(Polygon(value))
            parts = [parse_geometry(part) for part in value]
            polys = [part for part in parts if isinstance(part, Polygon)]
            if polys and len(polys) == len(parts):
                return _check_geometry(MultiPolygon(polys))
            return _check_geometry(shapely.GeometryCollection(parts))
    except GEOSException as exc:
        raise ValueError("invalid geometry") from exc
    raise ValueError(f"unrecognised geometry: {str(value)[:80]}")


def from_dict(raw: dict) -> dict:
    if not isinstance(raw, dict):
        raise ValueError("organiser JSON must be an object")
    plan = {}
    for key, value in raw.items():
        if not isinstance(key, str):
            raise ValueError("organiser JSON keys must be strings")
        k = key.strip().lower().replace(" ", "_")
        if k in SCALARS:
            plan[k] = value
        elif k in ALIASES:
            plan[ALIASES[k]] = parse_geometry(value)
    if plan.get("inner") is None:
        raise ValueError("organiser JSON has no building boundary ('inner' or 'boundary')")
    for name in ("area", "m_per_unit"):
        if name in plan:
            value = plan[name]
            if isinstance(value, bool) or not isinstance(value, (int, float)) or not math.isfinite(value) or value <= 0:
                raise ValueError(f"organiser JSON '{name}' must be a finite number greater than zero")
    if "area" not in plan and "m_per_unit" not in plan:
        raise ValueError("organiser JSON has neither 'area' nor 'm_per_unit'; can't compute scale")
    return plan


def load_json(path) -> dict:
    with open(pathlib.Path(path), encoding="utf-8") as f:
        return from_dict(json.load(f))
