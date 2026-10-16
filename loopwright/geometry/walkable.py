"""The walkable region: where cable may run, before any clearance.

inner minus walls (doors stay open), windows and external areas. Solver,
router and zoning all use this one definition so they can't disagree about
what is reachable.
"""
from shapely.geometry import Point, Polygon
from shapely.ops import polylabel, unary_union

from loopwright.geometry.heal import flat

EXTERNAL = ("window", "balcony", "garden", "pool", "parking")


def walkable_region(model):
    layers = model.layers
    blocked = []
    walls, doors = layers.get("wall"), layers.get("door")
    if walls is not None and not walls.is_empty:
        blocked.append(walls.difference(doors) if doors is not None and not doors.is_empty else walls)
    blocked += [layers[k] for k in EXTERNAL if layers.get(k) is not None and not layers[k].is_empty]
    region = layers["inner"]
    return region.difference(unary_union(blocked)) if blocked else region


def pieces(region):
    return sorted((p for p in flat(region) if isinstance(p, Polygon)), key=lambda p: -p.area)


def piece_index(point, parts):
    pt = Point(point)
    for k, part in enumerate(parts):
        if part.covers(pt):
            return k
    return None


def walkable_node(room_geom, region, m_per_unit):
    """A node inside the walkable part of a room (its largest piece), or None."""
    usable = [p for p in flat(room_geom.intersection(region)) if isinstance(p, Polygon)]
    if not usable:
        return None
    piece = max(usable, key=lambda p: p.area)
    p = polylabel(piece, tolerance=0.05 / m_per_unit)
    if not piece.contains(p):
        p = piece.representative_point()
    return (round(p.x, 3), round(p.y, 3))


def walkable_hub(room_geom, node, region, m_per_unit, min_m=0.5, others=()):
    """A hub point in the room's walkable part, min_m from the node (as close as allowed: a
    one-room ring runs there and back) and from the zone's other nodes, straight across first
    so its legs have no bend."""
    part = room_geom.intersection(region)
    x, y = node
    far = [Point(o) for o in others]
    clear = (min_m - 1e-3) / m_per_unit
    for offset_m in (min_m, min_m + 0.25, min_m + 0.5, min_m + 1.0, min_m + 2.0):
        d = max(offset_m, 1e-3) / m_per_unit
        e = d / 2 ** 0.5
        for dx, dy in ((d, 0), (-d, 0), (0, d), (0, -d), (e, e), (-e, e), (e, -e), (-e, -e)):
            q = Point(x + dx, y + dy)
            if part.contains(q) and all(q.distance(o) >= clear for o in far):
                return (round(q.x, 3), round(q.y, 3))
    q = part.representative_point() if not part.is_empty else Point(x + min_m / m_per_unit, y)
    return (round(q.x, 3), round(q.y, 3))
