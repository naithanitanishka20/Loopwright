"""The site's scale-model figure: everything the solver placed is built, and the live data is true."""
import re

import pytest
from shapely.geometry import Polygon, box

from loopwright.figure import hub_size, model_svg, room_name
from loopwright.io.sketch import build_plan
from loopwright.iso import rect_ring
from loopwright.solve import solve


def square(x0, y0, x1, y1):
    return [[x0, y0], [x1, y0], [x1, y1], [x0, y1]]


FLAT = build_plan([{"type": "living", "polygon": square(0, 0, 6, 6)},
                   {"type": "bedroom", "polygon": square(6, 0, 11, 5)},
                   {"type": "kitchen", "polygon": square(0, 6, 4, 10)}], doors=[(0, 1), (0, 2)])


@pytest.fixture(scope="module")
def solved():
    out, model = solve(FLAT)
    svg, meta = model_svg(model, out, live=True)
    return out, svg, meta


def test_every_node_hub_and_leg_of_the_solution_is_built(solved):
    out, svg, _ = solved
    assert len(re.findall(r'<g class="socket"', svg)) == len(out["nodes"])
    assert len(re.findall(r'<g class="hub"', svg)) == len(out["hubs"])
    for ring in out["rings"]:
        for leg in ring["legs"]:
            mark = f'data-ring="{ring["hub"]}" data-leg="{leg["n"]}"'
            assert re.search(r'<g class="tb cable[^"]*" ' + mark, svg), mark
            assert re.search(r'<path class="hit" ' + mark, svg), mark


def test_live_pieces_carry_their_place_along_the_ring_in_order(solved):
    out, svg, meta = solved
    ring = out["rings"][0]
    spans = sorted((float(a), float(b)) for a, b in re.findall(
        rf'<g class="tb cable[^"]*" data-ring="{ring["hub"]}" data-leg="\d+" data-a="([\d.]+)" data-b="([\d.]+)"', svg))
    assert spans and all(a < b for a, b in spans)
    assert all(b1 <= a2 + 1e-6 for (_, b1), (a2, _) in zip(spans, spans[1:]))
    stops = meta["rings"][0]["stops"]
    assert [s["node"] for s in stops] == [leg["to"] for leg in ring["legs"][:-1]]
    assert all(s1["s"] < s2["s"] for s1, s2 in zip(stops, stops[1:]))
    assert spans[-1][1] <= meta["rings"][0]["length"] + 1e-6
    assert meta["rings"][0]["length"] == pytest.approx(ring["length_m"], abs=0.1)


def test_each_leg_has_one_short_joint_that_can_be_cut(solved):
    out, svg, _ = solved
    for ring in out["rings"]:
        for leg in ring["legs"]:
            joints = re.findall(rf'<g class="tb cable joint" data-ring="{ring["hub"]}" data-leg="{leg["n"]}"[^>]*>(.*?)</g>', svg)
            assert len(joints) == 1
            assert joints[0].count('class="cut-end"') == 2


def test_a_hub_box_turns_or_shrinks_to_clear_a_wall_beside_it():
    wall = box(0.0, 0.0, 10.0, 0.2)
    w, d = hub_size((5.0, 0.4), wall)  # the full box would reach 0.19, into the wall
    assert (w, d) != (0.62, 0.42)
    assert wall.intersection(Polygon(rect_ring(5.0 - w / 2, 0.4 - d / 2, 5.0 + w / 2, 0.4 + d / 2))).area < 1e-4
    assert hub_size((5.0, 3.0), wall) == (0.62, 0.42)


def test_room_names_read_the_way_a_person_says_them():
    rooms = ["living_0", "bedroom_0", "bedroom_2", "kitchen_0"]
    assert [room_name(r, rooms) for r in rooms] == ["living room", "bedroom 1", "bedroom 3", "kitchen"]


def test_a_still_figure_has_no_signal_paths_or_hit_targets():
    out, model = solve(FLAT)
    svg, _ = model_svg(model, out)
    assert 'class="core"' not in svg and 'class="hit"' not in svg and "data-a=" not in svg


@pytest.mark.dataset
def test_past_three_hubs_zones_are_coloured_by_role_so_no_two_unrelated_zones_match(resplan_plans):
    import re

    from loopwright.io.resplan import get_plan

    out, model = solve(get_plan(resplan_plans, 16448))
    svg, _ = model_svg(model, out, coloured=True)
    colour = dict(re.findall(r'<g class="hub" data-hub="(H\d)" style="--ring:([^"]+)"', svg))
    living = next(h["id"] for h in out["hubs"] if any(r.startswith("living") for r in h["zone"]))
    singles = [h["id"] for h in out["hubs"] if len(h["zone"]) == 1]
    assert len(out["hubs"]) == 4 and singles
    assert all(colour[h] != colour[living] for h in singles)


@pytest.mark.dataset
def test_legs_too_short_to_see_get_no_click_target(resplan_plans):
    import re

    from loopwright.io.resplan import get_plan

    out, model = solve(get_plan(resplan_plans, 2916))
    svg, _ = model_svg(model, out, live=True)
    hits = re.findall(r'<path class="hit" data-ring="(H\d)" data-leg="(\d+)"', svg)
    assert ("H1", "2") in hits and not any(ring == "H2" for ring, _ in hits)  # H2's hub sits beside its socket


@pytest.mark.dataset
def test_a_real_plan_is_built_with_glazed_windows_and_open_doors(resplan_plans):
    from loopwright.io.resplan import get_plan

    out, model = solve(get_plan(resplan_plans, 2916))
    svg, meta = model_svg(model, out, live=True)
    assert 'class="wall-face glass"' in svg and 'class="iso-top glass-top"' in svg
    panes = re.findall(r'class="iso-top glass-top" d="([^"]+)"', svg)
    assert all(svg.count(f'd="{d}"') == 2 for d in panes)  # each pane is outlined, so its frame lines end on a stroke
    assert svg.count('class="threshold"') >= 5
    assert [r["hub"] for r in meta["rings"]] == ["H1", "H2"]
    assert meta["rings"][0]["length"] == pytest.approx(out["rings"][0]["length_m"], abs=0.1)
