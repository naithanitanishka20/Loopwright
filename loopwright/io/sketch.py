"""Build a full plan from room outlines and the pairs of rooms that share a door.

The drawing editor, the DXF importer and the image importer all produce room
outlines in metres. Adjacent outlines share an edge; the wall between them is
centred on that edge, half in each room. Every connected pair gets a door in
the middle of the shared edge; like ResPlan's doors, it is an opening in the
wall, which the solver and validator subtract from the wall layer.
"""
from shapely.geometry import LineString, MultiPolygon, Polygon
from shapely.ops import unary_union

from loopwright.geometry.heal import flat, valid

ROOM_TYPES = ("living", "bedroom", "kitchen", "storage", "bathroom", "stair")
DOOR_WIDTH_M = 0.9


def _shared_edge(a, b):
    lines = [g for g in flat(a.boundary.intersection(b.boundary)) if isinstance(g, LineString)]
    return max(lines, key=lambda g: g.length) if lines else None


def _door(edge, wall_m):
    width = min(DOOR_WIDTH_M, 0.8 * edge.length)
    mid = edge.length / 2
    p0, p1 = edge.interpolate(mid - width / 2), edge.interpolate(mid + width / 2)
    return LineString([p0, p1]).buffer(wall_m / 2, cap_style="flat")


def build_plan(rooms, doors, *, wall_m=0.1, plan_id="sketch"):
    """rooms: [{"type": ..., "polygon": [[x, y], ...]}] in metres; doors: [(i, j), ...] room indices."""
    outlines = []
    for k, room in enumerate(rooms):
        if room.get("type") not in ROOM_TYPES:
            raise ValueError(f"room {k}: unknown room type {room.get('type')!r}; use one of {ROOM_TYPES}")
        outlines.append(valid(Polygon(room["polygon"])))

    cuts = []
    for i, j in doors:
        edge = _shared_edge(outlines[i], outlines[j])
        if edge is None or edge.length <= wall_m:
            raise ValueError(f"rooms {i} and {j} share no wall to put a door in")
        cuts.append(_door(edge, wall_m))

    inner = unary_union(outlines)
    interiors = [o.buffer(-wall_m / 2, join_style="mitre") for o in outlines]
    walls = inner.difference(unary_union(interiors))
    door_layer = unary_union(cuts) if cuts else Polygon()

    plan = {"id": plan_id, "m_per_unit": 1.0, "wall_depth": wall_m, "inner": inner,
            "wall": walls, "door": door_layer}
    for t in ROOM_TYPES:
        parts = [p for room, interior in zip(rooms, interiors) if room["type"] == t
                 for p in flat(interior) if isinstance(p, Polygon)]
        if parts:
            plan[t] = MultiPolygon(parts)
    return plan
