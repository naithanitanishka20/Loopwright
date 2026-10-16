import copy
import json
import pathlib

import pytest
from shapely import affinity

from loopwright.config import DEFAULT
from loopwright.io.sketch import build_plan
from loopwright.output.schema import digest, write_json
from loopwright.solve import solve
from loopwright.validate.rules import validate
from tests.helpers import two_room_plan

SCHEMA = json.loads((pathlib.Path(__file__).resolve().parents[2] / "docs" / "schema-v2.json").read_text(encoding="utf-8"))


@pytest.fixture()
def solved():
    plan = two_room_plan()
    out, _ = solve(plan)
    return plan, out


def failed(plan, out, settings=DEFAULT):
    return {c["id"] for c in validate(plan, out, settings)["checks"] if c["pass"] is False}


def test_two_rooms_share_one_hub_and_pass_every_checked_rule(solved):
    plan, out = solved
    assert out["metrics"]["hubs"] == 1 and out["metrics"]["hub_lower_bound"] == 1
    assert out["rings"][0]["sequence"][0] == out["rings"][0]["sequence"][-1] == "H1"
    assert out["validation"]["valid"] is True
    assert set(SCHEMA["required"]) <= set(out)


def test_output_is_deterministic():
    a, _ = solve(two_room_plan())
    b, _ = solve(two_room_plan())
    assert digest(a) == digest(b)


def test_diagonal_segment_fails_v14(solved):
    plan, out = solved
    bad = copy.deepcopy(out)
    leg = bad["rings"][0]["legs"][1]
    leg["path"] = [leg["path"][0], leg["path"][-1]]
    leg["path"][-1] = [leg["path"][-1][0], leg["path"][-1][1] + 0.5]
    assert "V14" in failed(plan, bad)


def test_skipped_node_fails_v08(solved):
    plan, out = solved
    bad = copy.deepcopy(out)
    bad["rings"][0]["sequence"].pop(1)
    assert "V08" in failed(plan, bad)


def test_ring_ending_at_another_hub_fails_v07(solved):
    plan, out = solved
    bad = copy.deepcopy(out)
    bad["rings"][0]["sequence"][-1] = "H9"
    assert "V07" in failed(plan, bad)


def test_run_through_a_wall_fails_v10(solved):
    plan, out = solved
    bad = copy.deepcopy(out)
    # Push the leg that crosses the middle wall up to y = 3.0, above the door (1.5 to 2.4).
    for leg in bad["rings"][0]["legs"]:
        xs = [p[0] for p in leg["path"]]
        if min(xs) < 4.95 < max(xs):
            leg["path"] = [[p[0], 3.0] for p in leg["path"]]
    assert "V10" in failed(plan, bad)


def test_hub_in_the_wrong_room_fails_v06(solved):
    plan, out = solved
    bad = copy.deepcopy(out)
    bad["hubs"][0]["zone"] = ["bedroom_0"]
    bad["hubs"][0]["pos"] = [2.0, 2.0]          # inside the living room, not the bedroom
    assert "V06" in failed(plan, bad)


def test_routes_go_through_the_door(solved):
    plan, out = solved
    crossing = [leg for leg in out["rings"][0]["legs"]
                if min(p[0] for p in leg["path"]) < 4.95 < max(p[0] for p in leg["path"])]
    assert crossing, "some leg must cross the middle wall"
    for leg in crossing:
        for (x0, y0), (x1, y1) in zip(leg["path"], leg["path"][1:]):
            if min(x0, x1) < 5.0 < max(x0, x1):
                assert 1.5 < y0 < 2.4, f"crossed the wall outside the door at y={y0}"


def test_walling_up_the_door_breaks_zone_contiguity(solved):
    plan, out = solved
    from shapely.ops import unary_union

    sealed = dict(plan, wall=unary_union([plan["wall"], plan["door"]]), door=None)
    assert "V05" in failed(sealed, out)


def test_caps_are_enforced(solved):
    plan, out = solved
    assert "V03" in failed(plan, out, DEFAULT.with_overrides(max_area_m2=20.0))
    assert "V04" in failed(plan, out, DEFAULT.with_overrides(max_nodes=1))


def test_a_design_validates_the_same_from_its_json_file(tmp_path):
    # The validator rebuilds every area and length from frame.m_per_unit, so the file must keep the
    # scale exact. Rounded, it pushed this 99.9 m² zone over the cap.
    s = 0.06881688433052152
    plan = build_plan([{"type": "living", "polygon": [[0, 0], [10.1, 0], [10.1, 6], [0, 6]]},
                       {"type": "bedroom", "polygon": [[0, 6], [10.1, 6], [10.1, 10.19], [0, 10.19]]}],
                      doors=[(0, 1)])
    plan = {k: affinity.scale(v, 1 / s, 1 / s, origin=(0, 0)) if hasattr(v, "geom_type") else v
            for k, v in plan.items()}
    plan.update(m_per_unit=s, wall_depth=plan["wall_depth"] / s)
    out, _ = solve(plan)
    assert out["metrics"]["hubs"] == 1 and out["validation"]["valid"] is True

    write_json(out, tmp_path / "design.json")
    back = json.loads((tmp_path / "design.json").read_text(encoding="utf-8"))
    assert failed(plan, back) == set()
    assert back["frame"]["m_per_unit"] == s


