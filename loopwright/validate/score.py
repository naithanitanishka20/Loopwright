"""Metrics, J and the organisers' slide 5 reviewer checklist.

The metrics follow the organisers' slide 7: cable length includes every leg and
counts a retraced stretch each time it is run; a bend is any change of direction,
at a vertex, a node or the hub, a reversal counting once; a crossing is a point
where two cables meet away from a node or hub, inside one ring or between rings,
once per point; overlap is the length a stretch of line is covered more than once,
k legs counting (k - 1) times. Points within 1 mm are one point and lines within
1 mm one line.
"""
import math

from shapely.geometry import LineString

TOLERANCE_M = 0.001


def _direction(a, b, tol=1e-9):
    dx, dy = b[0] - a[0], b[1] - a[1]
    if abs(dx) <= tol and abs(dy) <= tol:
        return None
    if abs(dx) >= abs(dy):
        return "E" if dx > 0 else "W"
    return "N" if dy > 0 else "S"


def leg_length_and_bends(path, tol=1e-9):
    """Length (plan units), bends inside the leg, and its first and last directions."""
    length = sum(((b[0] - a[0]) ** 2 + (b[1] - a[1]) ** 2) ** 0.5 for a, b in zip(path, path[1:]))
    dirs = [d for d in (_direction(a, b, tol) for a, b in zip(path, path[1:])) if d]
    bends = sum(1 for d0, d1 in zip(dirs, dirs[1:]) if d0 != d1)
    return length, bends, (dirs[0] if dirs else None), (dirs[-1] if dirs else None)


def ring_metrics(ring, m_per_unit, bend_at_node=True, tolerance_m=TOLERANCE_M):
    """Length in metres and bends: turns inside legs, at every node and at the hub."""
    tol = tolerance_m / m_per_unit
    total, bends, ends = 0.0, 0, []
    for leg in ring["legs"]:
        length, b, first, last = leg_length_and_bends([tuple(p) for p in leg["path"]], tol)
        total += length
        bends += b
        ends.append((first, last))
    for i, (_, last) in enumerate(ends):
        at_hub = i == len(ends) - 1
        first = ends[(i + 1) % len(ends)][0]  # the next leg's start; the first leg's at the hub
        if last and first and last != first and (at_hub or bend_at_node):
            bends += 1
    return total * m_per_unit, bends


def interactions(rings, m_per_unit, tolerance_m=TOLERANCE_M, self_crossings=True):
    """Crossings (points) and overlap (metres) over every leg of every ring."""
    tol = tolerance_m / m_per_unit
    legs = [(k, [tuple(p) for p in leg["path"]]) for k, r in enumerate(rings) for leg in r["legs"] if len(leg["path"]) > 1]
    stops = [p for _, path in legs for p in (path[0], path[-1])]
    return _crossings(legs, stops, tol, self_crossings), _overlap([path for _, path in legs], tol) * m_per_unit


def _near(p, points, tol):
    return any(abs(p[0] - q[0]) <= tol and abs(p[1] - q[1]) <= tol for q in points)


def _crossings(legs, stops, tol, self_crossings):
    """Distinct points where two legs meet away from every node and hub."""
    lines = [(k, LineString(path)) for k, path in legs]
    found = []
    for i, (ki, a) in enumerate(lines):
        for kj, b in lines[i + 1:]:
            if ki == kj and not self_crossings:
                continue
            inter = a.intersection(b)
            for g in getattr(inter, "geoms", [inter]):
                if g.geom_type == "Point":
                    p = (g.x, g.y)
                    if not _near(p, stops, tol) and not _near(p, found, tol):
                        found.append(p)
    return len(found)


def _overlap(paths, tol):
    """Plan-unit length covered by more than one leg, each stretch counted (k - 1) times."""
    rows = {"h": [], "v": []}
    for path in paths:
        for a, b in zip(path, path[1:]):
            if abs(a[1] - b[1]) <= tol < abs(a[0] - b[0]):
                rows["h"].append(((a[1] + b[1]) / 2, min(a[0], b[0]), max(a[0], b[0])))
            elif abs(a[0] - b[0]) <= tol < abs(a[1] - b[1]):
                rows["v"].append(((a[0] + b[0]) / 2, min(a[1], b[1]), max(a[1], b[1])))
    total = 0.0
    for segs in rows.values():
        segs.sort()
        line = []
        for seg in segs + [(math.inf, 0.0, 0.0)]:
            if line and seg[0] - line[-1][0] > tol:  # the next segment lies on another line
                total += _covered_more_than_once(line, tol)
                line = []
            line.append(seg)
    return total


def _covered_more_than_once(line, tol):
    events = sorted([(lo, 1) for _, lo, _ in line] + [(hi, -1) for _, _, hi in line])
    total, depth, prev = 0.0, 0, None
    for x, step in events:
        if prev is not None and depth > 1 and x - prev > tol:
            total += (depth - 1) * (x - prev)
        depth += step
        prev = x
    return total


def score(out, settings):
    s = out["frame"]["m_per_unit"]
    length, bends = 0.0, 0
    for ring in out["rings"]:
        l, b = ring_metrics(ring, s, settings.bend_at_node, settings.tolerance_m)
        length += l
        bends += b
    crossings, overlap = interactions(out["rings"], s, settings.tolerance_m, settings.count_self_crossings)
    J = length + settings.bend_m * bends + settings.crossing_m * crossings + settings.overlap_factor * overlap
    return {"length_m": round(length, 1), "bends": bends, "crossings": crossings,
            "overlap_m": round(overlap, 1), "J": round(J, 1)}


def reviewer_lines(out, validation, lb, total_area, n_nodes):
    checks = {c["id"]: c["pass"] for c in validation["checks"]}

    def tick(text, ids):
        state = [checks.get(i) for i in ids]
        mark = "✓" if all(v is True for v in state) else ("?" if any(v is None for v in state) and not any(v is False for v in state) else "✗")
        return f"{mark} {text}"

    k = len(out["hubs"])
    hub_line = (f"{k} hubs = lower bound ({total_area:.0f} m², {n_nodes} nodes)" if k == lb
                else f"{k} hubs; lower bound {lb} ({total_area:.0f} m², {n_nodes} nodes)")
    return [
        tick("Each node once; ring ends at its own hub", ["V02", "V07", "V08"]),
        tick("≤ 100 m² and ≤ 5 nodes per hub", ["V03", "V04"]),
        tick("Each zone connected through doors only", ["V05"]),
        tick("Axis-aligned; no wall or window crossed", ["V10", "V11", "V14"]),
        ("✓ " if k == lb else "• ") + hub_line,
    ]
