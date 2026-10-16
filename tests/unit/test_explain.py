from loopwright.output.explain import explain_hubs

RULES = {"max_area_m2": 100.0, "max_nodes": 5, "zone_link": "strict"}


def design(areas, hubs, lb, diagnostics=()):
    rooms = [{"id": f"room_{i}", "area_m2": a, "eligible": True} for i, a in enumerate(areas)]
    return {"rules": RULES, "rooms": rooms, "metrics": {"hubs": hubs, "hub_lower_bound": lb},
            "diagnostics": list(diagnostics)}


def test_at_the_bound_set_by_area():
    e = explain_hubs(design([60.0, 50.0, 37.0], hubs=2, lb=2))
    assert (e["binding"], e["rooms"]) == ("area", [])
    assert "147 m²" in e["text"] and "2" in e["text"]


def test_at_the_bound_set_by_the_node_cap():
    e = explain_hubs(design([10.0] * 7, hubs=2, lb=2))
    assert e["binding"] == "nodes"
    assert "7" in e["text"] and "5" in e["text"]


def test_one_zone_fits_everything():
    assert explain_hubs(design([40.0, 30.0], hubs=1, lb=1))["binding"] == "one zone"


def test_above_the_bound_names_the_rooms_door_links_strand():
    extra = [{"code": "EXTRA_HUB", "room": "room_3", "reason": "joins only through room_0 (zone 96.0 m², 3 nodes)"},
             {"code": "EXTRA_HUB", "room": "room_4", "reason": "joins only through room_0 (zone 96.0 m², 3 nodes)"}]
    e = explain_hubs(design([50.0, 20.0, 26.0, 12.0, 11.0], hubs=4, lb=2, diagnostics=extra))
    assert (e["binding"], e["rooms"]) == ("door links", ["room_3", "room_4"])
    assert "strict" in e["text"] and "room_3" in e["text"]


def test_a_single_hub_above_the_bound_is_explained_too():
    extra = [{"code": "EXTRA_HUB", "room": "room_2", "reason": "no door or opening to another eligible room"}]
    e = explain_hubs(design([50.0, 30.0, 12.0], hubs=2, lb=1, diagnostics=extra))
    assert (e["binding"], e["rooms"]) == ("door links", ["room_2"])


def test_a_room_over_the_area_cap_makes_the_plan_infeasible():
    over = [{"code": "ROOM_OVER_CAP", "room": "room_0", "area_m2": 130.4}]
    e = explain_hubs(design([130.4, 12.0], hubs=2, lb=2, diagnostics=over))
    assert (e["binding"], e["rooms"]) == ("room over cap", ["room_0"])
    assert "130.4 m²" in e["text"]
