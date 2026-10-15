"""Rules V00-V14 checked against the raw plan. V05 and V13 need the door graph
and are reported as not checked until Phase 3.
"""
import math

import shapely
from shapely.geometry import LineString, Point, Polygon
from shapely.ops import unary_union

EPS_LEN = 1e-6
ELIGIBLE = ("living", "kitchen", "bedroom", "storage")
REQUIRED_TOP = ("schema", "plan_id", "frame", "rules", "weights", "rooms", "hubs", "nodes", "rings", "metrics", "ranking_key")


def _flat(g):
    if g is None or g.is_empty:
        return []
    if hasattr(g, "geoms"):
        return [q for part in g.geoms for q in _flat(part)]
    return [g]


def _valid(g):
    if g is None:
        return None
    try:
        return shapely.make_valid(g)
    except Exception:
        return g.buffer(0)


def _polys(g, min_area=0.0):
    return [p for p in _flat(_valid(g)) if isinstance(p, Polygon) and p.area >= min_area]


def rebuild_rooms(plan, m_per_unit, living_pieces="merge", sliver_m2=0.5):
    """Room id -> polygon, using the documented id convention."""
    sliver = sliver_m2 / (m_per_unit * m_per_unit)
    rooms = {}
    living = _polys(plan.get("living"), sliver)
    if living and living_pieces == "merge":
        rooms["living_0"] = unary_union(living)
    else:
        for i, p in enumerate(living):
            rooms[f"living_{i}"] = p
    for t in ("kitchen", "bedroom", "storage", "bathroom", "stair"):
        for i, p in enumerate(_polys(plan.get(t), sliver)):
            rooms[f"{t}_{i}"] = p
    return rooms


def _check(results, rule, ok, detail="", where=None):
    entry = {"id": rule, "pass": bool(ok)}
    if detail:
        entry["detail"] = detail
    if where:
        entry["where"] = where
    results.append(entry)
    return ok


