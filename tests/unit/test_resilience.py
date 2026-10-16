import pytest

from loopwright.config import DEFAULT
from loopwright.output.resilience import cut_analysis
from loopwright.solve import solve
from tests.helpers import two_room_plan

# H1 -> N1 -> N2 -> N3 -> H1 with legs of 2, 3, 4 and 5 m (ring 14 m).
RING = {"hub": "H1", "sequence": ["H1", "N1", "N2", "N3", "H1"],
        "legs": [{"n": i, "length_m": m} for i, m in enumerate((2.0, 3.0, 4.0, 5.0), start=1)]}


def cuts():
    return {c["leg"]: c for c in cut_analysis({"rings": [RING]})["H1"]}


def test_cutting_a_middle_leg_feeds_each_side_from_its_own_end():
    c = cuts()[3]  # between N2 and N3
    assert c["fed_forward"] == [{"node": "N1", "m": 2.0}, {"node": "N2", "m": 5.0}]
    assert c["fed_reverse"] == [{"node": "N3", "m": 5.0}]
    assert c["farthest_m"] == 5.0


def test_cutting_the_first_leg_feeds_every_node_the_other_way_round():
    c = cuts()[1]
    assert c["fed_forward"] == []
    assert c["fed_reverse"] == [{"node": "N3", "m": 5.0}, {"node": "N2", "m": 9.0}, {"node": "N1", "m": 12.0}]
    assert c["farthest_m"] == 12.0


def test_cutting_the_last_leg_feeds_every_node_forward():
    c = cuts()[4]
    assert [f["node"] for f in c["fed_forward"]] == ["N1", "N2", "N3"]
    assert c["fed_reverse"] == []
    assert c["farthest_m"] == 9.0


def test_a_one_node_ring_survives_either_cut():
    ring = {"hub": "H1", "sequence": ["H1", "N1", "H1"], "legs": [{"n": 1, "length_m": 0.6}, {"n": 2, "length_m": 0.6}]}
    c = {x["leg"]: x for x in cut_analysis({"rings": [ring]})["H1"]}
    assert c[1]["fed_reverse"] == [{"node": "N1", "m": 0.6}]
    assert c[2]["fed_forward"] == [{"node": "N1", "m": 0.6}]


@pytest.mark.parametrize("rooms", [1, 2])
def test_no_single_cut_on_a_solved_design_leaves_a_node_unfed(rooms):
    plan = two_room_plan()
    if rooms == 1:
        plan.pop("bedroom")
    design, _ = solve(plan, DEFAULT)
    for ring in design["rings"]:
        nodes = set(ring["sequence"][1:-1])
        for c in cut_analysis(design)[ring["hub"]]:
            fed = [f["node"] for f in c["fed_forward"] + c["fed_reverse"]]
            assert sorted(fed) == sorted(nodes)
