from __future__ import annotations

import math

from .config import DEFAULT, Settings


def lower_bound_hubs(eligible_area_m2, node_count, settings: Settings = DEFAULT):
    if isinstance(eligible_area_m2, bool) or not isinstance(eligible_area_m2, (int, float)):
        raise ValueError("eligible_area_m2 must be a finite non-negative number")
    if not math.isfinite(eligible_area_m2) or eligible_area_m2 < 0:
        raise ValueError("eligible_area_m2 must be a finite non-negative number")
    if type(node_count) is not int or node_count < 0:
        raise ValueError("node_count must be a non-negative integer")
    return max(
        1,
        math.ceil(eligible_area_m2 / settings.max_area_m2),
        math.ceil(node_count / settings.max_nodes),
    )
