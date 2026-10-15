import shapely
from shapely.errors import GEOSException
from shapely.geometry import Polygon


def flat(g):
    if g is None or g.is_empty:
        return []
    if hasattr(g, "geoms"):
        out = []
        for part in g.geoms:
            out.extend(flat(part))
        return out
    return [g]


def valid(g):
    if g is None:
        return None
    try:
        return shapely.make_valid(g)
    except (GEOSException, ValueError):
        return g.buffer(0)


def polygons(g, min_area=0.0):
    return [p for p in flat(valid(g)) if isinstance(p, Polygon) and p.area >= min_area]


def largest(g):
    parts = [p for p in flat(g) if isinstance(p, Polygon)]
    return max(parts, key=lambda p: p.area) if parts else None
