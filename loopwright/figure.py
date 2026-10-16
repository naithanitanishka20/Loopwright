"""The site's scale-model figures: a solved plan built as an isometric model on a baseboard.

Walls stand up from the plan's wall polygons with the door openings cut out and the
windows glazed. Each node is a floor socket, each hub a small switch box, and each ring
a cable laid along the solver's own route. With `live`, every cable piece also carries
where it lies along its ring, in metres, so the page can run a signal round the ring.
"""
import math
from html import escape

from shapely.affinity import affine_transform
from shapely.geometry import MultiPoint, Point, Polygon
from shapely.geometry.polygon import orient
from shapely.ops import unary_union

from loopwright.iso import (Item, box_hit, circle_ring, dots_svg, extrude, fit, line_svg, order, path, quad_hit,
                            rect_ring, rectangles, solid_svg)

RINGS = ("#05F7FF", "#6A7DFF", "#FFFFFF")  # zone and cable colours: the logo's cyan, a periwinkle, white
FLOOR_Z, WALL_H, BASE_T, MARGIN = 0.03, 0.45, 0.3, 0.55
CABLE_R, PIECE_M, JOINT_M, BEND_R = 0.034, 0.35, 0.2, 0.1
PLATE, PLATE_H, PUCK_R, PUCK_H = 0.18, 0.06, 0.12, 0.05
HUB_W, HUB_D, HUB_H = 0.62, 0.42, 0.3
SLIVER_M2 = 0.004
MIN_HIT_PX = 4  # a leg shorter than this on screen can't be seen, so it gets no click target


def _polys(geom):
    return [p for p in getattr(geom, "geoms", [geom]) if p.geom_type == "Polygon" and p.area > SLIVER_M2]


def _ring_path(ring, z, cam):
    return path([cam.iso((x, y, z)) for x, y in list(ring.coords)[:-1]], True)


def _area_path(poly, z, cam):
    return "".join(_ring_path(r, z, cam) for r in [poly.exterior, *poly.interiors])


def room_name(room_id, rooms):
    """'bedroom_2' -> 'bedroom 3' when the plan has several bedrooms; 'living_0' -> 'living room'."""
    kind, _, index = room_id.rpartition("_")
    word = {"living": "living room"}.get(kind, kind)
    if sum(1 for r in rooms if r.rpartition("_")[0] == kind) > 1:
        word += f" {int(index) + 1}"
    return word


def _box_item(svg, x0, y0, z0, x1, y1, z1, cam):
    corners = [(x, y, z) for x in (x0, x1) for y in (y0, y1) for z in (z0, z1)]
    hull = MultiPoint([cam.iso(p) for p in corners]).convex_hull
    return Item(svg, hull, box_hit(x0, y0, z0, x1, y1, z1), cam.depth(((x0 + x1) / 2, (y0 + y1) / 2, (z0 + z1) / 2)))


def _top_matrix(at, z, cam):
    """A transform that lays SVG text flat on a top face, its x along world +x and its y along world +y."""
    o, ex, ey = cam.iso((at[0], at[1], z)), cam.iso((at[0] + 1, at[1], z)), cam.iso((at[0], at[1] + 1, z))
    return (f"matrix({ex[0] - o[0]:.3f} {ex[1] - o[1]:.3f} {ey[0] - o[0]:.3f} {ey[1] - o[1]:.3f} "
            f"{o[0]:.2f} {o[1]:.2f})")


