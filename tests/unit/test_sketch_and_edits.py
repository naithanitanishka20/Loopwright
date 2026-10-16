import math

import pytest

from loopwright.config import DEFAULT
from loopwright.io.edits import apply_edits
from loopwright.io.sketch import build_plan
from loopwright.solve import solve
from tests.helpers import two_room_plan

LIVING = {"type": "living", "polygon": [[0, 0], [5, 0], [5, 4], [0, 4]]}
BEDROOM = {"type": "bedroom", "polygon": [[5, 0], [10, 0], [10, 4], [5, 4]]}
FAR_BEDROOM = {"type": "bedroom", "polygon": [[20, 0], [25, 0], [25, 4], [20, 4]]}


def hubs_and_validity(plan):
    out, _ = solve(plan, DEFAULT)
    return out["metrics"]["hubs"], out["validation"]["valid"]


def test_a_door_between_sketched_rooms_lets_them_share_one_hub():
    assert hubs_and_validity(build_plan([LIVING, BEDROOM], doors=[(0, 1)])) == (1, True)


def test_sketched_rooms_without_a_door_need_a_hub_each():
    assert hubs_and_validity(build_plan([LIVING, BEDROOM], doors=[])) == (2, True)


def test_a_door_between_rooms_that_share_no_wall_is_refused():
    with pytest.raises(ValueError, match="share no wall"):
        build_plan([LIVING, FAR_BEDROOM], doors=[(0, 1)])


def test_an_unknown_room_type_is_refused():
    with pytest.raises(ValueError, match="room type"):
        build_plan([{"type": "ballroom", "polygon": LIVING["polygon"]}], doors=[])


@pytest.mark.parametrize("wall_m", [0, -1, math.nan, math.inf, True])
def test_invalid_wall_width_is_refused(wall_m):
    with pytest.raises(ValueError, match="wall_m must be a finite positive number"):
        build_plan([LIVING], doors=[], wall_m=wall_m)


def test_invalid_door_indices_are_refused():
    with pytest.raises(ValueError, match="door room indices"):
        build_plan([LIVING, BEDROOM], doors=[(0, 2)])


def test_removing_the_only_door_splits_the_zone():
    assert hubs_and_validity(two_room_plan()) == (1, True)
    assert hubs_and_validity(apply_edits(two_room_plan(), [{"op": "remove_door", "door": 0}])) == (2, True)


def test_connecting_two_rooms_cuts_a_door_they_can_share_a_hub_through():
    no_door = apply_edits(two_room_plan(), [{"op": "remove_door", "door": 0}])
    joined = apply_edits(no_door, [{"op": "connect", "rooms": ["living_0", "bedroom_0"]}])
    assert hubs_and_validity(joined) == (1, True)


def test_changing_a_bedroom_to_a_bathroom_removes_its_node():
    out, _ = solve(apply_edits(two_room_plan(), [{"op": "set_type", "room": "bedroom_0", "to": "bathroom"}]), DEFAULT)
    assert [r["type"] for r in out["rooms"] if r["eligible"]] == ["living"]
    assert len(out["nodes"]) == 1


def test_edits_leave_the_input_plan_untouched():
    plan = two_room_plan()
    door_before = plan["door"].wkt
    apply_edits(plan, [{"op": "remove_door", "door": 0}])
    assert plan["door"].wkt == door_before


@pytest.mark.parametrize("op", [
    {"op": "remove_door", "door": 5},
    {"op": "connect", "rooms": ["living_0", "kitchen_9"]},
    {"op": "set_type", "room": "bedroom_0", "to": "ballroom"},
    {"op": "paint_walls"},
])
def test_bad_edits_are_refused(op):
    with pytest.raises(ValueError):
        apply_edits(two_room_plan(), [op])
