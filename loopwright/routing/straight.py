"""Phase 2 stand-in router: one axis-aligned L per leg.

It ignores walls, so legs can fail V10 to V13. Phase 3 replaces it with the
grid router; the output contract stays.
"""
import math


def _point(value):
    if not isinstance(value, (list, tuple)) or len(value) != 2:
        raise ValueError("point must contain two finite numbers")
    if any(isinstance(coord, bool) or not isinstance(coord, (int, float)) or not math.isfinite(coord) for coord in value):
        raise ValueError("point must contain two finite numbers")
    return value


def l_leg(a, b):
    """Horizontal then vertical polyline from a to b."""
    _point(a)
    _point(b)
    (ax, ay), (bx, by) = a, b
    pts = [(ax, ay)]
    if ax != bx:
        pts.append((bx, ay))
    if ay != by:
        pts.append((bx, by))
    if len(pts) == 1:
        pts.append((bx, by))
    return pts


def nearest_order(start, points):
    """Visit points greedily by Manhattan distance from start (Phase 2 only)."""
    _point(start)
    for point in points.values():
        _point(point)
    order, here, left = [], start, dict(points)
    while left:
        key = min(left, key=lambda k: abs(left[k][0] - here[0]) + abs(left[k][1] - here[1]))
        order.append(key)
        here = left.pop(key)
    return order
