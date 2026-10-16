"""Edits to a plan, applied before solving: remove a door, connect two rooms, change a room's type.

Rooms are named as the solver names them (living_0, bedroom_1, ...), and doors
by their position in door_parts(plan). Every edit returns a new plan dict; the
input is never changed.
"""
from shapely.geometry import LineString, MultiPolygon, Point, Polygon
from shapely.ops import nearest_points, unary_union

from loopwright.config import DEFAULT
from loopwright.geometry.heal import flat, polygons, valid
from loopwright.geometry.spaces import build_model
from loopwright.io.sketch import DOOR_WIDTH_M, ROOM_TYPES


def door_parts(plan):
    """The plan's doors as separate polygons, in a stable order."""
    return polygons(plan.get("door"))


def _remove_door(plan, k):
    doors = door_parts(plan)
    if not isinstance(k, int) or not 0 <= k < len(doors):
        raise ValueError(f"no door {k!r}; the plan has {len(doors)}")
    rooms = unary_union([g for t in ROOM_TYPES for g in polygons(plan.get(t))])
    fill = doors[k].difference(rooms)
    out = dict(plan)
    out["door"] = unary_union(doors[:k] + doors[k + 1:]) if len(doors) > 1 else Polygon()
    out["wall"] = unary_union([valid(plan.get("wall")) or Polygon(), fill])
    return out


def _facing_edge(a, b, reach):
    near = a.boundary.intersection(b.buffer(reach))
    lines = [g for g in flat(near) if isinstance(g, LineString)]
    return max(lines, key=lambda g: g.length) if lines else None


def _connect(plan, room_a, room_b, settings):
    model = build_model(plan, settings)
    geoms = {sp.id: sp.geom for sp in model.spaces}
    for r in (room_a, room_b):
        if r not in geoms:
            raise ValueError(f"no room {r!r}; rooms are {sorted(geoms)}")
    a, b = geoms[room_a], geoms[room_b]
    edge = None
    for factor in (1.5, 3.0, 6.0):
        edge = _facing_edge(a, b, factor * model.wall_depth)
        if edge is not None and edge.length > model.wall_depth:
            break
    if edge is None or edge.length <= model.wall_depth:
        raise ValueError(f"rooms {room_a} and {room_b} are not next to each other")
    width = min(DOOR_WIDTH_M / model.m_per_unit, 0.8 * edge.length)
    mid = edge.length / 2
    p0, p1 = edge.interpolate(mid - width / 2), edge.interpolate(mid + width / 2)
    q0 = nearest_points(Point(p0), b.boundary)[1]
    q1 = nearest_points(Point(p1), b.boundary)[1]
    door = Polygon([p0, p1, q1, q0]).buffer(0.01 / model.m_per_unit, join_style="mitre")
    out = dict(plan)
    # A door is an opening wherever it lies: every consumer subtracts doors from walls.
    out["door"] = unary_union([valid(plan.get("door")) or Polygon(), door])
    return out


def _set_type(plan, room, to, settings):
    if to not in ROOM_TYPES:
        raise ValueError(f"unknown room type {to!r}; use one of {ROOM_TYPES}")
    model = build_model(plan, settings)
    if room not in {sp.id for sp in model.spaces}:
        raise ValueError(f"no room {room!r}")
    groups = {t: [] for t in ROOM_TYPES}
    for sp in model.spaces:
        groups[to if sp.id == room else sp.type].extend(p for p in flat(sp.geom) if isinstance(p, Polygon))
    out = dict(plan)
    for t, parts in groups.items():
        if parts:
            out[t] = MultiPolygon(parts)
        else:
            out.pop(t, None)
    return out


def apply_edits(plan, ops, settings=DEFAULT):
    out = plan
    for op in ops:
        kind = op.get("op") if isinstance(op, dict) else None
        if kind == "remove_door":
            out = _remove_door(out, op.get("door"))
        elif kind == "connect":
            rooms = op.get("rooms") or []
            if len(rooms) != 2 or rooms[0] == rooms[1]:
                raise ValueError("connect needs two different rooms")
            out = _connect(out, rooms[0], rooms[1], settings)
        elif kind == "set_type":
            out = _set_type(out, op.get("room"), op.get("to"), settings)
        else:
            raise ValueError(f"unknown edit {op!r}")
    return dict(out) if out is plan else out
