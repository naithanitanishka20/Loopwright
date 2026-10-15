"""One node per eligible room (assumptions Q6: pole of inaccessibility)."""
from shapely.geometry import Point
from shapely.ops import polylabel

from loopwright.config import DEFAULT
from loopwright.geometry.heal import largest


def place_nodes(model, settings=DEFAULT):
    """Map room id to an (x, y) node position inside that room, in plan units."""
    tolerance = 0.05 / model.m_per_unit
    nodes = {}
    for sp in model.eligible:
        piece = largest(sp.geom)
        p = polylabel(piece, tolerance=tolerance)
        if not piece.contains(p):
            p = piece.representative_point()
        nodes[sp.id] = (round(p.x, 3), round(p.y, 3))
    return nodes


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