def _base(plate, cam, label):
    """Baseboard: halo, four feet, a bevelled plate with a groove, corner screws, a metre ruler and a label plate."""
    x0, y0, x1, y1 = plate
    ring = rect_ring(x0, y0, x1, y1)
    out = [f'<path class="iso-halo" d="{extrude(ring, -BASE_T - 0.16, BASE_T, cam)["fill"]}"/>']
    feet = sorted([(x0 + 0.55, y0 + 0.55), (x1 - 0.55, y0 + 0.55), (x0 + 0.55, y1 - 0.55), (x1 - 0.55, y1 - 0.55)],
                  key=lambda p: cam.depth((p[0], p[1], 0)))
    for fx, fy in feet:
        out.append(solid_svg(extrude(circle_ring(fx, fy, 0.22, 28), -BASE_T - 0.16, 0.05, cam), tone="lo"))
        out.append(solid_svg(extrude(circle_ring(fx, fy, 0.17, 28), -BASE_T - 0.11, 0.11, cam), tone="mid", crease="none"))
    out.append(solid_svg(extrude(ring, -BASE_T, BASE_T, cam, bevel=0.06), tone="mid"))
    out.append(line_svg(path([cam.iso((x, y, 0)) for x, y in rect_ring(x0 + 0.22, y0 + 0.22, x1 - 0.22, y1 - 0.22)], True), "faint"))
    screws = [(x0 + 0.4, y0 + 0.4), (x1 - 0.4, y0 + 0.4), (x0 + 0.4, y1 - 0.4), (x1 - 0.4, y1 - 0.4)]
    for sx, sy in screws:
        out.append(line_svg(path([cam.iso((x, y, 0)) for x, y in circle_ring(sx, sy, 0.08, 20)], True), "lo"))
    out.append(dots_svg([cam.iso((sx, sy, 0)) for sx, sy in screws], size=0.6))
    # Ruler along the front-left edge, in true metres: a minor tick every 25 cm, a major one every metre
    rx0, rx1, ry1 = x0 + 0.7, x1 - 0.7, y1 - 0.12
    ry0 = ry1 - 0.2
    out.append(solid_svg(extrude(rect_ring(rx0, ry0, rx1, ry1), 0, 0.015, cam), tone="lo", crease="none"))
    minor, major = [], []
    for i in range(int((rx1 - rx0 - 0.1) / 0.25) + 1):
        x = rx0 + 0.05 + i * 0.25
        (major if i % 4 == 0 else minor).append(path([cam.iso((x, ry1, 0.015)), cam.iso((x, ry1 - (0.12 if i % 4 == 0 else 0.06), 0.015))]))
    out.append(line_svg("".join(minor), "lo") + line_svg("".join(major), "mid"))
    # Label plate on the front-right margin: three rule lines for printed text, two screws, one engraved label
    lx0, lx1 = x1 - MARGIN / 2 - 0.2, x1 - MARGIN / 2 + 0.2
    ly0, ly1 = (y0 + y1) / 2 - 0.55, (y0 + y1) / 2 + 0.55
    out.append(solid_svg(extrude(rect_ring(lx0, ly0, lx1, ly1), 0, 0.02, cam), tone="lo"))
    rules = [path([cam.iso((lx0 + 0.09 + i * 0.07, ly0 + 0.18, 0.02)), cam.iso((lx0 + 0.09 + i * 0.07, ly1 - 0.18 - i * 0.2, 0.02))])
             for i in range(3)]
    out.append(line_svg("".join(rules), "lo", free=True))
    out.append(dots_svg([cam.iso(((lx0 + lx1) / 2, ly0 + 0.08, 0.02)), cam.iso(((lx0 + lx1) / 2, ly1 - 0.08, 0.02))], size=0.5))
    out.append(f'<text class="iso-face-text" transform="{_top_matrix((lx1 - 0.05, ly0 + 0.18), 0.02, cam)}" '
               f'font-size="0.13" rotate="0" writing-mode="tb">{escape(label)}</text>')
    return "".join(out)


def _floor(floor, spaces, zone_of, colour, doors, cam):
    out = [solid_svg(extrude(list(orient(p).exterior.coords)[:-1], 0, FLOOR_Z, cam), tone="lo", crease="none")
           for p in _polys(floor)]
    for sp_id, geom in spaces:
        hub = zone_of.get(sp_id)
        zone = f' data-zone="{hub}" style="--ring:{colour[hub]}"' if hub else ""
        for p in _polys(geom):
            out.append(f'<path class="room" data-room="{escape(sp_id)}"{zone} d="{_area_path(p, FLOOR_Z, cam)}"/>')
    for p in _polys(doors):
        out.append(f'<path class="threshold" d="{_area_path(p, FLOOR_Z, cam)}"/>')
    return "".join(out)