def test_a_plan_too_big_for_the_exact_search_is_refused_quickly_with_a_reason():
    import time

    from loopwright.io.sketch import build_plan
    from loopwright.optimize.zones import MAX_EXACT_ROOMS

    n = MAX_EXACT_ROOMS + 1  # one limit, owned by the zone search
    rooms = [{"type": "bedroom", "polygon": [[4 * i, 0], [4 * i + 4, 0], [4 * i + 4, 4], [4 * i, 4]]} for i in range(n)]
    plan = build_plan(rooms, [(i, i + 1) for i in range(n - 1)])
    started = time.perf_counter()
    with pytest.raises(ValueError, match=f"{n} eligible rooms"):
        solve(plan)
    assert time.perf_counter() - started < 5


def test_a_living_room_drawn_in_two_parts_puts_its_node_where_the_bedroom_opens():
    sq = lambda x0, y0, x1, y1: [[x0, y0], [x1, y0], [x1, y1], [x0, y1]]
    plan = build_plan([{"type": "living", "polygon": sq(0, 0, 6, 5)},   # the larger part, walled off from the rest
                       {"type": "living", "polygon": sq(6, 0, 9, 4)},   # the part the bedroom opens onto
                       {"type": "bedroom", "polygon": sq(9, 0, 13, 4)}], doors=[(1, 2)])
    settings = DEFAULT.with_overrides(node_rule="pole")  # the pole of the whole living room lies in the larger part
    out, model = solve(plan, settings)
    assert [sp.id for sp in model.eligible] == ["living_0", "bedroom_0"]
    assert out["metrics"]["hubs"] == 1 and out["validation"]["valid"]  # 54 m² and two nodes: one zone
    living = next(n for n in out["nodes"] if n["room"] == "living_0")
    x0, _, x1, _ = model.space("living_0").geom.bounds
    assert living["pos"][0] > x0 + (x1 - x0) * 6 / 9  # east of the wall at 6 m: in the bedroom's part
    assert any(d["code"] == "NODE_MOVED" for d in out["diagnostics"])


def test_a_door_drawn_a_hair_short_of_its_wall_still_joins_the_rooms():
    from shapely.geometry import box
    from shapely.ops import unary_union

    # The wall runs to x = 5.05 and the door to a float hair short of it. Cut out exactly, the door would leave a
    # sliver of wall across the doorway that parts the two rooms; the drawn plans of three rooms hit this.
    plan = two_room_plan()
    plan.update(wall=unary_union([plan["wall"], box(4.95, 0.1, 5.05, 3.9)]), door=box(4.95, 1.5, 5.05 - 1e-12, 2.4))
    out, _ = solve(plan)
    assert out["metrics"]["hubs"] == 1 and out["validation"]["valid"]


def test_greedy_joins_only_rooms_that_share_a_walkable_area():
    from shapely.geometry import box
    from shapely.ops import unary_union

    # An opening with no door in the middle wall, and an external area laid over it: the door graph still sees the
    # opening, but no cable may pass, so greedy can't count the two rooms as one zone any more than the exact search.
    plan = two_room_plan()
    plan.update(door=None, balcony=box(4.9, 1.5, 5.1, 2.4))
    out, _ = solve(plan)
    assert out["metrics"]["hubs"] == 2
    assert out["metrics"]["hubs_greedy"] == 2


def test_a_door_drawn_short_of_its_walls_far_face_still_opens_the_wall():
    from shapely.geometry import box
    from shapely.ops import unary_union

    # ResPlan draws some doors a few centimetres shallower than their wall (plan 4755: 3 cm short). The door is still
    # an opening through the whole wall, so the strip of wall left in front of it must not part the rooms.
    plan = two_room_plan()
    plan.update(wall=unary_union([plan["wall"], box(4.95, 0.1, 5.05, 3.9)]), door=box(4.95, 1.5, 5.02, 2.4))
    out, _ = solve(plan)
    assert out["metrics"]["hubs"] == 1 and out["validation"]["valid"]


def test_a_room_part_too_narrow_for_a_node_does_not_get_it():
    sq = lambda x0, y0, x1, y1: [[x0, y0], [x1, y0], [x1, y1], [x0, y1]]
    plan = build_plan([{"type": "living", "polygon": sq(0, 0, 6, 5)},
                       {"type": "living", "polygon": sq(6, 0, 6.8, 4)},   # 0.7 m clear: no point 0.5 m from its walls
                       {"type": "bedroom", "polygon": sq(6.8, 0, 10.8, 4)}], doors=[(1, 2)])
    out, _ = solve(plan, DEFAULT.with_overrides(node_rule="pole"))
    assert out["metrics"]["hubs"] == 2 and out["validation"]["valid"]
    assert not any(d["code"] == "NODE_MOVED" for d in out["diagnostics"])


def test_a_leg_through_a_wall_that_meets_a_doors_side_fails_v10(solved):
    from shapely.geometry import box
    from shapely.ops import unary_union

    # A wall runs into the side of the door. Only the door is an opening: a leg crossing that wall 3 cm from the
    # door, within the door's reach, still crosses a wall.
    plan, out = solved
    plan = dict(plan, wall=unary_union([plan["wall"], box(4.0, 2.2, 4.95, 2.3)]))  # clear of the design's legs
    assert "V10" not in failed(plan, out)
    bad = copy.deepcopy(out)
    bad["rings"][0]["legs"][0]["path"] = [[4.92, 2.1], [4.92, 2.35]]
    assert "V10" in failed(plan, bad)
