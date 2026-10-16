"""The product site's generated parts.

`plan_svg` draws a solved plan as line-work on black, with every leg, node and hub
tagged for the page's animation. `site_numbers` reads the headline figures from the
batch records. `build_site` writes them, the drawings and the dark charts into the
site folder as `data.js` and `assets/`, so the page works opened straight from disk.
"""
import json
import pathlib
from html import escape

from loopwright import __version__
from loopwright.batch import p50_p95
from loopwright.charts import extra_hubs_chart, runtime_chart
from loopwright.geometry.heal import flat
from loopwright.results import load_rows, summarize
from loopwright.solve import solve

SPLITS = ("test", "val", "augmented", "train")
RINGS = ("#05F7FF", "#6A7DFF", "#FFFFFF")  # cable on black: the logo's cyan, a periwinkle, white
WALL, WINDOW, INK, BLACK = "#4A5563", "#8B96A3", "#FFFFFF", "#000000"  # walls stay darker than any cable
FONT = "Outfit, system-ui, sans-serif"
FEASIBLE = ("valid", "invalid", "crash")
NODE_R, HUB_HALF, LABEL_SIZE = 7, 8, 14
MARKER_GROWTH = 1.5  # the page scales markers up to about twice on a phone; place labels for the middle of that


def _path(poly, tx):
    d = []
    for ring in [poly.exterior, *poly.interiors]:
        pts = [tx(x, y) for x, y in ring.coords]
        d.append("M" + " L".join(f"{a:.1f},{b:.1f}" for a, b in pts) + "Z")
    return "".join(d)


def _overlaps(box, other):
    return box[0] < other[2] and other[0] < box[2] and box[1] < other[3] and other[1] < box[3]


def label_spot(hub, nodes, legs, text="H1"):
    """Where a hub's label goes: right, left, above or below, whichever keeps off nodes, then off cable.

    Returns (x, y, text-anchor) in drawing coordinates.
    """
    x, y = hub
    g, w = MARKER_GROWTH, (0.62 * LABEL_SIZE * len(text) + 4) * MARKER_GROWTH
    spots = [(x + 13 * g, y + 5 * g, "start"), (x - 13 * g, y + 5 * g, "end"),
             (x, y - 14 * g, "middle"), (x, y + 25 * g, "middle")]
    best = None
    for rank, (lx, ly, anchor) in enumerate(spots):
        left = {"start": lx, "end": lx - w, "middle": lx - w / 2}[anchor]
        box = (left, ly - 11 * g, left + w, ly + 3 * g)
        r = NODE_R * g + 2
        node_hits = sum(_overlaps(box, (nx - r, ny - r, nx + r, ny + r)) for nx, ny in nodes)
        leg_hits = sum(_overlaps(box, (min(a[0], b[0]) - 1, min(a[1], b[1]) - 1, max(a[0], b[0]) + 1, max(a[1], b[1]) + 1))
                       for leg in legs for a, b in zip(leg, leg[1:]))
        score = 100 * node_hits + 10 * leg_hits + rank
        if best is None or score < best[0]:
            best = (score, (lx, ly, anchor))
    lx, ly, anchor = best[1]
    return (x + (lx - x) / g, y + (ly - y) / g, anchor)  # offsets at the drawn size; the page scales the group