def _walls(solid, glass, cam):
    """Upright faces of the walls as sortable items, and the tops (drawn last: no face rises above them)."""
    walls = unary_union([solid, glass])
    glass_ok = glass.buffer(1e-4)
    top_z = FLOOR_Z + WALL_H
    vx, vy = cam.toward()
    lx, ly = -cam.sa, cam.ca
    items, crease, edge = [], [], []
    for poly in _polys(walls):
        poly = orient(poly)
        for ring in [poly.exterior, *poly.interiors]:
            pts = list(ring.coords)[:-1]
            n = len(pts)
            normals, facing = [], []
            for i in range(n):
                (ax, ay), (bx, by) = pts[i], pts[(i + 1) % n]
                length = math.hypot(bx - ax, by - ay) or 1.0
                nx, ny = (by - ay) / length, -(bx - ax) / length
                normals.append((nx, ny))
                facing.append(nx * vx + ny * vy > 1e-9)
            for i in range(n):
                a, b = pts[i], pts[(i + 1) % n]
                top_seg = path([cam.iso((*a, top_z)), cam.iso((*b, top_z))])
                if not facing[i]:
                    edge.append(top_seg)
                    continue
                crease.append(top_seg)
                nx, ny = normals[i]
                shade = min(3, max(0, int((nx * lx + ny * ly + 1) / 2 * 4)))
                length = math.hypot(b[0] - a[0], b[1] - a[1])
                count = max(1, math.ceil(length / 1.0))
                for k in range(count):
                    p = (a[0] + (b[0] - a[0]) * k / count, a[1] + (b[1] - a[1]) * k / count)
                    q = (a[0] + (b[0] - a[0]) * (k + 1) / count, a[1] + (b[1] - a[1]) * (k + 1) / count)
                    mid = Point((p[0] + q[0]) / 2 - nx * 1e-3, (p[1] + q[1]) / 2 - ny * 1e-3)
                    corners = [cam.iso((*p, top_z)), cam.iso((*q, top_z)), cam.iso((*q, FLOOR_Z)), cam.iso((*p, FLOOR_Z))]
                    lines = [path([corners[3], corners[2]])]
                    if k == 0 and not facing[i - 1]:
                        lines.append(path([corners[0], corners[3]]))
                    if k == count - 1 and not facing[(i + 1) % n]:
                        lines.append(path([corners[1], corners[2]]))
                    kind = " glass" if glass_ok.contains(mid) else ""
                    svg = (f'<g class="wall-face{kind}"><path class="iso-shade" data-shade="{shade}" d="{path(corners, True)}"/>'
                           f'{line_svg("".join(lines), "mid", cls="iso-edge")}</g>')
                    hull = Polygon(corners)
                    centre = ((p[0] + q[0]) / 2, (p[1] + q[1]) / 2, FLOOR_Z + WALL_H / 2)
                    items.append(Item(svg, hull, quad_hit(p, q, FLOOR_Z, top_z), cam.depth(centre)))
    tops = [f'<path class="iso-top wall-top" fill-rule="evenodd" d="{"".join(_area_path(p, top_z, cam) for p in _polys(walls))}"/>']
    for r in rectangles(glass):
        x0, y0, x1, y1 = r
        pane = path([cam.iso((x, y, top_z)) for x, y in rect_ring(*r)], True)
        tops.append(f'<path class="iso-top glass-top" d="{pane}"/>' + line_svg(pane, "faint"))  # the frame lines end on it
        if x1 - x0 >= y1 - y0:
            frame = [path([cam.iso((x0, y0 + (y1 - y0) * f, top_z)), cam.iso((x1, y0 + (y1 - y0) * f, top_z))]) for f in (1 / 3, 2 / 3)]
        else:
            frame = [path([cam.iso((x0 + (x1 - x0) * f, y0, top_z)), cam.iso((x0 + (x1 - x0) * f, y1, top_z))]) for f in (1 / 3, 2 / 3)]
        tops.append(line_svg("".join(frame), "lo"))
    tops.append(line_svg("".join(crease), "faint", cls="iso-crease"))
    tops.append(line_svg("".join(edge), "mid", cls="iso-edge"))
    return items, "".join(tops)


