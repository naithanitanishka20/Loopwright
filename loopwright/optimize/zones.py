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
    try:
        areas = list(areas)
    except TypeError as exc:
        raise ValueError("areas must be a sequence of finite non-negative numbers") from exc
    if any(isinstance(area, bool) or not isinstance(area, (int, float)) or not math.isfinite(area) or area < 0 for area in areas):
        raise ValueError("areas must be a sequence of finite non-negative numbers")
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


def min_hubs_cheapest(n, feasible, cost):
    """The exact minimum number of zones and, among the partitions that reach it, one with the
    lowest total cost(zone). cost is called only for zones that can be part of such a partition,
    and not at all when a single partition reaches the minimum."""
    count, zones = min_hubs(n, feasible)
    if count >= INF or count <= 1:
        return count, zones
    size = 1 << n
    best, ways = [INF] * size, [0] * size  # fewest zones covering each mask, and in how many ways (capped at 2)
    best[0], ways[0] = 0, 1
    for mask in range(1, size):
        low = mask & -mask
        rest = mask ^ low
        sub = rest
        while True:
            zone = sub | low
            if feasible[zone] and best[mask ^ zone] < INF:
                c = best[mask ^ zone] + 1
                if c < best[mask]:
                    best[mask], ways[mask] = c, ways[mask ^ zone]
                elif c == best[mask]:
                    ways[mask] = min(2, ways[mask] + ways[mask ^ zone])
            if sub == 0:
                break
            sub = (sub - 1) & rest
    if ways[size - 1] < 2:
        return count, zones
    total, choice, zone_cost = [math.inf] * size, [0] * size, {}
    total[0] = 0.0
    for mask in range(1, size):
        if best[mask] >= INF:
            continue
        low = mask & -mask
        rest = mask ^ low
        sub = rest
        while True:
            zone = sub | low
            prev = mask ^ zone
            if feasible[zone] and best[prev] + 1 == best[mask] and total[prev] < math.inf:
                if zone not in zone_cost:
                    zone_cost[zone] = cost(zone)
                if total[prev] + zone_cost[zone] < total[mask]:
                    total[mask], choice[mask] = total[prev] + zone_cost[zone], zone
            if sub == 0:
                break
            sub = (sub - 1) & rest
    zones, mask = [], size - 1
    while mask:
        zones.append(choice[mask])
        mask ^= choice[mask]
    return count, zones


def members(mask, n):
    return [k for k in range(n) if mask >> k & 1]
