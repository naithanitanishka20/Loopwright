"""Isometric drawing for the product site's figures.

World coordinates are metres with x and y on the floor and z up; the camera looks down
from the +x, +y side. Solids are prisms, a floor outline extruded up, with their visible
sides shaded in four tones by how they face the light (from -x, +y) and a lighter top.
Painter's order is measured, not guessed: wherever two items overlap on screen, rays
through the overlap find which surface is nearer, and the items are sorted to agree.
"""
import heapq
import math
from dataclasses import dataclass
from typing import Callable

from shapely.geometry import MultiPoint, Point
from shapely.prepared import prep

SHADES = 4
_UNIT = math.sqrt(1.6)


class Camera:
    def __init__(self, scale=1.0, origin=(0.0, 0.0), azimuth=45.0, elevation=30.0):
        self.scale, self.origin, self.azimuth, self.elevation = scale, origin, azimuth, elevation
        a, e = math.radians(azimuth), math.radians(elevation)
        self.sa, self.ca, self.se, self.ce = math.sin(a), math.cos(a), math.sin(e), math.cos(e)
        self.k = scale * _UNIT

    def iso(self, p):
        x, y, z = p
        return (self.origin[0] + (x * self.sa - y * self.ca) * self.k,
                self.origin[1] + ((x * self.ca + y * self.sa) * self.se - z * self.ce) * self.k)

    def view(self):
        """Unit vector toward the viewer."""
        return (self.ca * self.ce, self.sa * self.ce, self.se)

    def toward(self):
        """Floor direction toward the viewer: faces whose normal points this way are seen."""
        return (self.ca, self.sa)

    def depth(self, p):
        v = self.view()
        return p[0] * v[0] + p[1] * v[1] + p[2] * v[2]

    def ray(self, sx, sy):
        """The floor point (z = 0) seen at screen point (sx, sy); the ray is that point plus t * view()."""
        u = (sx - self.origin[0]) / self.k
        w = (sy - self.origin[1]) / (self.k * self.se)
        return (u * self.sa + w * self.ca, -u * self.ca + w * self.sa, 0.0)


def fit(points, width, height, pad=24.0, azimuth=45.0, elevation=30.0):
    """A camera that centres and fits these world points in a width x height view."""
    unit = Camera(1.0, (0.0, 0.0), azimuth, elevation)
    flat = [unit.iso(p) for p in points]
    xs, ys = [p[0] for p in flat], [p[1] for p in flat]
    scale = min((width - 2 * pad) / (max(xs) - min(xs)), (height - 2 * pad) / (max(ys) - min(ys)))
    origin = (width / 2 - (min(xs) + max(xs)) / 2 * scale, height / 2 - (min(ys) + max(ys)) / 2 * scale)
    return Camera(scale, origin, azimuth, elevation)


def _num(v):
    text = f"{v:.1f}".rstrip("0").rstrip(".")
    return "0" if text in ("-0", "") else text


def path(points, closed=False):
    if not points:
        return ""
    return "".join(f"{'L' if i else 'M'}{_num(x)} {_num(y)}" for i, (x, y) in enumerate(points)) + ("Z" if closed else "")


def _runs(flags, want):
    """Index runs (as vertex lists) of consecutive edges whose flag equals want, on a closed ring."""
    n = len(flags)
    start = next((i for i in range(n) if flags[i] != flags[i - 1]), None)
    if start is None:
        return [[*(range(n)), 0]] if flags[0] == want else []
    runs, run = [], None
    for step in range(n):
        i = (start + step) % n
        if flags[i] == want:
            run = run or [i]
            run.append((i + 1) % n)
        elif run:
            runs.append(run)
            run = None
    if run:
        runs.append(run)
    return runs


def _wound(points):
    """The same points, wound one way, so overlapping faces of one fill add up instead of cancelling."""
    return points if _area(points) > 0 else points[::-1]


def _area(ring):
    return sum(ax * by - bx * ay for (ax, ay), (bx, by) in zip(ring, ring[1:] + ring[:1])) / 2


