"""Assisted import from a plan image or PDF, on synthetic drawings (black walls on white, 8 px thick)."""
import io

import pytest

PIL = pytest.importorskip("PIL", reason="install the import extra")
pytest.importorskip("skimage", reason="install the import extra")
from PIL import Image, ImageDraw  # noqa: E402

from loopwright.config import DEFAULT  # noqa: E402
from loopwright.io.image import read_image, read_pdf  # noqa: E402
from loopwright.io.sketch import build_plan  # noqa: E402
from loopwright.solve import solve  # noqa: E402

M_PER_PX = 0.025  # 40 px per metre


def plan_image(*, door=True, arc=False, corridor=False, furniture=False, front_door=False):
    """Two rooms (left 238 x 144 px inside, right 178 x 144 px) or, with corridor, room | 40 px corridor | room."""
    img = Image.new("L", (480, 200), 255)
    d = ImageDraw.Draw(img)
    wall = lambda x0, y0, x1, y1: d.rectangle([x0, y0, x1 - 1, y1 - 1], fill=0)
    wall(20, 20, 460, 28), wall(20, 172, 460, 180), wall(20, 20, 28, 180), wall(452, 20, 460, 180)
    if corridor:
        wall(226, 28, 234, 172), wall(274, 28, 282, 172)              # corridor 40 px (1.0 m) between x 234 and 274
        d.rectangle([226, 85, 233, 114], fill=255)                    # door room A -> corridor
        d.rectangle([274, 85, 281, 114], fill=255)                    # door corridor -> room B
    else:
        wall(266, 28, 274, 172)
        if door:
            d.rectangle([266, 85, 273, 114], fill=255)                # 30 px door gap
            if arc:
                d.line([274, 85, 304, 85], fill=0, width=1)           # door leaf
                d.arc([244, 55, 304, 115], start=270, end=360, fill=0, width=1)
    if furniture:
        d.line([360, 28, 360, 171], fill=0, width=1)                  # a thin line from wall to wall
    if front_door:
        d.rectangle([100, 172, 129, 179], fill=255)                   # gap in the outside wall
    buf = io.BytesIO()
    img.save(buf, format="PNG")
    return buf.getvalue()


def plan_of(sketch):
    return build_plan(sketch["rooms"], sketch["doors"], wall_m=sketch["wall_m"])


def solve_sketch(sketch):
    out, _ = solve(plan_of(sketch), DEFAULT)
    return out["metrics"]["hubs"], out["validation"]["valid"]


def area(poly):
    return abs(sum(x0 * y1 - x1 * y0 for (x0, y0), (x1, y1) in zip(poly, poly[1:] + poly[:1]))) / 2


def test_two_rooms_and_a_door_gap_become_one_zone():
    sketch = read_image(plan_image(), m_per_px=M_PER_PX)
    assert [r["type"] for r in sketch["rooms"]] == ["living", "bedroom"]
    assert sketch["doors"] == [[0, 1]]
    assert solve_sketch(sketch) == (1, True)


def test_room_interiors_keep_their_drawn_size():
    sketch = read_image(plan_image(), m_per_px=M_PER_PX)
    assert sketch["wall_m"] == pytest.approx(8 * M_PER_PX, abs=M_PER_PX)
    assert plan_of(sketch)["living"].area == pytest.approx(238 * 144 * M_PER_PX ** 2, rel=0.03)   # 21.42 m² as drawn


def test_without_a_gap_the_rooms_stay_apart():
    sketch = read_image(plan_image(door=False), m_per_px=M_PER_PX)
    assert (len(sketch["rooms"]), sketch["doors"]) == (2, [])
    assert solve_sketch(sketch)[0] == 2


def test_a_drawn_door_leaf_and_swing_still_reads_as_a_door():
    assert read_image(plan_image(arc=True), m_per_px=M_PER_PX)["doors"] == [[0, 1]]


def test_a_thin_line_across_a_room_does_not_split_it():
    sketch = read_image(plan_image(furniture=True), m_per_px=M_PER_PX)
    assert (len(sketch["rooms"]), sketch["doors"]) == (2, [[0, 1]])


def test_a_gap_in_the_outside_wall_is_not_a_door_between_rooms():
    sketch = read_image(plan_image(front_door=True), m_per_px=M_PER_PX)
    assert (len(sketch["rooms"]), sketch["doors"]) == (2, [[0, 1]])


def test_a_narrow_corridor_between_parallel_walls_is_kept():
    sketch = read_image(plan_image(corridor=True), m_per_px=M_PER_PX)
    assert len(sketch["rooms"]) == 3
    corridor = min(range(3), key=lambda k: area(sketch["rooms"][k]["polygon"]))
    assert sorted(map(sorted, sketch["doors"])) == sorted(sorted([corridor, k]) for k in range(3) if k != corridor)


def test_scale_from_the_flat_area():
    sketch = read_image(plan_image(), area_m2=21.42 + 16.02)          # both interiors as drawn: 37.44 m²
    assert sketch["m_per_px"] == pytest.approx(M_PER_PX, rel=0.02)


def test_a_pdf_page_reads_like_the_image():
    buf = io.BytesIO()
    Image.open(io.BytesIO(plan_image())).convert("RGB").save(buf, format="PDF", resolution=72)
    sketch = read_pdf(buf.getvalue(), dpi=72, m_per_px=M_PER_PX)
    assert (len(sketch["rooms"]), sketch["doors"]) == (2, [[0, 1]])


def test_scale_is_required():
    with pytest.raises(ValueError, match="scale"):
        read_image(plan_image())


def test_an_image_with_no_rooms_is_refused():
    buf = io.BytesIO()
    Image.new("L", (100, 100), 255).save(buf, format="PNG")
    with pytest.raises(ValueError, match="no rooms"):
        read_image(buf.getvalue(), m_per_px=M_PER_PX)
