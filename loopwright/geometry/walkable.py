"""The walkable region: where cable may run, before any clearance.

inner minus walls (doors stay open), windows and external areas. Solver,
router and zoning all use this one definition so they can't disagree about
what is reachable.
"""
import math

from shapely.geometry import MultiPoint, Point, Polygon
from shapely.ops import polylabel, unary_union

from loopwright.geometry.heal import flat

EXTERNAL = ("window", "balcony", "garden", "pool", "parking")
# A door opens the wall it is drawn in from face to face (assumptions Q18). ResPlan draws some doors shallower
# than their wall (plan 4755: 3 cm short), and a door drawn to x = 7.699999999999999 in a wall drawn to 7.7 leaves
# a sliver, so wall within DOOR_REACH wall depths of a door's long side is doorway too when it runs at least
# DOOR_SPAN of the door's width. A wall that only meets the door's side is shorter than that and stays.
DOOR_REACH = 0.5
DOOR_SPAN = 0.9


def door_cut(door, walls, reach):
    """The door, and the strips of wall left in front of it: within reach of a long side, along its whole width."""
    rect = door.minimum_rotated_rectangle
    if not isinstance(rect, Polygon):
        return door
    c = list(rect.exterior.coords)[:4]
    a, b = (c[1][0] - c[0][0], c[1][1] - c[0][1]), (c[2][0] - c[1][0], c[2][1] - c[1][1])
    across, along = (a, b) if math.hypot(*a) <= math.hypot(*b) else (b, a)
    depth, width = math.hypot(*across), math.hypot(*along)
    if depth == 0:
        return door
    dx, dy = across[0] / depth * reach, across[1] / depth * reach
    front = MultiPoint([(x + k * dx, y + k * dy) for x, y in c for k in (-1, 1)]).convex_hull
    ux, uy = along[0] / width, along[1] / width
    strips = []
    for piece in flat(walls.intersection(front).difference(door)):
        if isinstance(piece, Polygon):
            t = [x * ux + y * uy for x, y in piece.exterior.coords]
            if max(t) - min(t) >= DOOR_SPAN * width:
                strips.append(piece)
    return unary_union([door, *strips])


def open_walls(layers, wall_depth):
    """The walls with every door cut through them, or None for a plan without walls."""
    walls, doors = layers.get("wall"), layers.get("door")
    if walls is None or walls.is_empty:
        return None
    if doors is None or doors.is_empty:
        return walls
    cuts = [door_cut(d, walls, DOOR_REACH * wall_depth) for d in flat(doors) if isinstance(d, Polygon)]
    return walls.difference(unary_union(cuts)) if cuts else walls


def walkable_region(model):
    layers = model.layers
    blocked = [g for g in [open_walls(layers, model.wall_depth)] + [layers.get(k) for k in EXTERNAL]
               if g is not None and not g.is_empty]
    return layers["inner"].difference(unary_union(blocked)) if blocked else layers["inner"]


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


def walkable_hub(room_geom, node, region, m_per_unit, min_m=0.5, others=(), keep_m=0.15):
    """A hub point in the room's walkable part, min_m from the node (as close as allowed: a
    one-room ring runs there and back) and from the zone's other nodes, straight across first
    so its legs have no bend. Points keep_m inside the walkable part come first, so the hub
    stays clear of the router's wall clearance."""
    part = room_geom.intersection(region)
    roomy = part.buffer(-keep_m / m_per_unit)
    x, y = node
    far = [Point(o) for o in others]
    clear = (min_m - 1e-3) / m_per_unit
    for area in (roomy, part):
        for offset_m in (min_m, min_m + 0.25, min_m + 0.5, min_m + 1.0, min_m + 2.0):
            d = max(offset_m, 1e-3) / m_per_unit
            e = d / 2 ** 0.5
            for dx, dy in ((d, 0), (-d, 0), (0, d), (0, -d), (e, e), (-e, e), (e, -e), (-e, -e)):
                q = Point(x + dx, y + dy)
                if area.contains(q) and all(q.distance(o) >= clear for o in far):
                    return (round(q.x, 3), round(q.y, 3))
    q = part.representative_point() if not part.is_empty else Point(x + min_m / m_per_unit, y)
    return (round(q.x, 3), round(q.y, 3))
