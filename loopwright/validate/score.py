"""Metrics, J and the organisers' slide 5 reviewer checklist."""
from shapely.geometry import LineString
from shapely.ops import unary_union


def _direction(a, b):
    dx, dy = b[0] - a[0], b[1] - a[1]
    if abs(dx) < 1e-9 and abs(dy) < 1e-9:
        return None
    if abs(dx) >= abs(dy):
        return "E" if dx > 0 else "W"
    return "N" if dy > 0 else "S"


def leg_length_and_bends(path):
    length = sum(((b[0] - a[0]) ** 2 + (b[1] - a[1]) ** 2) ** 0.5 for a, b in zip(path, path[1:]))
    dirs = [d for d in (_direction(a, b) for a, b in zip(path, path[1:])) if d]
    bends = sum(1 for d0, d1 in zip(dirs, dirs[1:]) if d0 != d1)
    return length, bends, (dirs[0] if dirs else None), (dirs[-1] if dirs else None)


def ring_metrics(ring, m_per_unit, bend_at_node=True):
    """Length in metres and bends, counting turns at nodes but not at the hub."""
    total, bends, prev_out = 0.0, 0, None
    for i, leg in enumerate(ring["legs"]):
        length, b, first, last = leg_length_and_bends([tuple(p) for p in leg["path"]])
        total += length
        bends += b
        if bend_at_node and i > 0 and prev_out and first and prev_out != first:
            bends += 1
        prev_out = last
    return total * m_per_unit, bends


def interactions(rings, m_per_unit):
    """Crossings (points) and overlap (metres) between different rings."""
    lines = [unary_union([LineString(l["path"]) for l in r["legs"] if len(l["path"]) > 1]) for r in rings]
    crossings, overlap = 0, 0.0
    for i in range(len(lines)):
        for j in range(i + 1, len(lines)):
            inter = lines[i].intersection(lines[j])
            if inter.is_empty:
                continue
            overlap += inter.length * m_per_unit
            parts = getattr(inter, "geoms", [inter])
            crossings += sum(1 for g in parts if g.geom_type == "Point")
    return crossings, overlap


def score(out, settings):
    s = out["frame"]["m_per_unit"]
    length, bends = 0.0, 0
    for ring in out["rings"]:
        l, b = ring_metrics(ring, s, settings.bend_at_node)
        length += l
        bends += b
    crossings, overlap = interactions(out["rings"], s)
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
