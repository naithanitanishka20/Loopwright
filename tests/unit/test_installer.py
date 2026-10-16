from loopwright.config import DEFAULT
from loopwright.io.edits import door_parts
from loopwright.output.installer import installer_csv, installer_data
from loopwright.solve import solve
from tests.helpers import two_room_plan

# One ring H1 -> N1 -> N2 -> N3 -> H1, legs 2, 3, 4 and 5 m (14 m).
DESIGN = {
    "plan_id": "t",
    "hubs": [{"id": "H1", "room": "living_0"}],
    "nodes": [{"id": "N1", "room": "living_0"}, {"id": "N2", "room": "kitchen_0"}, {"id": "N3", "room": "bedroom_0"}],
    "rings": [{"hub": "H1", "sequence": ["H1", "N1", "N2", "N3", "H1"], "length_m": 14.0, "bends": 6,
               "legs": [{"n": i, "length_m": m, "path": []} for i, m in enumerate((2.0, 3.0, 4.0, 5.0), start=1)]}],
}


def test_ring_order_is_the_loop_address_order():
    ring = installer_data(DESIGN)["rings"][0]
    assert ring["addresses"] == [{"address": 1, "node": "N1", "room": "living_0"},
                                 {"address": 2, "node": "N2", "room": "kitchen_0"},
                                 {"address": 3, "node": "N3", "room": "bedroom_0"}]


def test_cable_slack_loop_resistance_and_worst_feed():
    ring = installer_data(DESIGN, slack=0.10)["rings"][0]
    assert ring["cable_m"] == 15.4          # 14 m + 10 %
    assert ring["loop_ohm"] == 0.339        # 2 conductors x 14 m x 12.1 ohm/km
    assert ring["worst_feed_m"] == 12.0     # first leg cut: N1 is fed the long way round


def test_bill_of_materials_adds_up_every_ring():
    second = {**DESIGN["rings"][0], "hub": "H2", "sequence": ["H2", "N4", "H2"], "length_m": 1.2,
              "legs": [{"n": 1, "length_m": 0.6, "path": []}, {"n": 2, "length_m": 0.6, "path": []}]}
    design = {**DESIGN, "hubs": DESIGN["hubs"] + [{"id": "H2", "room": "bedroom_1"}],
              "nodes": DESIGN["nodes"] + [{"id": "N4", "room": "bedroom_1"}], "rings": DESIGN["rings"] + [second]}
    bom = installer_data(design, slack=0.0)["bom"]
    assert bom == {"hubs": 2, "devices": 4, "cable_m": 15.2, "cable_m_with_slack": 15.2, "max_loop_ohm": 0.339}


def test_a_ring_between_two_rooms_passes_their_door_both_ways():
    design, model = solve(two_room_plan(), DEFAULT)
    ring = installer_data(design, door_parts(two_room_plan()))["rings"][0]
    assert ring["doors_passed"] == 2


def test_csv_has_one_row_per_device_in_address_order():
    lines = installer_csv(installer_data(DESIGN)).strip().splitlines()
    assert lines[0] == "hub,address,node,room,ring_cable_m,ring_loop_ohm"
    assert lines[1:] == ["H1,1,N1,living_0,15.4,0.339", "H1,2,N2,kitchen_0,15.4,0.339", "H1,3,N3,bedroom_0,15.4,0.339"]
