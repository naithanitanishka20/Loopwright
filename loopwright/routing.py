from __future__ import annotations

import math


def axis_aligned_path(start, end):
    first = _point(start, "start")
    last = _point(end, "end")
    if first == last:
        return (first,)
    if first[0] == last[0] or first[1] == last[1]:
        return (first, last)
    return (first, (last[0], first[1]), last)


def _point(value, name):
    if not isinstance(value, (tuple, list)) or len(value) != 2:
        raise ValueError(f"{name} must contain two finite numbers")
    if any(isinstance(coord, bool) or not isinstance(coord, (int, float)) or not math.isfinite(coord) for coord in value):
        raise ValueError(f"{name} must contain two finite numbers")
    return (float(value[0]), float(value[1]))