def validate(plan, out, settings):
    """Return {"valid": bool, "checks": [...]} for output `out` on raw `plan`."""
    checks = []
    missing = [k for k in REQUIRED_TOP if k not in out]
    _check(checks, "V00", not missing, f"missing keys: {missing}" if missing else "")
    if missing:
        return {"valid": False, "checks": checks}

    s = float(out["frame"]["m_per_unit"])
    rooms = rebuild_rooms(plan, s, settings.living_pieces, settings.sliver_m2)
    eligible = {rid for rid in rooms if rid.split("_")[0] in ELIGIBLE}
    hubs = {h["id"]: h for h in out["hubs"]}
    nodes = {n["id"]: n for n in out["nodes"]}

    # V01: one node per eligible room, inside it
    per_room = {}
    for n in out["nodes"]:
        per_room.setdefault(n["room"], []).append(n)
    bad = [r for r in eligible if len(per_room.get(r, [])) != 1]
    outside = [n["id"] for n in out["nodes"] if n["room"] not in rooms or not rooms[n["room"]].buffer(EPS_LEN).covers(Point(n["pos"]))]
    extra = [r for r in per_room if r not in eligible]
    _check(checks, "V01", not bad and not outside and not extra,
           f"rooms without exactly one node: {bad}; nodes outside their room: {outside}; nodes in non-eligible rooms: {extra}")

    # V02: each node belongs to exactly one hub and appears in exactly one ring
    seen = {}
    for ring in out["rings"]:
        for stop in ring["sequence"][1:-1]:
            seen[stop] = seen.get(stop, 0) + 1
    orphan = [nid for nid, n in nodes.items() if n["hub"] not in hubs or seen.get(nid, 0) != 1]
    _check(checks, "V02", not orphan, f"nodes not in exactly one ring: {orphan}")

    # V03, V04: caps per zone
    over_area, over_nodes = [], []
    for h in out["hubs"]:
        area = sum(rooms[r].area for r in h["zone"] if r in rooms) * s * s
        if area > settings.max_area_m2 + 1e-6:
            over_area.append(f"{h['id']} {area:.1f} m²")
        if len(h["zone"]) > settings.max_nodes:
            over_nodes.append(f"{h['id']} {len(h['zone'])} nodes")
    _check(checks, "V03", not over_area, "; ".join(over_area))
    _check(checks, "V04", not over_nodes, "; ".join(over_nodes))

    # V05: zone connected under the declared rule, on the validator's own link test
    zone_link = out["rules"].get("zone_link", "strict")
    if zone_link == "none":
        checks.append({"id": "V05", "pass": None, "detail": "output declares no zone rule"})
    else:
        wd = float(plan.get("wall_depth") or 0) or 0.2 / s
        walls_raw, doors_raw = _valid(plan.get("wall")), _valid(plan.get("door"))
        barrier = walls_raw
        if barrier is not None and doors_raw is not None and not doors_raw.is_empty:
            barrier = barrier.difference(doors_raw)
        windows_raw = _valid(plan.get("window"))
        if windows_raw is not None and not windows_raw.is_empty:
            barrier = windows_raw if barrier is None else unary_union([barrier, windows_raw])
        if zone_link == "strict":
            connectors = set()
        elif zone_link == "circulation":
            connectors = {r for r in rooms if r.split("_")[0] in ("bathroom", "stair")}
        else:
            connectors = set(rooms)
        door_parts = [d for d in _flat(doors_raw) if not d.is_empty] if doors_raw is not None else []
        disconnected = []
        for h in out["hubs"]:
            zone = [r for r in h["zone"] if r in rooms]
            if len(zone) > 1 and not _zone_connected(zone, connectors, rooms, barrier, wd, door_parts):
                disconnected.append(h["id"])
        _check(checks, "V05", not disconnected, f"zones not connected under '{zone_link}': {disconnected}")

    # V06: hub inside an eligible room of its own zone
    bad_hubs = []
    for h in out["hubs"]:
        zone_geom = unary_union([rooms[r] for r in h["zone"] if r in rooms and r in eligible])
        if zone_geom.is_empty or not zone_geom.buffer(EPS_LEN).covers(Point(h["pos"])):
            bad_hubs.append(h["id"])
    _check(checks, "V06", not bad_hubs, f"hubs outside their zone: {bad_hubs}")

    # V07, V08, V09: ring structure
    v07, v08, v09 = [], [], []
    stops = {**{k: tuple(v["pos"]) for k, v in hubs.items()}, **{k: tuple(v["pos"]) for k, v in nodes.items()}}
    for ring in out["rings"]:
        seq = ring["sequence"]
        if len(seq) < 2 or seq[0] != ring["hub"] or seq[-1] != ring["hub"]:
            v07.append(ring["hub"])
        mine = sorted(nid for nid, n in nodes.items() if n["hub"] == ring["hub"])
        if sorted(seq[1:-1]) != mine or len(set(seq[1:-1])) != len(seq) - 2:
            v08.append(ring["hub"])
        legs = ring["legs"]
        if len(legs) != len(seq) - 1:
            v09.append(f"{ring['hub']}: {len(legs)} legs for {len(seq)} stops")
            continue
        for i, leg in enumerate(legs):
            path = [tuple(p) for p in leg["path"]]
            a, b = stops.get(seq[i]), stops.get(seq[i + 1])
            if a is None or b is None or not _close(path[0], a) or not _close(path[-1], b):
                v09.append(f"{ring['hub']} leg {i + 1} does not join {seq[i]} to {seq[i + 1]}")
    _check(checks, "V07", not v07, f"rings not closed at their own hub: {v07}")
    _check(checks, "V08", not v08, f"rings with skipped, repeated or foreign nodes: {v08}")
    _check(checks, "V09", not v09, "; ".join(v09))

    # Geometry rules on every leg
    layers = {k: _valid(plan.get(k)) for k in ("wall", "door", "window", "balcony", "garden", "pool", "parking", "front_door")}
    doors = layers["door"]
    walls = layers["wall"]
    if walls is not None and doors is not None and not doors.is_empty:
        walls = walls.difference(doors.buffer(EPS_LEN * 10))
    windows = layers["window"]
    building = _building(plan, rooms, s)
    allowed = building
    for k in ("balcony", "garden", "pool", "parking"):
        if layers[k] is not None and not layers[k].is_empty:
            allowed = allowed.difference(layers[k])
    allowed = allowed.buffer(EPS_LEN * 10)
    wd = float(plan.get("wall_depth") or 0) or 0.2 / s
    portal_zone, label = _portals(rooms, building, walls, windows, doors, wd, s)
    found = {"V10": [], "V11": [], "V12": [], "V13": [], "V14": []}
    for ring in out["rings"]:
        for leg in ring["legs"]:
            path = [tuple(p) for p in leg["path"]]
            where = {"ring": ring["hub"], "leg": leg["n"]}
            if any(abs(x1 - x0) > EPS_LEN and abs(y1 - y0) > EPS_LEN for (x0, y0), (x1, y1) in zip(path, path[1:])):
                found["V14"].append(where)
            line = LineString(path) if len(path) > 1 else None
            if line is None or line.length == 0:
                continue
            if walls is not None and not walls.is_empty and line.intersection(walls).length > 1e-6:
                found["V10"].append(where)
            if windows is not None and not windows.is_empty and line.intersection(windows).length > 1e-6:
                found["V11"].append(where)
            if not allowed.covers(line):
                found["V12"].append(where)
            off = _space_changes_off_portal(line, label, portal_zone, s)
            if off:
                found["V13"].append({**where, "at": off[:3]})
    texts = {"V10": "legs crossing walls", "V11": "legs touching windows",
             "V12": "legs leaving the building or entering external areas",
             "V13": "legs changing space away from any door or open passage", "V14": "legs with a diagonal segment"}
    for rule in ("V10", "V11", "V12", "V13", "V14"):
        hits = found[rule]
        detail = f"{texts[rule]}: " + ", ".join(f"{w['ring']} leg {w['leg']}" for w in hits) if hits else ""
        _check(checks, rule, not hits, detail, hits or None)

    valid = all(c["pass"] is not False for c in checks)
    return {"valid": valid, "checks": checks}