def extrude(ring, z, h, cam, bevel=0.0):
    """A floor outline extruded from z to z + h: paper fill, four side shades, top, crease, outline."""
    n = len(ring)
    ccw = _area(ring) > 0
    vx, vy = cam.toward()
    normals = []
    for (ax, ay), (bx, by) in zip(ring, ring[1:] + ring[:1]):
        dx, dy = bx - ax, by - ay
        length = math.hypot(dx, dy) or 1.0
        normals.append((dy / length, -dx / length) if ccw else (-dy / length, dx / length))
    facing = [nx * vx + ny * vy > 1e-9 for nx, ny in normals]
    top = [cam.iso((x, y, z + h)) for x, y in ring]
    bottom = [cam.iso((x, y, z)) for x, y in ring]
    outline = [path([top[i] for i in run]) for run in _runs(facing, False)]
    crease = []
    for run in _runs(facing, True):
        crease.append(path([top[i] for i in run]))
        if h > 0:
            outline.append(path([bottom[i] for i in run]))
    if h > 0:
        outline += [path([top[i], bottom[i]]) for i in range(n) if facing[i - 1] != facing[i]]
    hull = MultiPoint(top + bottom).convex_hull
    if abs(_area(ring)) >= MultiPoint(ring).convex_hull.area - 1e-9:
        fill = path(list(hull.exterior.coords)[:-1], True)
    else:  # concave: the hull would paint over what lies in the notches, so fill with the faces themselves
        faces = [top, bottom] + [[top[i], top[(i + 1) % n], bottom[(i + 1) % n], bottom[i]] for i in range(n) if facing[i]]
        fill = "".join(path(_wound(f), True) for f in faces)
    shades = [[] for _ in range(SHADES)]
    if h > 0:
        lx, ly = -cam.sa, cam.ca
        for i in range(n):
            if facing[i]:
                nx, ny = normals[i]
                shade = min(SHADES - 1, max(0, int((nx * lx + ny * ly + 1) / 2 * SHADES)))
                j = (i + 1) % n
                shades[shade].append(path([top[i], top[j], bottom[j], bottom[i]], True))
    bevel_d = ""
    if bevel > 0:
        inset = []
        for i, (x, y) in enumerate(ring):
            (ax, ay), (bx, by) = normals[i - 1], normals[i]
            mx, my = ax + bx, ay + by
            length = math.hypot(mx, my) or 1.0
            inset.append(cam.iso((x - mx / length * bevel, y - my / length * bevel, z + h)))
        bevel_d = "".join(path([top[run[0]], *[inset[i] for i in run[1:-1]], top[run[-1]]]) for run in _runs(facing, True))
    top_ring = top if ccw else top[::-1]
    return {"fill": fill, "outline": "".join(outline), "crease": "".join(crease), "top": path(top_ring, True),
            "shades": ["".join(s) for s in shades], "bevel": bevel_d}


def rect_ring(x0, y0, x1, y1):
    return [(x0, y0), (x1, y0), (x1, y1), (x0, y1)]


def circle_ring(cx, cy, r, steps=24):
    return [(cx + r * math.cos(2 * math.pi * i / steps), cy + r * math.sin(2 * math.pi * i / steps)) for i in range(steps)]


def solid_svg(paths, tone="hi", crease="faint", lit=False, cls=None, inner="", attrs=""):
    """A solid in paint order: fill, shades, top, crease, bevel, anything inner, then the outline."""
    parts = [f'<path class="iso-fill" d="{paths["fill"]}"/>']
    parts += [f'<path class="iso-shade" data-shade="{i}" d="{d}"/>' for i, d in enumerate(paths["shades"]) if d]
    parts.append(f'<path class="iso-top" d="{paths["top"]}"/>')
    if paths["crease"]:
        parts.append(f'<path class="iso-line iso-crease" data-tone="{crease}" d="{paths["crease"]}"/>')
    if paths.get("bevel"):
        parts.append(f'<path class="iso-line iso-bevel" data-tone="{crease}" d="{paths["bevel"]}"/>')
    parts.append(inner)
    parts.append(f'<path class="iso-line iso-edge" data-tone="{tone}" d="{paths["outline"]}"/>')
    names = "iso-solid" + (f" {cls}" if cls else "")
    return f'<g class="{names}"{" data-lit" if lit else ""}{attrs}>{"".join(parts)}</g>'


def line_svg(d, tone="lo", cls=None, free=None):
    if not d:
        return ""
    names = "iso-line" + (f" {cls}" if cls else "")
    end = "" if free is None else (' data-free=""' if free is True else f' data-free="{free}"')
    return f'<path class="{names}" data-tone="{tone}"{end} d="{d}"/>'


def dots_svg(points, size=0.5, tone="mid"):
    return (f'<g class="iso-dots" data-tone="{tone}">'
            + "".join(f'<circle cx="{_num(x)}" cy="{_num(y)}" r="{size}"/>' for x, y in points) + "</g>")


def box_hit(x0, y0, z0, x1, y1, z1):
    """Ray test for an axis-aligned box: the ray parameter of the first surface seen from the viewer."""
    lo_corner, hi_corner = (x0, y0, z0), (x1, y1, z1)

    def hit(p0, v):
        lo, hi = -math.inf, math.inf
        for a in range(3):
            if abs(v[a]) < 1e-12:
                if not lo_corner[a] <= p0[a] <= hi_corner[a]:
                    return None
                continue
            t1, t2 = (lo_corner[a] - p0[a]) / v[a], (hi_corner[a] - p0[a]) / v[a]
            lo, hi = max(lo, min(t1, t2)), min(hi, max(t1, t2))
        return hi if hi >= lo - 1e-9 else None
    return hit


