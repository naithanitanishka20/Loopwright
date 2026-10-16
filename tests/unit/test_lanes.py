"""Legs take a separate lane rather than run on top of cable already placed (slide 7 overlap)."""
from shapely.geometry import box

from loopwright.config import DEFAULT
from loopwright.geometry.spaces import build_model
from loopwright.io.sketch import build_plan
from loopwright.routing.grid import GridRouter, path_edges


def square(x0, y0, x1, y1):
    return [[x0, y0], [x1, y0], [x1, y1], [x0, y1]]


def open_room():
    plan = {"id": "open", "m_per_unit": 1.0, "wall_depth": 0.1, "inner": box(0, 0, 4, 4), "living": box(0, 0, 4, 4)}
    model = build_model(plan, DEFAULT)
    return GridRouter(model, {"a": (0.6, 2.0), "b": (3.4, 2.0)}, DEFAULT)


def test_a_leg_moves_to_a_parallel_lane_when_overlap_would_cost_more():
    router = open_room()
    straight = router.path("a", "b")
    lane = router.route_avoiding(tuple(straight[0]), tuple(straight[-1]), path_edges(router, straight), DEFAULT.overlap_factor)
    assert not path_edges(router, lane) & path_edges(router, straight)
    assert lane[0] == straight[0] and lane[-1] == straight[-1]


def test_with_nothing_to_avoid_the_lane_is_the_straight_path():
    router = open_room()
    straight = router.path("a", "b")
    assert router.route_avoiding(tuple(straight[0]), tuple(straight[-1]), set(), DEFAULT.overlap_factor) == straight


def test_a_ring_through_a_one_door_room_overlaps_less_with_lanes():
    plan = build_plan([{"type": "living", "polygon": square(0, 0, 6, 6)},
                       {"type": "bedroom", "polygon": square(6, 0, 11, 5)},
                       {"type": "bedroom", "polygon": square(0, 6, 5, 11)},
                       {"type": "kitchen", "polygon": square(6, 5, 10, 9)}], doors=[(0, 1), (0, 2), (0, 3)])
    with_lanes, _ = solve_with(plan, True)
    without, _ = solve_with(plan, False)
    assert with_lanes["validation"]["valid"] is True
    assert with_lanes["metrics"]["hubs"] == without["metrics"]["hubs"]
    assert with_lanes["metrics"]["J"] <= without["metrics"]["J"]
    assert with_lanes["metrics"]["overlap_m"] < without["metrics"]["overlap_m"]


def solve_with(plan, lanes):
    from loopwright.solve import solve
    return solve(plan, DEFAULT.with_overrides(separate_lanes=lanes))


def test_a_leg_goes_round_a_short_cable_rather_than_cross_it_when_that_is_cheaper():
    router = open_room()
    straight = router.path("a", "b")  # along y = 2.0
    stub = [[2.0, 1.8], [2.0, 2.2]]   # a cable already placed across it
    lane = router.route_avoiding(tuple(straight[0]), tuple(straight[-1]), path_edges(router, stub),
                                 DEFAULT.overlap_factor, DEFAULT.crossing_m)
    from shapely.geometry import LineString
    assert LineString(lane).intersection(LineString(stub)).is_empty
