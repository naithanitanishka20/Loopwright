"""Axis-aligned router with exact bend costs.

Grid lines run every `spacing_m` plus through the exact x and y of every stop
(hub or node), so legs start and end on their stops. A vertex is usable when it
lies in the walkable region shrunk by the clearance; an edge when its midpoint
does too. Walls are at least 0.4 m wide once both clearances are added, wider
than any grid edge, so no edge can jump a wall. The search state is
(vertex, heading), so each turn costs bend_m exactly.
"""
import heapq
import itertools

import numpy as np
import shapely
from shapely.ops import unary_union

INF = float("inf")
START = 4


class GridRouter:
    def __init__(self, model, stops, settings, spacing_m=0.2):
        self.s = model.m_per_unit
        layers = model.layers
        blocked = []
        walls, doors = layers.get("wall"), layers.get("door")
        if walls is not None and not walls.is_empty:
            blocked.append(walls.difference(doors) if doors is not None and not doors.is_empty else walls)
        for k in ("window", "balcony", "garden", "pool", "parking"):
            g = layers.get(k)
            if g is not None and not g.is_empty:
                blocked.append(g)
        region = layers["inner"]
        if blocked:
            region = region.difference(unary_union(blocked))
        shrunk = region.buffer(-settings.clearance_m / self.s)
        self.region = shrunk if not shrunk.is_empty else region
        shapely.prepare(self.region)

        x1, y1, x2, y2 = layers["inner"].bounds
        step = spacing_m / self.s
        xs = set(np.round(np.arange(x1, x2 + step, step), 6).tolist())
        ys = set(np.round(np.arange(y1, y2 + step, step), 6).tolist())
        for x, y in stops.values():
            xs.add(round(x, 6))
            ys.add(round(y, 6))
        self.xs, self.ys = sorted(xs), sorted(ys)
        X, Y = np.meshgrid(self.xs, self.ys, indexing="ij")
        ok = shapely.contains_xy(self.region, X, Y)
        xi = {x: i for i, x in enumerate(self.xs)}
        yi = {y: j for j, y in enumerate(self.ys)}
        self.stop_at = {}
        for name, (x, y) in stops.items():
            i, j = xi[round(x, 6)], yi[round(y, 6)]
            ok[i, j] = True
            self.stop_at[name] = (i, j)
        xa, ya = np.array(self.xs), np.array(self.ys)
        mx = (xa[:-1] + xa[1:]) / 2
        my = (ya[:-1] + ya[1:]) / 2
        hmid = shapely.contains_xy(self.region, *np.meshgrid(mx, ya, indexing="ij"))
        vmid = shapely.contains_xy(self.region, *np.meshgrid(xa, my, indexing="ij"))
        self.hok = (ok[:-1, :] & ok[1:, :] & hmid).tolist()
        self.vok = (ok[:, :-1] & ok[:, 1:] & vmid).tolist()
        self.bend = settings.bend_m / self.s
        self.cache = {}

    def _search(self, src):
        if src in self.cache:
            return self.cache[src]
        xs, ys, hok, vok, bend = self.xs, self.ys, self.hok, self.vok, self.bend
        nx, ny = len(xs), len(ys)
        targets = {i * ny + j for name, (i, j) in self.stop_at.items() if name != src}
        dist = [INF] * (nx * ny * 5)
        parent = [-1] * (nx * ny * 5)
        i0, j0 = self.stop_at[src]
        start = (i0 * ny + j0) * 5 + START
        dist[start] = 0.0
        heap = [(0.0, start)]
        while heap and targets:
            d, state = heapq.heappop(heap)
            if d > dist[state]:
                continue
            v, h = divmod(state, 5)
            targets.discard(v)
            i, j = divmod(v, ny)
            moves = []
            if i + 1 < nx and hok[i][j]:
                moves.append((v + ny, 0, xs[i + 1] - xs[i]))
            if i > 0 and hok[i - 1][j]:
                moves.append((v - ny, 1, xs[i] - xs[i - 1]))
            if j + 1 < ny and vok[i][j]:
                moves.append((v + 1, 2, ys[j + 1] - ys[j]))
            if j > 0 and vok[i][j - 1]:
                moves.append((v - 1, 3, ys[j] - ys[j - 1]))
            for nv, nh, step in moves:
                nd = d + step + (bend if h != START and h != nh else 0.0)
                ns = nv * 5 + nh
                if nd < dist[ns]:
                    dist[ns] = nd
                    parent[ns] = state
                    heapq.heappush(heap, (nd, ns))
        self.cache[src] = (dist, parent)
        return self.cache[src]

    def cost(self, a, b):
        """Cheapest length + bends from stop a to stop b, in metres (inf if unreachable)."""
        if a == b:
            return 0.0
        dist, _ = self._search(a)
        i, j = self.stop_at[b]
        v = i * len(self.ys) + j
        return min(dist[v * 5 + h] for h in range(5)) * self.s

    def path(self, a, b):
        """Polyline of the cheapest leg from a to b, or None if unreachable."""
        dist, parent = self._search(a)
        ny = len(self.ys)
        i, j = self.stop_at[b]
        v = i * ny + j
        state = min(range(v * 5, v * 5 + 5), key=lambda st: dist[st])
        if dist[state] == INF:
            return None
        pts = []
        while state != -1:
            vv = state // 5
            pts.append((self.xs[vv // ny], self.ys[vv % ny]))
            state = parent[state]
        pts.reverse()
        return _merge_collinear(pts)

    def vertices_on(self, path):
        """Grid vertices along a path, in order, without its two ends: (x, y, segment, is_corner)."""
        pts = [tuple(p) for p in path]
        out = []
        for seg, (a, b) in enumerate(zip(pts, pts[1:])):
            if a[1] == b[1]:
                lo, hi = sorted((a[0], b[0]))
                inner = [(x, a[1]) for x in self.xs if lo < x < hi]
                reverse = b[0] < a[0]
            else:
                lo, hi = sorted((a[1], b[1]))
                inner = [(a[0], y) for y in self.ys if lo < y < hi]
                reverse = b[1] < a[1]
            out += [(x, y, seg, False) for x, y in (reversed(inner) if reverse else inner)]
            if seg + 1 < len(pts) - 1:
                out.append((b[0], b[1], seg, True))
        return out


def _merge_collinear(pts):
    out = [pts[0]]
    for p in pts[1:]:
        if p == out[-1]:
            continue
        if len(out) >= 2:
            a, b = out[-2], out[-1]
            if (a[0] == b[0] == p[0]) or (a[1] == b[1] == p[1]):
                out[-1] = p
                continue
        out.append(p)
    if len(out) == 1:
        out.append(out[0])
    return [list(p) for p in out]


def best_cycle(router, nodes):
    """Cheapest closed tour through the nodes alone: fix the first, try every order of the rest."""
    first, *rest = sorted(nodes)
    best, best_order = INF, [first, *rest]
    for perm in itertools.permutations(rest):
        seq = (first,) + perm + (first,)
        total = 0.0
        for a, b in zip(seq, seq[1:]):
            total += router.cost(a, b)
            if total >= best:
                break
        if total < best:
            best, best_order = total, [first, *perm]
    return best_order, best


def best_ring_order(router, hub, nodes):
    """Exact visiting order: every permutation of the zone's nodes (5! = 120 at most)."""
    best, best_order = INF, list(nodes)
    for perm in itertools.permutations(sorted(nodes)):
        seq = (hub,) + perm + (hub,)
        total = 0.0
        for a, b in zip(seq, seq[1:]):
            total += router.cost(a, b)
            if total >= best:
                break
        if total < best:
            best, best_order = total, list(perm)
    return best_order, best
