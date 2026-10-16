"""The door graph: spaces joined by doors and open passages.

Ported from the 15 Oct dataset analysis (all 17,000 plans).
"""
import shapely
from shapely.geometry import LineString, MultiLineString, Polygon
from shapely.ops import unary_union

from loopwright.geometry.heal import flat, valid
from loopwright.geometry.spaces import Space


def circulation_pockets(model):
    """Indoor space with no room label (hallways not drawn as part of the living room)."""
    wd = model.wall_depth
    s2 = model.m_per_unit ** 2
    blockers = [sp.geom for sp in model.spaces]
    blockers += [g for k, g in model.layers.items() if k != "inner" and g is not None and not g.is_empty]
    try:
        free = model.layers["inner"].difference(unary_union(blockers))
        free = free.buffer(-0.25 * wd).buffer(0.25 * wd)
    except Exception:
        return []
    keep = max((2 * wd) ** 2, 1.0 / s2)
    pockets = [p for p in flat(free) if isinstance(p, Polygon) and p.area >= keep]
    return [Space(f"circulation_{i}", "circulation", p, p.area * s2, False) for i, p in enumerate(pockets)]


def door_graph(model):
    """Return (spaces, adjacency) where adjacency maps space id to the set of joined space ids."""
    spaces = list(model.spaces) + circulation_pockets(model)
    adj = {sp.id: set() for sp in spaces}
    if len(spaces) < 2:
        return spaces, adj
    wd = model.wall_depth
    x1, y1, x2, y2 = model.layers["inner"].bounds
    buf = max(max(x2 - x1, y2 - y1) * 0.007, 0.5)
    grown = [sp.geom.buffer(buf) for sp in spaces]
    tree = shapely.STRtree(grown)

    def link(i, j):
        adj[spaces[i].id].add(spaces[j].id)
        adj[spaces[j].id].add(spaces[i].id)

    doors = []
    for d in flat(model.layers.get("door")):
        if isinstance(d, (LineString, MultiLineString)):
            d = d.buffer(0.5)
        if isinstance(d, Polygon):
            doors.append(d)
    for d in doors:
        hit = [int(i) for i in tree.query(d, predicate="intersects")]
        if len(hit) < 2:
            continue
        if len(hit) > 2:
            scored = sorted(((i, d.boundary.intersection(spaces[i].geom.buffer(buf * 0.6)).length) for i in hit),
                            key=lambda t: t[1], reverse=True)
            best = scored[0][1]
            hit = [scored[0][0], scored[1][0]] + [i for i, sc in scored[2:] if sc >= 0.25 * best and sc >= buf]
        for a in range(len(hit)):
            for b in range(a + 1, len(hit)):
                link(hit[a], hit[b])

    walls = valid(model.layers.get("wall"))
    dil = [sp.geom.buffer(wd * 0.55) for sp in spaces]
    tree2 = shapely.STRtree(dil)
    for i in range(len(spaces)):
        for j in tree2.query(dil[i], predicate="intersects"):
            j = int(j)
            if j <= i or spaces[j].id in adj[spaces[i].id]:
                continue
            try:
                gap = dil[i].intersection(dil[j])
                if walls is not None and not walls.is_empty:
                    gap = gap.difference(walls)
            except Exception:
                continue
            for piece in flat(gap):
                bx1, by1, bx2, by2 = piece.bounds
                if max(bx2 - bx1, by2 - by1) >= 2 * wd and piece.area >= 0.25 * wd * wd:
                    link(i, j)
                    break
    return spaces, adj


def connector_ids(spaces, zone_link):
    """Spaces a zone may pass through to stay connected, for each zone rule (Q1)."""
    if zone_link == "strict":
        return set()
    if zone_link == "circulation":
        return {sp.id for sp in spaces if sp.type in ("circulation", "bathroom", "stair")}
    return {sp.id for sp in spaces}


def is_connected(room_ids, adj, connectors):
    room_ids = list(room_ids)
    if len(room_ids) <= 1:
        return True
    allowed = set(room_ids) | connectors
    seen, stack = {room_ids[0]}, [room_ids[0]]
    while stack:
        u = stack.pop()
        for v in adj.get(u, ()):
            if v in allowed and v not in seen:
                seen.add(v)
                stack.append(v)
    return all(r in seen for r in room_ids)
