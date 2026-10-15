"""Geometry repair helpers. Raw ResPlan polygons can be invalid."""
import shapely
from shapely.geometry import Polygon


def flat(g):
    """Every non-empty part of a geometry, recursively."""
    if g is None or g.is_empty:
        return []
    if hasattr(g, "geoms"):
        out = []
        for part in g.geoms:
            out.extend(flat(part))
        return out
    return [g]


def valid(g):
    """A valid version of g, or None."""
    if g is None:
        return None
    try:
        return shapely.make_valid(g)
    except Exception:
        return g.buffer(0)


def polygons(g, min_area=0.0):
    """Valid polygon parts of g with at least min_area (plan units squared)."""
    return [p for p in flat(valid(g)) if isinstance(p, Polygon) and p.area >= min_area]


def largest(g):
    """The largest polygon part of g."""
    parts = [p for p in flat(g) if isinstance(p, Polygon)]
    return max(parts, key=lambda p: p.area) if parts else None
