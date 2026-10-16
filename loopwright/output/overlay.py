"""SVG overlay in the organisers' slide 5 style."""
from html import escape

from loopwright.geometry.heal import flat

ZONE_COLOURS = ("#2A78D6", "#EB6834", "#1BAF7A")
INK, PAPER, GREY = "#18202B", "#FFFFFF", "#E6EAE8"


def _path(poly, tx):
    d = []
    for ring in [poly.exterior, *poly.interiors]:
        pts = [tx(x, y) for x, y in ring.coords]
        d.append("M" + " L".join(f"{a:.1f},{b:.1f}" for a, b in pts) + "Z")
    return "".join(d)


def render_svg(model, out, width=900):
    x1, y1, x2, y2 = model.layers["inner"].bounds
    pad = 20
    k = (width - 2 * pad) / max(x2 - x1, 1e-9)
    height = (y2 - y1) * k + 2 * pad + 90

    def tx(x, y):
        return ((x - x1) * k + pad, (y - y1) * k + pad)

    zone_of, colour_of = {}, {}
    by_role = len(out["hubs"]) > len(ZONE_COLOURS)
    for i, hub in enumerate(out["hubs"]):
        if by_role:  # past three zones colour by role; the H labels tell them apart
            living = any(r.startswith("living") for r in hub["zone"])
            colour = ZONE_COLOURS[0] if living else ZONE_COLOURS[1 if len(hub["zone"]) == 1 else 2]
        else:
            colour = ZONE_COLOURS[i]
        colour_of[hub["id"]] = colour
        for r in hub["zone"]:
            zone_of[r] = (hub["id"], colour)

    parts = [f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {width} {height:.0f}" font-family="monospace">',
             f'<rect width="{width}" height="{height:.0f}" fill="{PAPER}"/>']
    for sp in model.spaces:
        fill, opacity = (zone_of[sp.id][1], 0.22) if sp.id in zone_of else (GREY, 1)
        for p in flat(sp.geom):
            if p.geom_type == "Polygon":
                parts.append(f'<path d="{_path(p, tx)}" fill="{fill}" fill-opacity="{opacity}"/>')
    for layer, fill, stroke in (("wall", INK, "none"), ("window", PAPER, "#4B5664"), ("door", PAPER, "none")):
        for p in flat(model.layers.get(layer)):
            if p.geom_type == "Polygon":
                parts.append(f'<path d="{_path(p, tx)}" fill="{fill}" stroke="{stroke}" stroke-width="0.8"/>')

    hubs = {h["id"]: h for h in out["hubs"]}
    for ring in out["rings"]:
        colour = colour_of[ring["hub"]]
        for leg in ring["legs"]:
            pts = " ".join(f"{a:.1f},{b:.1f}" for a, b in (tx(*p) for p in leg["path"]))
            parts.append(f'<polyline points="{pts}" fill="none" stroke="{colour}" stroke-width="2.5" stroke-linejoin="round"/>')
        for leg in ring["legs"]:
            path = leg["path"]
            mx, my = tx(*_midpoint_of_longest(path))
            last = leg["n"] == len(ring["legs"])
            if last:
                parts.append(f'<circle cx="{mx:.1f}" cy="{my:.1f}" r="10" fill="none" stroke="{colour}" stroke-width="1.2"/>')
            parts.append(f'<circle cx="{mx:.1f}" cy="{my:.1f}" r="7" fill="{PAPER}" stroke="{colour}" stroke-width="1.5"/>'
                         f'<text x="{mx:.1f}" y="{my + 3:.1f}" font-size="9" text-anchor="middle" fill="{INK}">{leg["n"]}</text>')
    for node in out["nodes"]:
        x, y = tx(*node["pos"])
        colour = colour_of.get(node["hub"], INK)
        parts.append(f'<circle cx="{x:.1f}" cy="{y:.1f}" r="10" fill="{PAPER}" stroke="{colour}" stroke-width="2.2"/>'
                     f'<text x="{x:.1f}" y="{y + 3:.1f}" font-size="8" text-anchor="middle" fill="{INK}">{escape(node["id"])}</text>')
    for hub in hubs.values():
        x, y = tx(*hub["pos"])
        parts.append(f'<rect x="{x - 7:.1f}" y="{y - 7:.1f}" width="14" height="14" fill="{colour_of[hub["id"]]}"/>'
                     f'<text x="{x + 10:.1f}" y="{y + 4:.1f}" font-size="11" fill="{INK}">{escape(hub["id"])}</text>')

    base = (y2 - y1) * k + 2 * pad + 14
    for i, hub in enumerate(out["hubs"]):
        ring = next(r for r in out["rings"] if r["hub"] == hub["id"])
        text = f'{hub["id"]} · {", ".join(hub["zone"])} · {hub["area_m2"]:.1f} m² | {hub["nodes"]} nodes | {ring["length_m"]:.1f} m, {ring["bends"]} bends'
        parts.append(f'<rect x="{pad}" y="{base + i * 16 - 9:.1f}" width="10" height="10" fill="{colour_of[hub["id"]]}"/>'
                     f'<text x="{pad + 16}" y="{base + i * 16:.1f}" font-size="11" fill="{INK}">{escape(text)}</text>')
    m = out["metrics"]
    summary = f'Hubs {m["hubs"]} (bound {m["hub_lower_bound"]}) · Cable {m["length_m"]:.1f} m · Bends {m["bends"]} · J {m["J"]:.1f} · valid: {out["validation"]["valid"]}'
    parts.append(f'<text x="{pad}" y="{base + len(out["hubs"]) * 16 + 6:.1f}" font-size="11" fill="{INK}">{escape(summary)}</text>')
    parts.append("</svg>")
    return "\n".join(parts)


def _midpoint_of_longest(path):
    best, mid = -1.0, path[0]
    for a, b in zip(path, path[1:]):
        length = abs(b[0] - a[0]) + abs(b[1] - a[1])
        if length > best:
            best, mid = length, ((a[0] + b[0]) / 2, (a[1] + b[1]) / 2)
    return mid
