"""The hub sits on its own ring, so it adds no cable (two rooms, nodes at the centre of 5.9 m squares)."""
from loopwright.config import DEFAULT
from loopwright.io.sketch import build_plan
from loopwright.solve import solve


def square(x0, y0, x1, y1):
    return [[x0, y0], [x1, y0], [x1, y1], [x0, y1]]


def ring_of(rooms, doors):
    out, _ = solve(build_plan(rooms, doors), DEFAULT)
    assert out["validation"]["valid"], [c for c in out["validation"]["checks"] if c["pass"] is False]
    return out["rings"][0]


def test_a_hub_on_the_path_between_nodes_adds_no_cable():
    # Nodes at (3, 3) and (3, 9): the ring is the 6 m run there and back, with a turn at each node.
    ring = ring_of([{"type": "living", "polygon": square(0, 0, 6, 6)},
                    {"type": "bedroom", "polygon": square(0, 6, 6, 12)}], doors=[(0, 1)])
    assert (ring["length_m"], ring["bends"]) == (12.0, 2)


def test_a_hub_on_a_corner_of_the_path_saves_that_bend():
    # Nodes at (3, 3) and (9, 5) with the door between: 8 m each way and 2 bends per leg,
    # plus a turn at each node; a hub at one of the corners takes one bend away.
    ring = ring_of([{"type": "living", "polygon": square(0, 0, 6, 6)},
                    {"type": "bedroom", "polygon": square(6, 2, 12, 8)}], doors=[(0, 1)])
    assert (ring["length_m"], ring["bends"]) == (16.0, 5)


def test_a_one_room_zone_keeps_its_out_and_back_ring():
    ring = ring_of([{"type": "living", "polygon": square(0, 0, 6, 6)}], doors=[])
    assert ring["length_m"] == 1.2
