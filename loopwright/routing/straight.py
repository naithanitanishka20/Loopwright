"""Phase 2 axis-aligned stand-in router."""
import math


def _point(value):
    if not isinstance(value, (list, tuple)) or len(value) != 2:
        raise ValueError("point must contain two finite numbers")
    if any(isinstance(coord, bool) or not isinstance(coord, (int, float)) or not math.isfinite(coord) for coord in value):
        raise ValueError("point must contain two finite numbers")
    return value


def l_leg(a, b):
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
    _point(start)
    for point in points.values():
        _point(point)
    order, here, left = [], start, dict(points)
    while left:
        key = min(left, key=lambda k: abs(left[k][0] - here[0]) + abs(left[k][1] - here[1]))
        order.append(key)
        here = left.pop(key)
    return order
