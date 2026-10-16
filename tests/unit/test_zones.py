import math

import pytest
from hypothesis import given, settings as hsettings, strategies as st

from loopwright.config import DEFAULT, Settings
from loopwright.optimize.zones import INF, feasible_zones, lower_bound, min_hubs


def test_lower_bound_takes_the_tighter_cap():
    assert lower_bound(100.0, 5) == 1           # exactly at both caps
    assert lower_bound(100.01, 5) == 2          # area binds
    assert lower_bound(60.0, 6) == 2            # node cap binds
    assert lower_bound(0.0, 0) == 0             # no eligible rooms, no hub
    assert lower_bound(201, 11, Settings(max_area_m2=100, max_nodes=5)) == 3


@pytest.mark.parametrize(
    ("area", "n"),
    [(math.nan, 1), (math.inf, 1), (-1, 1), (True, 1), (1, -1), (1, True), (1, 2.0)],
)
def test_lower_bound_rejects_invalid_inputs(area, n):
    with pytest.raises(ValueError):
        lower_bound(area, n)


def test_min_hubs_packs_rooms_under_both_caps():
    feasible = feasible_zones([60.0, 50.0, 30.0], DEFAULT, relax_singletons=False)
    count, zones = min_hubs(3, feasible)
    assert count == 2 and sorted(bin(z).count("1") for z in zones) == [1, 2]


def test_over_cap_room_gets_its_own_relaxed_zone():
    strict = feasible_zones([130.0, 10.0], DEFAULT, relax_singletons=False)
    assert min_hubs(2, strict)[0] == INF
    relaxed = feasible_zones([130.0, 10.0], DEFAULT, relax_singletons=True)
    assert min_hubs(2, relaxed)[0] == 2


def test_exact_zone_search_rejects_unbounded_room_counts():
    with pytest.raises(ValueError, match="at most 12 rooms"):
        feasible_zones([1.0] * 13)

    with pytest.raises(ValueError, match="at most 12 rooms"):
        min_hubs(13, [False] * (1 << 13))


def test_connectivity_callback_forces_more_hubs():
    # Rooms 1 and 2 may only share a zone with room 0 (a star around the living room).
    star = lambda mask: mask & 1 == 1 or bin(mask).count("1") == 1
    feasible = feasible_zones([40.0, 30.0, 30.0], DEFAULT, connected=star, relax_singletons=False)
    assert min_hubs(3, feasible)[0] == 1        # all three fit around room 0
    feasible = feasible_zones([70.0, 30.0, 30.0], DEFAULT, connected=star, relax_singletons=False)
    assert min_hubs(3, feasible)[0] == 2        # area forces a split; 1 and 2 can't pair without 0


def _brute_force(areas, cap_area, cap_nodes):
    best = [INF]

    def go(i, zones):
        if len(zones) >= best[0]:
            return
        if i == len(areas):
            best[0] = len(zones)
            return
        for z in zones:
            if len(z) < cap_nodes and sum(areas[j] for j in z) + areas[i] <= cap_area + 1e-9:
                z.append(i)
                go(i + 1, zones)
                z.pop()
        if areas[i] <= cap_area + 1e-9:
            zones.append([i])
            go(i + 1, zones)
            zones.pop()

    go(0, [])
    return best[0]


def _connected(rooms, edges):
    rooms = list(rooms)
    seen, stack = {rooms[0]}, [rooms[0]]
    while stack:
        u = stack.pop()
        for v in rooms:
            if v not in seen and (min(u, v), max(u, v)) in edges:
                seen.add(v)
                stack.append(v)
    return len(seen) == len(rooms)


def _brute_force_linked(areas, edges, cap_area, cap_nodes):
    """Smallest partition into connected zones within both caps, by trying every set partition."""
    best = [INF]

    def parts(items):
        if not items:
            yield []
            return
        first, rest = items[0], items[1:]
        for sub in parts(rest):
            for i in range(len(sub)):
                yield sub[:i] + [[first] + sub[i]] + sub[i + 1:]
            yield [[first]] + sub

    for p in parts(list(range(len(areas)))):
        if len(p) < best[0] and all(
            len(z) <= cap_nodes and sum(areas[k] for k in z) <= cap_area + 1e-9 and _connected(z, edges) for z in p
        ):
            best[0] = len(p)
    return best[0]


@hsettings(max_examples=150, deadline=None)
@given(st.data())
def test_hub_minimum_with_door_links_matches_brute_force(data):
    n = data.draw(st.integers(min_value=1, max_value=6))
    areas = data.draw(st.lists(st.floats(min_value=1, max_value=99, allow_nan=False), min_size=n, max_size=n))
    pairs = [(i, j) for i in range(n) for j in range(i + 1, n)]
    edges = set(data.draw(st.lists(st.sampled_from(pairs), unique=True)) if pairs else [])

    def connected(mask):
        return _connected([k for k in range(n) if mask >> k & 1], edges)

    feasible = feasible_zones(areas, DEFAULT, connected=connected, relax_singletons=False)
    assert min_hubs(n, feasible)[0] == _brute_force_linked(areas, edges, DEFAULT.max_area_m2, DEFAULT.max_nodes)


@hsettings(max_examples=200, deadline=None)
@given(st.lists(st.floats(min_value=1, max_value=99, allow_nan=False), min_size=1, max_size=7))
def test_subset_search_matches_brute_force(areas):
    feasible = feasible_zones(areas, DEFAULT, relax_singletons=False)
    assert min_hubs(len(areas), feasible)[0] == _brute_force(areas, DEFAULT.max_area_m2, DEFAULT.max_nodes)