def _socket(node, at, ring_s, cam, colour, live):
    x, y = at
    z1, z2 = FLOOR_Z + PLATE_H, FLOOR_Z + PLATE_H + PUCK_H
    plate = extrude(rect_ring(x - PLATE, y - PLATE, x + PLATE, y + PLATE), FLOOR_Z, PLATE_H, cam, bevel=0.012)
    puck = extrude(circle_ring(x, y, PUCK_R, 32), z1, PUCK_H, cam)
    screws = [cam.iso((x + dx * (PLATE - 0.045), y + dy * (PLATE - 0.045), z1)) for dx in (-1, 1) for dy in (-1, 1)]
    face = path([cam.iso((px, py, z2)) for px, py in circle_ring(x, y, PUCK_R * 0.6, 28)], True)
    led = cam.iso((x, y, z2))
    data = f' data-node="{node["id"]}" data-ring="{node["hub"]}"' + (f' data-s="{ring_s:.3f}"' if live else "")
    svg = (f'<g class="socket"{data} style="--ring:{colour}">{solid_svg(plate, tone="mid")}{dots_svg(screws, size=0.45)}'
           f'{solid_svg(puck, tone="hi")}{line_svg(face, "lo")}<circle class="led" cx="{led[0]:.1f}" cy="{led[1]:.1f}" r="2.2"/></g>')
    return _box_item(svg, x - PLATE, y - PLATE, FLOOR_Z, x + PLATE, y + PLATE, z2, cam)


def hub_size(at, walls):
    """The switch box's footprint at its true place: full size if it clears the walls, else turned or smaller."""
    x, y = at
    for scale in (1.0, 0.85, 0.7, 0.55):
        for w, d in ((HUB_W, HUB_D), (HUB_D, HUB_W)):
            w, d = w * scale, d * scale
            if walls.intersection(Polygon(rect_ring(x - w / 2, y - d / 2, x + w / 2, y + d / 2))).area < 1e-4:
                return w, d
    return HUB_D * 0.55, HUB_D * 0.55


def _hub(hub, at, size, cam, colour):
    x, y = at
    (w, d) = size
    x0, x1, y0, y1 = x - w / 2, x + w / 2, y - d / 2, y + d / 2
    top = FLOOR_Z + HUB_H
    body = extrude(rect_ring(x0, y0, x1, y1), FLOOR_Z, HUB_H, cam, bevel=0.015)
    seam = path([cam.iso((x1, y0, top - 0.07)), cam.iso((x1, y1, top - 0.07)), cam.iso((x0, y1, top - 0.07))])
    ports = [cam.iso((x0 + w * f, y1, FLOOR_Z + 0.12)) for f in (0.2, 0.4, 0.6, 0.8)]
    screws = [cam.iso((x0 + 0.06, y0 + 0.06, top)), cam.iso((x1 - 0.06, y1 - 0.06, top))]
    leds = "".join(f'<circle class="port" cx="{px:.1f}" cy="{py:.1f}" r="1.4"/>' for px, py in ports)
    label = (f'<text class="iso-face-text hub-label" transform="{_top_matrix((x - 0.12, y + 0.05), top, cam)}" '
             f'font-size="0.15">{escape(hub["id"])}</text>')
    svg = (f'<g class="hub" data-hub="{hub["id"]}" style="--ring:{colour}">'
           f'{solid_svg(body, tone="hi", inner=line_svg(seam, "faint"))}{dots_svg(screws, size=0.45)}{leds}{label}</g>')
    return _box_item(svg, x0, y0, FLOOR_Z, x1, y1, top, cam)


def _clip(points, box_of_start, box_of_end):
    """Cut a route where it leaves the footprint at its start and enters the one at its end."""
    def cut(pts, rect):
        x0, y0, x1, y1 = rect
        for i in range(len(pts) - 1):
            (ax, ay), (bx, by) = pts[i], pts[i + 1]
            if not (x0 <= bx <= x1 and y0 <= by <= y1):
                lo, hi = 0.0, 1.0
                for _ in range(40):
                    t = (lo + hi) / 2
                    px, py = ax + (bx - ax) * t, ay + (by - ay) * t
                    lo, hi = (t, hi) if x0 <= px <= x1 and y0 <= py <= y1 else (lo, t)
                return [(ax + (bx - ax) * hi, ay + (by - ay) * hi), *pts[i + 1:]]
        return pts[-1:]
    pts = cut(points, box_of_start)
    return cut(pts[::-1], box_of_end)[::-1]