def quad_hit(a, b, z0, z1):
    """Ray test for an upright rectangle standing on the floor segment a-b between heights z0 and z1."""
    (ax, ay), (bx, by) = a, b
    dx, dy = bx - ax, by - ay
    span = dx * dx + dy * dy

    def hit(p0, v):
        denom = dy * v[0] - dx * v[1]
        if abs(denom) < 1e-12 or span == 0:
            return None
        t = (dy * (ax - p0[0]) - dx * (ay - p0[1])) / denom
        x, y, z = p0[0] + t * v[0], p0[1] + t * v[1], p0[2] + t * v[2]
        s = ((x - ax) * dx + (y - ay) * dy) / span
        return t if -1e-6 <= s <= 1 + 1e-6 and z0 - 1e-6 <= z <= z1 + 1e-6 else None
    return hit


@dataclass
class Item:
    """One drawn piece: its markup, screen footprint, ray test and the depth of its centre (for ties)."""
    svg: str
    hull: object
    hit: Callable
    key: float


def _samples(shape, count):
    """Up to count points spread over a screen region, its representative point first."""
    points = [shape.representative_point()]
    x0, y0, x1, y1 = shape.bounds
    inside = prep(shape)
    steps = max(2, int(math.sqrt(count)) + 1)
    for i in range(1, steps):
        for j in range(1, steps):
            p = Point(x0 + (x1 - x0) * i / steps, y0 + (y1 - y0) * j / steps)
            if inside.contains(p):
                points.append(p)
    return points[:count]


def order(items, cam=None, samples=7, least=0.2):
    """Items sorted back to front. A pair is ordered when their footprints overlap by at least
    `least` square units and rays through the overlap find one surface nearer; the rest keep
    their depth order. A cycle (it would need a split) releases its farthest item first."""
    if cam is None:
        cam = Camera()
    v = cam.view()
    n = len(items)
    bounds = [it.hull.bounds for it in items]
    after, waiting = [[] for _ in range(n)], [0] * n
    for i in range(n):
        for j in range(i + 1, n):
            a, b = bounds[i], bounds[j]
            if a[2] <= b[0] or b[2] <= a[0] or a[3] <= b[1] or b[3] <= a[1]:
                continue
            overlap = items[i].hull.intersection(items[j].hull)
            if overlap.area < least:
                continue
            vote = 0
            for p in _samples(overlap, samples):
                p0 = cam.ray(p.x, p.y)
                ti, tj = items[i].hit(p0, v), items[j].hit(p0, v)
                if ti is not None and tj is not None and abs(ti - tj) > 1e-7:
                    vote += 1 if ti > tj else -1
            if vote:
                back, front = (j, i) if vote > 0 else (i, j)
                after[back].append(front)
                waiting[front] += 1
    ready = [(items[i].key, i) for i in range(n) if not waiting[i]]
    heapq.heapify(ready)
    done, out = [False] * n, []
    while len(out) < n:
        if not ready:
            i = min((i for i in range(n) if not done[i]), key=lambda i: items[i].key)
            ready.append((items[i].key, i))
        _, i = heapq.heappop(ready)
        if done[i]:
            continue
        done[i] = True
        out.append(items[i])
        for j in after[i]:
            waiting[j] -= 1
            if waiting[j] == 0 and not done[j]:
                heapq.heappush(ready, (items[j].key, j))
    return out


def rectangles(shape, digits=6):
    """A rectilinear polygon (or several) as disjoint axis-aligned rectangles (x0, y0, x1, y1)."""
    polys = getattr(shape, "geoms", [shape])
    out = []
    for poly in polys:
        if poly.geom_type != "Polygon" or poly.is_empty:
            continue
        rings = [poly.exterior, *poly.interiors]
        xs = sorted({round(x, digits) for ring in rings for x, _ in ring.coords})
        ys = sorted({round(y, digits) for ring in rings for _, y in ring.coords})
        inside = prep(poly)
        open_spans = {}
        for j in range(len(ys) - 1):
            ym = (ys[j] + ys[j + 1]) / 2
            spans, start = [], None
            for i in range(len(xs) - 1):
                cell = inside.contains(Point((xs[i] + xs[i + 1]) / 2, ym))
                if cell and start is None:
                    start = i
                if not cell and start is not None:
                    spans.append((xs[start], xs[i]))
                    start = None
            if start is not None:
                spans.append((xs[start], xs[-1]))
            for span in list(open_spans):
                if span not in spans:
                    out.append((span[0], open_spans.pop(span), span[1], ys[j]))
            for span in spans:
                open_spans.setdefault(span, ys[j])
        out += [(x0, y0, x1, ys[-1]) for (x0, x1), y0 in open_spans.items()]
    return out
