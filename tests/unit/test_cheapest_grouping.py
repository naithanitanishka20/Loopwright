"""Among the groupings with the fewest hubs, the one with the least cable."""
from hypothesis import given, settings as hsettings, strategies as st

from loopwright.config import DEFAULT
from loopwright.optimize.zones import INF, feasible_zones, min_hubs, min_hubs_cheapest


def partitions(items):
    if not items:
        yield []
        return
    first, rest = items[0], items[1:]
    for sub in partitions(rest):
        for i in range(len(sub)):
            yield sub[:i] + [[first] + sub[i]] + sub[i + 1:]
        yield [[first]] + sub


def mask(group):
    return sum(1 << k for k in group)


@hsettings(max_examples=150, deadline=None)
@given(st.data())
def test_the_cheapest_grouping_keeps_the_fewest_hubs_and_costs_least(data):
    n = data.draw(st.integers(min_value=1, max_value=6))
    areas = data.draw(st.lists(st.floats(min_value=1, max_value=99, allow_nan=False), min_size=n, max_size=n))
    table = data.draw(st.lists(st.floats(min_value=0, max_value=50, allow_nan=False), min_size=1 << n, max_size=1 << n))
    feasible = feasible_zones(areas, DEFAULT, relax_singletons=False)
    count, zones = min_hubs_cheapest(n, feasible, lambda m: table[m])
    assert count == min_hubs(n, feasible)[0]
    if count < INF:
        assert sorted(k for z in zones for k in range(n) if z >> k & 1) == list(range(n))
        best = min(sum(table[mask(g)] for g in p) for p in partitions(list(range(n)))
                   if len(p) == count and all(feasible[mask(g)] for g in p))
        assert abs(sum(table[z] for z in zones) - best) < 1e-6


def test_a_single_best_grouping_needs_no_costing():
    feasible = feasible_zones([60.0, 50.0], DEFAULT, relax_singletons=False)  # 110 m²: two zones, one way

    def cost(m):
        raise AssertionError("costed a zone with only one best grouping")

    count, zones = min_hubs_cheapest(2, feasible, cost)
    assert count == 2 and sorted(zones) == [0b01, 0b10]
