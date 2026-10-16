import pytest

ezdxf = pytest.importorskip("ezdxf", reason="install the import extra")

from loopwright.config import DEFAULT  # noqa: E402
from loopwright.io.dxf import read_dxf  # noqa: E402
from loopwright.io.sketch import build_plan  # noqa: E402
from loopwright.solve import solve  # noqa: E402


def drawing(path, *, scale=1000, insunits=4, rooms=(("Living", (0, 0, 5, 4)), ("Bedroom 1", (5, 0, 10, 4))),
            doors=(((5, 2), (5.0001, 2)),)):
    """A DXF in the documented convention; geometry given in metres, written scale units per metre."""
    doc = ezdxf.new()
    doc.header["$INSUNITS"] = insunits
    msp = doc.modelspace()
    for label, (x0, y0, x1, y1) in rooms:
        pts = [(x0 * scale, y0 * scale), (x1 * scale, y0 * scale), (x1 * scale, y1 * scale), (x0 * scale, y1 * scale)]
        msp.add_lwpolyline(pts, close=True, dxfattribs={"layer": "ROOMS"})
        if label:
            msp.add_text(label, dxfattribs={"layer": "ROOMS"}).set_placement(((x0 + x1) / 2 * scale, (y0 + y1) / 2 * scale))
    for (ax, ay), (bx, by) in doors:
        msp.add_line((ax * scale - 0.2 * scale, ay * scale), (bx * scale + 0.2 * scale, by * scale), dxfattribs={"layer": "DOORS"})
    doc.saveas(path)
    return path


def test_rooms_labels_and_a_door_become_a_plan_one_hub_can_serve(tmp_path):
    sketch = read_dxf(drawing(tmp_path / "flat.dxf"))
    assert [r["type"] for r in sketch["rooms"]] == ["living", "bedroom"]
    assert sketch["doors"] == [[0, 1]]
    out, _ = solve(build_plan(sketch["rooms"], sketch["doors"]), DEFAULT)
    assert (out["metrics"]["hubs"], out["validation"]["valid"]) == (1, True)


def test_common_label_words_map_onto_room_types(tmp_path):
    rooms = (("LOUNGE", (0, 0, 5, 4)), ("Bed 2", (5, 0, 10, 4)), ("WC", (10, 0, 12, 4)))
    sketch = read_dxf(drawing(tmp_path / "flat.dxf", rooms=rooms, doors=()))
    assert [r["type"] for r in sketch["rooms"]] == ["living", "bedroom", "bathroom"]


def test_millimetres_and_metres_give_the_same_room_areas(tmp_path):
    in_mm = read_dxf(drawing(tmp_path / "mm.dxf", scale=1000, insunits=4))
    in_m = read_dxf(drawing(tmp_path / "m.dxf", scale=1, insunits=6))
    area = lambda s: [round(abs(sum(x0 * y1 - x1 * y0 for (x0, y0), (x1, y1) in zip(r["polygon"], r["polygon"][1:] + r["polygon"][:1]))) / 2, 3)
                      for r in s["rooms"]]
    assert area(in_mm) == area(in_m) == [20.0, 20.0]


def test_without_a_door_marker_the_rooms_are_not_connected(tmp_path):
    sketch = read_dxf(drawing(tmp_path / "flat.dxf", doors=()))
    assert sketch["doors"] == []


def test_an_unlabelled_room_is_named_in_the_error(tmp_path):
    with pytest.raises(ValueError, match="no label"):
        read_dxf(drawing(tmp_path / "flat.dxf", rooms=(("Living", (0, 0, 5, 4)), ("", (5, 0, 10, 4)))))


def test_a_door_marker_away_from_any_shared_wall_is_refused(tmp_path):
    with pytest.raises(ValueError, match="door"):
        read_dxf(drawing(tmp_path / "flat.dxf", doors=(((2, 2), (2.0001, 2)),)))
