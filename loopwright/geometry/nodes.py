"""One node per eligible room (assumptions Q6).

The organisers leave the node's position to us, as long as it keeps 0.5 m from the
walls. A ring has to reach every node through the room's doors, so the node goes where
the cable already passes: the point at least that far from the walls with the least total
distance to the room's openings (just inside the door of a one-door room). A room with no
opening, or rule "pole", keeps the point farthest from its walls.
"""
import numpy as np
import shapely
from shapely.geometry import Point
from shapely.ops import nearest_points, polylabel, unary_union

from loopwright.config import DEFAULT
from loopwright.geometry.heal import flat, largest


# polylabel precision: the pole found is within this of the true farthest point from the walls
POLE_TOLERANCE_M = 0.01


def room_pole(geom, m_per_unit):
    """The point of the room (its largest piece) farthest from its walls, and that distance in metres."""
    piece = largest(geom)
    p = polylabel(piece, tolerance=POLE_TOLERANCE_M / m_per_unit)
    if not piece.contains(p):
        p = piece.representative_point()
    return p, piece.boundary.distance(p) * m_per_unit


def place_nodes(model, settings=DEFAULT):
    """Map room id to an (x, y) node position inside that room, in plan units."""
    nodes = {}
    barrier = _barrier(model.layers, model.wall_depth) if settings.node_rule == "near_doors" else None
    for sp in model.eligible:
        p = None
        if barrier is not None:
            piece = largest(sp.geom)
            p = near_openings(piece, room_openings(piece, barrier, model.wall_depth),
                              model.m_per_unit, settings.node_wall_m)
        if p is None:
            p, _ = room_pole(sp.geom, model.m_per_unit)
        nodes[sp.id] = (round(p.x, 3), round(p.y, 3))
    return nodes


def _barrier(layers, wall_depth):
    """Walls (doors cut out) and windows, grown a little so the room outline along them drops out."""
    walls, doors, windows = layers.get("wall"), layers.get("door"), layers.get("window")
    blockers = []
    if walls is not None and not walls.is_empty:
        blockers.append(walls.difference(doors) if doors is not None and not doors.is_empty else walls)
    if windows is not None and not windows.is_empty:
        blockers.append(windows)
    if not blockers:
        return shapely.Polygon()
    barrier = unary_union(blockers).buffer(0.3 * wall_depth)
    shapely.prepare(barrier)
    return barrier


def room_openings(piece, barrier, wall_depth):
    """Middles of the stretches of the room's outline with no wall or window: its doors and open passages."""
    outline = piece.boundary.difference(barrier) if not barrier.is_empty else piece.boundary
    return [g.interpolate(0.5, normalized=True) for g in flat(outline) if g.length >= wall_depth]


def near_openings(piece, openings, m_per_unit, wall_m, step_m=0.25):
    """The point at least wall_m from the walls with the least total axis distance to the openings, or None."""
    allowed = piece.buffer(-(wall_m + 0.01) / m_per_unit)  # 1 cm to spare on the wall distance
    if allowed.is_empty or not openings:
        return None
    ox = np.array([o.x for o in openings])
    oy = np.array([o.y for o in openings])
    x1, y1, x2, y2 = allowed.bounds
    step = max(step_m / m_per_unit, (allowed.area / 2500) ** 0.5)  # at most about 2,500 candidates
    gx, gy = np.meshgrid(np.arange(x1, x2 + step, step), np.arange(y1, y2 + step, step))
    inside = shapely.contains_xy(allowed, gx, gy)
    cx = np.concatenate([gx[inside], [nearest_points(allowed, o)[0].x for o in openings]])
    cy = np.concatenate([gy[inside], [nearest_points(allowed, o)[0].y for o in openings]])
    cost = np.abs(cx[:, None] - ox[None, :]).sum(axis=1) + np.abs(cy[:, None] - oy[None, :]).sum(axis=1)
    k = int(np.argmin(cost))
    return Point(cx[k], cy[k])


def hub_point(room_geom, node, m_per_unit, offset_m=0.6):
    """A hub position inside the room, offset from its node so legs have length."""
    piece = largest(room_geom)
    d = offset_m / m_per_unit
    x, y = node
    for dx, dy in ((d, 0), (-d, 0), (0, d), (0, -d)):
        q = Point(x + dx, y + dy)
        if piece.contains(q):
            return (round(q.x, 3), round(q.y, 3))
    q = piece.representative_point()
    return (round(q.x, 3), round(q.y, 3))
