"""Phase 2 stand-in router: one axis-aligned L per leg.

It ignores walls, so legs can fail V10 to V13. Phase 3 replaces it with the
grid router; the output contract stays.
"""


def l_leg(a, b):
    """Horizontal then vertical polyline from a to b."""
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
    order, here, left = [], start, dict(points)
    while left:
        key = min(left, key=lambda k: abs(left[k][0] - here[0]) + abs(left[k][1] - here[1]))
        order.append(key)
        here = left.pop(key)
    return order