def _rounded(points):
    """The route with each corner turned on a bend of BEND_R (less where a leg is short), as dense points."""
    if len(points) < 3:
        return list(points)
    out = [points[0]]
    for i in range(1, len(points) - 1):
        p0, p, p1 = points[i - 1], points[i], points[i + 1]
        la, lb = math.dist(p0, p), math.dist(p, p1)
        if la < 1e-9 or lb < 1e-9:
            continue
        d0 = ((p[0] - p0[0]) / la, (p[1] - p0[1]) / la)
        d1 = ((p1[0] - p[0]) / lb, (p1[1] - p[1]) / lb)
        if abs(d0[0] * d1[1] - d0[1] * d1[0]) < 1e-6:
            out.append(p)
            continue
        r = min(BEND_R, 0.45 * la, 0.45 * lb)
        c = (p[0] - d0[0] * r + d1[0] * r, p[1] - d0[1] * r + d1[1] * r)
        for k in range(6):
            t = math.pi / 2 * k / 5
            out.append((c[0] + r * (-d1[0] * math.cos(t) + d0[0] * math.sin(t)),
                        c[1] + r * (-d1[1] * math.cos(t) + d0[1] * math.sin(t))))
    out.append(points[-1])
    return out


def _tube(a, b, cam, cls, extra=""):
    """One straight cable piece lying on the floor: paper body, shine and shade bands, two edge lines."""
    z = FLOOR_Z + CABLE_R
    dx, dy = b[0] - a[0], b[1] - a[1]
    length = math.hypot(dx, dy) or 1.0
    u = (-dy / length, dx / length)
    sa, sb = cam.iso((*a, z)), cam.iso((*b, z))
    sl = math.hypot(sb[0] - sa[0], sb[1] - sa[1]) or 1.0
    e = (-(sb[1] - sa[1]) / sl, (sb[0] - sa[0]) / sl)
    section = [cam.iso((a[0] + CABLE_R * math.cos(t) * u[0], a[1] + CABLE_R * math.cos(t) * u[1], z + CABLE_R * math.sin(t)))
               for t in (2 * math.pi * i / 16 for i in range(16))]
    offsets = [(p[0] - sa[0]) * e[0] + (p[1] - sa[1]) * e[1] for p in section]
    up, down = (max(offsets), min(offsets)) if e[1] < 0 else (min(offsets), max(offsets))

    def band(f0, f1, side):
        return path([(sa[0] + e[0] * side * f0, sa[1] + e[1] * side * f0), (sb[0] + e[0] * side * f0, sb[1] + e[1] * side * f0),
                     (sb[0] + e[0] * side * f1, sb[1] + e[1] * side * f1), (sa[0] + e[0] * side * f1, sa[1] + e[1] * side * f1)], True)
    body = band(1.0, 0.0, up) + band(1.0, 0.0, down)
    edges = path([(sa[0] + e[0] * up, sa[1] + e[1] * up), (sb[0] + e[0] * up, sb[1] + e[1] * up)]) + \
        path([(sa[0] + e[0] * down, sa[1] + e[1] * down), (sb[0] + e[0] * down, sb[1] + e[1] * down)])
    return (f'<g class="tb {cls}"{extra}><path class="tb-body" d="{body}"/><path class="tb-shine" d="{band(0.15, 0.6, up)}"/>'
            f'<path class="tb-shade" d="{band(0.3, 0.85, down)}"/>{line_svg(edges, "hi", cls="iso-edge")}'), (sa, sb, e, up, down)


def _cap(at, toward, cam):
    """The round end of a cut cable, as a filled ellipse seen from outside."""
    z = FLOOR_Z + CABLE_R
    length = math.hypot(toward[0], toward[1]) or 1.0
    u = (-toward[1] / length, toward[0] / length)
    pts = [cam.iso((at[0] + CABLE_R * math.cos(t) * u[0], at[1] + CABLE_R * math.cos(t) * u[1], z + CABLE_R * math.sin(t)))
           for t in (2 * math.pi * i / 18 for i in range(18))]
    return f'<path class="cut-end" d="{path(pts, True)}"/>'


