"""Adapter for the organisers' one-JSON-per-plan files.

Their schema is still pending (assumptions Q5). Until a sample arrives this
accepts geometry as WKT strings, GeoJSON objects or coordinate lists, and maps
room keys through an alias table onto ResPlan's keys. A missing required key
raises with its name instead of being guessed.
"""
import json
import pathlib

import shapely
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


def parse_geometry(value):
    """WKT string, GeoJSON object, ring of [x, y] points, or a list of rings."""
    if value is None:
        return None
    if isinstance(value, str):
        return shapely.from_wkt(value)
    if isinstance(value, dict) and "type" in value:
        return shape(value)
    if isinstance(value, list) and value:
        if all(isinstance(v, (list, tuple)) and len(v) == 2 and all(isinstance(c, (int, float)) for c in v) for v in value):
            return Polygon(value)
        parts = [parse_geometry(v) for v in value]
        polys = [p for p in parts if isinstance(p, Polygon)]
        if polys and len(polys) == len(parts):
            return MultiPolygon(polys)
        return shapely.GeometryCollection(parts)
    raise ValueError(f"unrecognised geometry: {str(value)[:80]}")


def from_dict(raw: dict) -> dict:
    plan = {}
    for key, value in raw.items():
        k = key.strip().lower().replace(" ", "_")
        if k in SCALARS:
            plan[k] = value
        elif k in ALIASES:
            plan[ALIASES[k]] = parse_geometry(value)
    if plan.get("inner") is None:
        raise ValueError("organiser JSON has no building boundary ('inner' or 'boundary')")
    if not plan.get("area") and not plan.get("m_per_unit"):
        raise ValueError("organiser JSON has neither 'area' nor 'm_per_unit'; can't compute scale")
    return plan


def load_json(path) -> dict:
    with open(pathlib.Path(path), encoding="utf-8") as f:
        return from_dict(json.load(f))