def plan_svg(model, out, width=900):
    """The plan as line-work on black; legs, nodes and hubs carry data attributes for the animation.

    Nodes and hubs are drawn about their own centre inside a translated group, so the page
    can scale the `.mark` groups and keep markers readable however small the drawing gets.
    """
    x1, y1, x2, y2 = model.layers["inner"].bounds
    pad = 16
    k = (width - 2 * pad) / max(x2 - x1, 1e-9)
    height = (y2 - y1) * k + 2 * pad

    def tx(x, y):
        return ((x - x1) * k + pad, (y - y1) * k + pad)

    by_role = len(out["hubs"]) > len(RINGS)
    colour = {}
    for i, hub in enumerate(out["hubs"]):
        if by_role:  # past three rings, colour by role and let the hub labels tell them apart
            living = any(r.startswith("living") for r in hub["zone"])
            colour[hub["id"]] = RINGS[0] if living else RINGS[1 if len(hub["zone"]) == 1 else 2]
        else:
            colour[hub["id"]] = RINGS[i]
    zone_of = {r: h["id"] for h in out["hubs"] for r in h["zone"]}
    label = (f"Plan {escape(str(out['plan_id']))}: {len(out['hubs'])} hub{'s' if len(out['hubs']) != 1 else ''} "
             f"and {out['metrics']['length_m']:.1f} m of cable")
    parts = [f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {width} {height:.0f}" class="plan" role="img" '
             f'aria-label="{label}">', '<g class="rooms">']
    for sp in model.spaces:
        hub = zone_of.get(sp.id)
        for p in flat(sp.geom):
            if p.geom_type == "Polygon":
                fill = f'fill="{colour[hub]}" fill-opacity="0.1"' if hub else 'fill="none"'
                zone = f' data-zone="{hub}"' if hub else ""
                parts.append(f'<path class="room" d="{_path(p, tx)}" {fill}{zone}/>')
    parts.append('</g><g class="walls">')
    for p in flat(model.layers.get("wall")):
        if p.geom_type == "Polygon":
            parts.append(f'<path class="wall" d="{_path(p, tx)}" fill="{WALL}"/>')
    parts.append('</g><g class="openings">')
    for layer, attrs in (("window", f'fill="{BLACK}" stroke="{WINDOW}" stroke-width="1"'),
                         ("door", f'fill="{BLACK}"')):
        for p in flat(model.layers.get(layer)):
            if p.geom_type == "Polygon":
                parts.append(f'<path class="{layer}" d="{_path(p, tx)}" {attrs}/>')
    parts.append('</g><g class="rings">')
    drawn_legs = []
    for ring in out["rings"]:
        for leg in ring["legs"]:
            pts = [tx(*p) for p in leg["path"]]
            drawn_legs.append(pts)
            d = "M" + " L".join(f"{a:.1f},{b:.1f}" for a, b in pts)
            parts.append(f'<path class="leg" d="{d}" data-ring="{ring["hub"]}" data-step="{leg["n"]}" fill="none" '
                         f'stroke="{colour[ring["hub"]]}" stroke-width="3" stroke-linecap="round" stroke-linejoin="round"/>')
    parts.append('</g><g class="nodes">')
    for node in out["nodes"]:
        x, y = tx(*node["pos"])
        parts.append(f'<g class="node" data-node="{escape(node["id"])}" data-ring="{node["hub"]}" data-step="{node["order"]}" '
                     f'color="{colour[node["hub"]]}" transform="translate({x:.1f} {y:.1f})"><g class="mark">'
                     f'<circle r="{NODE_R}" fill="currentColor" stroke="{BLACK}" stroke-width="2"/></g></g>')
    parts.append('</g><g class="hubs">')
    centres = {h["id"]: tx(*h["pos"]) for h in out["hubs"]}
    blockers = [tx(*n["pos"]) for n in out["nodes"]]
    for hub in out["hubs"]:
        x, y = centres[hub["id"]]
        others = blockers + [c for h, c in centres.items() if h != hub["id"]]
        lx, ly, anchor = label_spot((x, y), others, drawn_legs, text=hub["id"])
        parts.append(f'<g class="hub" data-hub="{hub["id"]}" color="{colour[hub["id"]]}" transform="translate({x:.1f} {y:.1f})">'
                     f'<g class="mark"><rect x="{-HUB_HALF}" y="{-HUB_HALF}" width="{2 * HUB_HALF}" height="{2 * HUB_HALF}" rx="2" '
                     f'fill="currentColor" stroke="{BLACK}" stroke-width="2"/>'
                     f'<text x="{lx - x:.1f}" y="{ly - y:.1f}" text-anchor="{anchor}" font-family="{FONT}" '
                     f'font-size="{LABEL_SIZE}" font-weight="700" fill="{INK}" stroke="{BLACK}" stroke-width="4" '
                     f'stroke-linejoin="round" paint-order="stroke">{hub["id"]}</text></g></g>')
    parts.append("</g></svg>")
    return "".join(parts)


def _rows(bench_dir):
    rows = []
    for split in SPLITS:
        path = pathlib.Path(bench_dir) / f"{split}-split.jsonl"
        if path.exists():
            rows += load_rows(path)
    return rows


def site_numbers(bench_dir):
    """Headline figures over every split's batch records; timing from the one-process run."""
    rows = _rows(bench_dir)
    s = summarize(rows)
    latency = pathlib.Path(bench_dir) / "latency-test.jsonl"
    timed = load_rows(latency) if latency.exists() else rows
    p50, p95 = p50_p95([r["runtime_s"] for r in timed]) if timed else (0.0, 0.0)
    at_bound = sum(1 for r in rows if r["status"] in FEASIBLE and r["hubs"] == r["hub_lower_bound"])
    return {"plans": s["plans"], "feasible": s["feasible"], "valid": s["valid"], "hubs": s["hubs"],
            "lower_bound": s["lower_bound"], "greedy": s["greedy"], "at_bound": at_bound,
            "length_m": s["length_m"], "J": s["J"], "p50_s": p50, "p95_s": p95}


def build_site(site_dir, drawings, bench_dir):
    """Write site/data.js and site/assets/: drawings is {name: (plan, settings)}."""
    site, assets = pathlib.Path(site_dir), pathlib.Path(site_dir) / "assets"
    assets.mkdir(parents=True, exist_ok=True)
    drawn = {}
    for name, (plan, settings) in drawings.items():
        out, model = solve(plan, settings)
        svg = plan_svg(model, out)
        (assets / f"{name}.svg").write_text(svg, encoding="utf-8")
        m = out["metrics"]
        drawn[name] = {"svg": svg, "plan": out["plan_id"], "hubs": m["hubs"], "lower_bound": m["hub_lower_bound"],
                       "greedy": m["hubs_greedy"], "length_m": m["length_m"], "bends": m["bends"], "crossings": m["crossings"],
                       "overlap_m": m["overlap_m"], "J": m["J"], "valid": out["validation"]["valid"]}
    rows = _rows(bench_dir)
    latency = pathlib.Path(bench_dir) / "latency-test.jsonl"
    times = [r["runtime_s"] for r in (load_rows(latency) if latency.exists() else rows)]
    charts = {"extra_hubs": extra_hubs_chart(rows, theme="dark"), "runtime": runtime_chart(times, theme="dark")}
    (assets / "extra-hubs.svg").write_text(charts["extra_hubs"], encoding="utf-8")
    (assets / "runtime.svg").write_text(charts["runtime"], encoding="utf-8")
    data = {"version": __version__, "numbers": site_numbers(bench_dir), "drawings": drawn, "charts": charts}
    (site / "data.js").write_text("window.LOOPWRIGHT = " + json.dumps(data, ensure_ascii=False) + ";\n", encoding="utf-8")
    return data
