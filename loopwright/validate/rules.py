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

    checks.append({"id": "V05", "pass": None, "detail": "zone contiguity needs the door graph (Phase 3)"})

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
    doors = unary_union([g for g in (layers["door"],) if g is not None and not g.is_empty]) if layers["door"] is not None else None
    walls = layers["wall"]
    if walls is not None and doors is not None and not doors.is_empty:
        walls = walls.difference(doors.buffer(EPS_LEN * 10))
    windows = layers["window"]
    allowed = _valid(plan.get("inner"))
    for k in ("balcony", "garden", "pool", "parking"):
        if layers[k] is not None and not layers[k].is_empty:
            allowed = allowed.difference(layers[k])
    allowed = allowed.buffer(EPS_LEN * 10)
    v10, v11, v12, v14 = [], [], [], []
    for ring in out["rings"]:
        for leg in ring["legs"]:
            path = [tuple(p) for p in leg["path"]]
            where = f"{ring['hub']} leg {leg['n']}"
            for (x0, y0), (x1, y1) in zip(path, path[1:]):
                if abs(x1 - x0) > EPS_LEN and abs(y1 - y0) > EPS_LEN:
                    v14.append(where)
                    break
            line = LineString(path) if len(path) > 1 else None
            if line is None or line.length == 0:
                continue
            if walls is not None and not walls.is_empty and line.intersection(walls).length > 1e-6:
                v10.append(where)
            if windows is not None and not windows.is_empty and line.intersection(windows).length > 1e-6:
                v11.append(where)
            if not allowed.covers(line):
                v12.append(where)
    _check(checks, "V10", not v10, f"legs crossing walls: {v10}")
    _check(checks, "V11", not v11, f"legs touching windows: {v11}")
    _check(checks, "V12", not v12, f"legs leaving the building or entering external areas: {v12}")
    checks.append({"id": "V13", "pass": None, "detail": "space changes at portals need the door graph (Phase 3)"})
    _check(checks, "V14", not v14, f"legs with a diagonal segment: {v14}")

    valid = all(c["pass"] is not False for c in checks)
    return {"valid": valid, "checks": checks}


def _close(p, q, tol=1e-3):
    return math.hypot(p[0] - q[0], p[1] - q[1]) <= tol