def _cable(ring, legs_world, footprints, cam, colour, live):
    """Every cable piece of one ring as sortable items, and the legs' screen paths for hit targets."""
    items, hits, offset = [], [], 0.0
    for leg, pts in legs_world:
        total = sum(math.dist(p, q) for p, q in zip(pts, pts[1:]))
        drawn = _rounded(_clip(pts, footprints[leg["from"]], footprints[leg["to"]]))
        # arc length along the original route for each drawn point: clipping trims the ends, bends shave corners
        lead = math.dist(pts[0], drawn[0]) if drawn else 0.0
        span = sum(math.dist(p, q) for p, q in zip(drawn, drawn[1:]))
        scale = (total - lead - math.dist(pts[-1], drawn[-1])) / span if span else 0.0
        mid = offset + total / 2
        s, cuts = offset + lead, []
        for p, q in zip(drawn, drawn[1:]):
            seg = math.dist(p, q)
            if seg < 1e-6:
                continue
            a_s, b_s = s, s + seg * scale
            marks = sorted({a_s, b_s, *(m for m in (mid - JOINT_M / 2, mid + JOINT_M / 2) if a_s < m < b_s)})
            for m0, m1 in zip(marks, marks[1:]):
                count = max(1, math.ceil((m1 - m0) / (PIECE_M * scale or PIECE_M)))
                for k in range(count):
                    s0, s1 = m0 + (m1 - m0) * k / count, m0 + (m1 - m0) * (k + 1) / count
                    f0, f1 = (s0 - a_s) / (b_s - a_s), (s1 - a_s) / (b_s - a_s)
                    cuts.append(((p[0] + (q[0] - p[0]) * f0, p[1] + (q[1] - p[1]) * f0),
                                 (p[0] + (q[0] - p[0]) * f1, p[1] + (q[1] - p[1]) * f1), s0, s1))
            s = b_s
        for index, (a, b, s0, s1) in enumerate(cuts):
            joint = s0 >= mid - JOINT_M / 2 - 1e-6 and s1 <= mid + JOINT_M / 2 + 1e-6
            data = f' data-ring="{ring["hub"]}" data-leg="{leg["n"]}"'
            if live:
                data += f' data-a="{s0:.3f}" data-b="{s1:.3f}"'
            body, (sa, sb, e, up, _) = _tube(a, b, cam, "cable" + (" joint" if joint else ""), data + f' style="--ring:{colour}"')
            core = ""
            if live:
                lift = (e[0] * up * 0.35, e[1] * up * 0.35)
                d = path([(sa[0] + lift[0], sa[1] + lift[1]), (sb[0] + lift[0], sb[1] + lift[1])])
                core = (f'<path class="glow" pathLength="{s1 - s0:.4f}" d="{d}"/>'
                        f'<path class="core" pathLength="{s1 - s0:.4f}" d="{d}"/>')
            ends = ""
            if joint:
                ends = _cap(a, (a[0] - b[0], a[1] - b[1]), cam) + _cap(b, (b[0] - a[0], b[1] - a[1]), cam)
            dots = []
            if index == 0:
                dots.append(cam.iso((*a, FLOOR_Z + CABLE_R)))
            if index == len(cuts) - 1:
                dots.append(cam.iso((*b, FLOOR_Z + CABLE_R)))
            term = "".join(f'<circle class="iso-wire-end" cx="{x:.1f}" cy="{y:.1f}" r="1.3"/>' for x, y in dots)
            svg = body + core + ends + term + "</g>"
            r = CABLE_R
            items.append(_box_item(svg, min(a[0], b[0]) - r, min(a[1], b[1]) - r, FLOOR_Z,
                                   max(a[0], b[0]) + r, max(a[1], b[1]) + r, FLOOR_Z + 2 * r, cam))
        screen = [cam.iso((x, y, FLOOR_Z + CABLE_R)) for x, y in drawn]
        if sum(math.dist(p, q) for p, q in zip(screen, screen[1:])) >= MIN_HIT_PX:
            hits.append(f'<path class="hit" data-ring="{ring["hub"]}" data-leg="{leg["n"]}" d="{path(screen)}"/>')
        offset += total
    return items, hits