def _portals(rooms, building, walls, windows, doors, wd, s):
    """Where a cable may change space (doors, and open passages at least two wall
    depths long), plus a function that names the space a point is in."""
    spaces = dict(rooms)
    rest = building.difference(unary_union(list(rooms.values()))) if rooms else building
    for g in (walls, windows, doors):
        if g is not None and not g.is_empty:
            rest = rest.difference(g)
    rest = rest.buffer(-0.25 * wd).buffer(0.25 * wd)
    if rest.area * s * s > 1.0:
        spaces["circulation"] = rest
    barriers = [g for g in (walls, windows) if g is not None and not g.is_empty]
    barrier = unary_union(barriers) if barriers else None
    tol = 0.6 * wd
    parts = [doors.buffer(tol)] if doors is not None and not doors.is_empty else []
    names = list(spaces)
    grown = {k: spaces[k].buffer(0.55 * wd) for k in names}
    for i, a in enumerate(names):
        for b in names[i + 1:]:
            if not grown[a].intersects(grown[b]):
                continue
            gap = grown[a].intersection(grown[b])
            if barrier is not None:
                gap = gap.difference(barrier)
            for piece in _flat(gap):
                x0, y0, x1, y1 = piece.bounds
                if max(x1 - x0, y1 - y0) >= 2 * wd:
                    parts.append(piece.buffer(tol))
    portal = unary_union(parts) if parts else None
    items = list(spaces.items())
    tree = shapely.STRtree([g for _, g in items])

    def label(pt):
        hits = tree.query(pt, predicate="intersects")
        return items[int(hits[0])][0] if len(hits) else None

    return portal, label


def _space_changes_off_portal(line, label, portal, s, step_m=0.05):
    """Points where the line moves from one space into another outside every portal."""
    n = max(2, int(line.length * s / step_m) + 1)
    prev_label, prev_pt, bad = None, None, []
    for k in range(n + 1):
        pt = line.interpolate(k / n, normalized=True)
        lab = label(pt)
        if lab is None:
            continue  # inside a wall band or doorway; judged where the next space starts
        if prev_label is not None and lab != prev_label:
            mid = Point((pt.x + prev_pt.x) / 2, (pt.y + prev_pt.y) / 2)
            if portal is None or not portal.covers(mid):
                bad.append([round(mid.x, 2), round(mid.y, 2)])
        prev_label, prev_pt = lab, pt
    return bad


def _building(plan, rooms, s):
    """The building outline: `inner`, widened to cover every room and door when the
    data's outline leaves parts of rooms out (assumptions Q16)."""
    inner = _valid(plan.get("inner"))
    if not rooms:
        return inner
    room_union = unary_union(list(rooms.values()))
    if room_union.difference(inner).area * s * s <= 0.5:
        return inner
    wd = float(plan.get("wall_depth") or 0) or 0.2 / s
    doors = _valid(plan.get("door"))
    cover = [room_union] + ([doors] if doors is not None and not doors.is_empty else [])
    return unary_union([inner, unary_union(cover).buffer(0.5 * wd)])


def _linked(a, b, barrier, wd, doors=()):
    """Rooms a and b share a passage: a door polygon reaches both, or their grown
    outlines overlap somewhere no wall or window covers (an open passage)."""
    ga, gb = a.buffer(wd * 0.6), b.buffer(wd * 0.6)
    for d in doors:
        if d.intersects(ga) and d.intersects(gb):
            return True
    gap = ga.intersection(gb)
    if gap.is_empty:
        return False
    if barrier is not None and not barrier.is_empty:
        gap = gap.difference(barrier)
    return gap.area > 0.2 * wd * wd


def _zone_connected(zone, connectors, rooms, barrier, wd, doors=()):
    allowed = set(zone) | set(connectors)
    seen, stack = {zone[0]}, [zone[0]]
    while stack:
        u = stack.pop()
        for v in allowed - seen:
            if _linked(rooms[u], rooms[v], barrier, wd, doors):
                seen.add(v)
                stack.append(v)
    return all(r in seen for r in zone)


def _close(p, q, tol=1e-3):
    return math.hypot(p[0] - q[0], p[1] - q[1]) <= tol
