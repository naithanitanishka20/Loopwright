"""Lower bound, feasible zones and the exact minimum hub count.

Rooms are indexed 0..n-1 and zones are bitmasks over them (n <= 9 on ResPlan,
so at most 511 zones).
"""
import math

from loopwright.config import DEFAULT

INF = 10 ** 9


def ceil_div(x, d):
    return math.ceil(round(x / d, 9))


def lower_bound(total_area_m2, n, settings=DEFAULT):
    """max(ceil(area / cap), ceil(n / node cap)); 0 when there are no rooms."""
    if isinstance(total_area_m2, bool) or not isinstance(total_area_m2, (int, float)) \
            or not math.isfinite(total_area_m2) or total_area_m2 < 0:
        raise ValueError("total_area_m2 must be a finite non-negative number")
    if type(n) is not int or n < 0:
        raise ValueError("n must be a non-negative integer")
    if n == 0:
        return 0
    return max(ceil_div(total_area_m2, settings.max_area_m2), ceil_div(n, settings.max_nodes), 1)


def feasible_zones(areas, settings=DEFAULT, connected=None, relax_singletons=True):
    """feasible[mask] for every subset of rooms.

    connected(mask) -> bool checks the zone rule; None means not checked yet.
    relax_singletons keeps a single over-cap room as its own zone, so the plan
    still gets a (flagged) design instead of no answer (assumptions Q11).
    """
    n = len(areas)
    size = 1 << n
    area = [0.0] * size
    count = [0] * size
    feasible = [False] * size
    for mask in range(1, size):
        low = (mask & -mask).bit_length() - 1
        rest = mask & (mask - 1)
        area[mask] = area[rest] + areas[low]
        count[mask] = count[rest] + 1
        ok = count[mask] <= settings.max_nodes and area[mask] <= settings.max_area_m2 + 1e-9
        if ok and connected is not None and count[mask] > 1:
            ok = connected(mask)
        if not ok and relax_singletons and count[mask] == 1:
            ok = True
        feasible[mask] = ok
    return feasible


def min_hubs(n, feasible):
    """Exact minimum number of zones covering all rooms, and one optimal partition."""
    if n == 0:
        return 0, []
    size = 1 << n
    best = [INF] * size
    choice = [0] * size
    best[0] = 0
    for mask in range(1, size):
        low = mask & -mask
        rest = mask ^ low
        sub = rest
        while True:
            zone = sub | low
            if feasible[zone] and best[mask ^ zone] + 1 < best[mask]:
                best[mask] = best[mask ^ zone] + 1
                choice[mask] = zone
            if sub == 0:
                break
            sub = (sub - 1) & rest
    full = size - 1
    if best[full] >= INF:
        return INF, []
    zones, mask = [], full
    while mask:
        zones.append(choice[mask])
        mask ^= choice[mask]
    return best[full], zones


def members(mask, n):
    return [k for k in range(n) if mask >> k & 1]