def model_svg(model, out, *, width=1000, height=640, live=False, coloured=False, label=None):
    """The solved plan as an isometric scale model. Returns the SVG and, for `live`, what the page needs
    to run a signal round each ring: its length and where each node sits along it, in metres.
    `coloured` draws each ring's cable in its zone's colour (for figures where the zones are the point)."""
    m = model.m_per_unit
    floor_plan = unary_union([model.layers["inner"], model.layers["wall"]])
    cx, cy = floor_plan.centroid.x, floor_plan.centroid.y

    def to_world(g):
        return affine_transform(g, [m, 0, 0, -m, -m * cx, m * cy])

    def at(p):
        return (m * (p[0] - cx), -m * (p[1] - cy))

    # doors and windows are gaps in the wall layer: doors stay open, windows are glazed
    openings = unary_union([g for k in ("door", "front_door") if (g := model.layers.get(k)) is not None])
    glass = model.layers.get("window") or Polygon()
    solid = model.layers["wall"].difference(glass).difference(openings)
    floor, solid, glass = to_world(floor_plan), to_world(solid), to_world(glass)
    fx0, fy0, fx1, fy1 = floor.bounds
    plate = (fx0 - MARGIN, fy0 - MARGIN, fx1 + MARGIN, fy1 + MARGIN)
    extremes = [(x, y, z) for x in (plate[0], plate[2]) for y in (plate[1], plate[3]) for z in (-BASE_T - 0.16, FLOOR_Z + WALL_H)]
    cam = fit(extremes, width, height, pad=28, elevation=36.0)

    colour = {}
    for i, h in enumerate(out["hubs"]):
        if len(out["hubs"]) > len(RINGS):  # past three rings, colour by role: the living room's zone, one-room zones, the rest
            living = any(r.startswith("living") for r in h["zone"])
            colour[h["id"]] = RINGS[0] if living else RINGS[1 if len(h["zone"]) == 1 else 2]
        else:
            colour[h["id"]] = RINGS[i]
    zone_of = {r: h["id"] for h in out["hubs"] for r in h["zone"]}
    rooms = [n["room"] for n in out["nodes"]]
    footprints, positions, sizes = {}, {}, {}
    for h in out["hubs"]:
        x, y = at(h["pos"])
        w, d = sizes[h["id"]] = hub_size((x, y), solid)
        footprints[h["id"]] = (x - w / 2, y - d / 2, x + w / 2, y + d / 2)
        positions[h["id"]] = (x, y)
    for n in out["nodes"]:
        x, y = at(n["pos"])
        footprints[n["id"]] = (x - PLATE, y - PLATE, x + PLATE, y + PLATE)
        positions[n["id"]] = (x, y)

    items, hits, rings_meta, node_s = [], [], [], {}
    wall_items, tops = _walls(solid, glass, cam)
    items += wall_items
    for ring in out["rings"]:
        legs = [(leg, [at(p) for p in leg["path"]]) for leg in ring["legs"]]
        pieces, leg_hits = _cable(ring, legs, footprints, cam, colour[ring["hub"]], live)
        items += pieces
        hits += leg_hits
        s, stops = 0.0, []
        for leg, pts in legs:
            s += sum(math.dist(p, q) for p, q in zip(pts, pts[1:]))
            if leg["to"] != ring["hub"]:
                node_s[leg["to"]] = s
                room = next(n["room"] for n in out["nodes"] if n["id"] == leg["to"])
                stops.append({"node": leg["to"], "s": round(s, 3), "room": room_name(room, rooms)})
        rings_meta.append({"hub": ring["hub"], "length": round(s, 3), "legs": len(ring["legs"]), "stops": stops})
    for n in out["nodes"]:
        items.append(_socket(n, positions[n["id"]], node_s.get(n["id"], 0.0), cam, colour[n["hub"]], live))
    for h in out["hubs"]:
        items.append(_hub(h, positions[h["id"]], sizes[h["id"]], cam, colour[h["id"]]))

    spaces = [(sp.id, to_world(sp.geom)) for sp in model.spaces]
    doors = to_world(openings.intersection(floor_plan.buffer(0)))
    name = label or (f"Scale model of plan {out['plan_id']}: {len(out['hubs'])} hub{'s' if len(out['hubs']) != 1 else ''} "
                     f"and {out['metrics']['length_m']:.1f} m of cable")
    kind = "iso-svg model" + (" coloured" if coloured else "") + (" live" if live else "")
    parts = [f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {width} {height}" class="{kind}" role="img" '
             f'aria-label="{escape(name)}">',
             f'<g class="base">{_base(plate, cam, str(out["plan_id"]))}</g>',
             f'<g class="floor">{_floor(floor, spaces, zone_of, colour, doors, cam)}</g>',
             f'<g class="scene">{"".join(i.svg for i in order(items, cam))}</g>',
             f'<g class="tops">{tops}</g>']
    if live:
        parts.append(f'<g class="hits">{"".join(hits)}</g>')
    parts.append("</svg>")
    return "".join(parts), {"rings": rings_meta}
