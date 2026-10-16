"""Isometric drawing for the site's figures: camera, shading by facing, rectangles and painter's order."""
import math

import pytest
from shapely.geometry import Point, Polygon, box

from loopwright.iso import Camera, Item, box_hit, extrude, order, rectangles


def test_the_camera_projects_like_the_figure_style():
    cam = Camera(scale=1.0, origin=(0.0, 0.0), azimuth=45.0, elevation=30.0)
    k, s, c = math.sqrt(1.6), math.sin(math.radians(45)), math.cos(math.radians(45))
    assert cam.iso((1.0, 0.0, 0.0)) == pytest.approx((s * k, c * 0.5 * k))
    assert cam.iso((0.0, 0.0, 1.0)) == pytest.approx((0.0, -math.cos(math.radians(30)) * k))


def test_a_ray_through_a_projected_point_passes_through_that_point():
    cam = Camera(scale=37.0, origin=(400.0, 120.0), azimuth=45.0, elevation=36.0)
    p = (2.0, -1.5, 0.7)
    p0, v = cam.ray(*cam.iso(p)), cam.view()
    t = p[2] / v[2]
    assert (p0[0] + t * v[0], p0[1] + t * v[1]) == pytest.approx(p[:2])


def test_the_side_facing_the_light_is_shaded_lightest_and_the_back_is_hidden():
    cam = Camera(scale=10.0)
    paths = extrude([(0, 0), (1, 0), (1, 1), (0, 1)], 0.0, 1.0, cam)
    # light comes from -x, +y: the +y face is lightest, the +x face darkest, -x and -y face away
    assert paths["shades"][3] and paths["shades"][0]
    assert not paths["shades"][1] and not paths["shades"][2]
    assert paths["top"].startswith("M") and paths["fill"].endswith("Z")


def test_rectangles_cover_a_rectilinear_outline_exactly_without_overlap():
    ell = Polygon([(0, 0), (4, 0), (4, 1), (1, 1), (1, 3), (0, 3)])
    pieces = [box(*r) for r in rectangles(ell)]
    assert sum(p.area for p in pieces) == pytest.approx(ell.area)
    assert all(a.intersection(b).area < 1e-9 for i, a in enumerate(pieces) for b in pieces[i + 1:])


def item(name, x0, y0, z0, x1, y1, z1, cam):
    corners = [(x, y, z) for x in (x0, x1) for y in (y0, y1) for z in (z0, z1)]
    hull = Polygon([cam.iso(p) for p in corners]).convex_hull
    centre = ((x0 + x1) / 2, (y0 + y1) / 2, (z0 + z1) / 2)
    return Item(name, hull, box_hit(x0, y0, z0, x1, y1, z1), cam.depth(centre))


def test_of_two_overlapping_boxes_the_nearer_is_drawn_last_whatever_the_input_order():
    cam = Camera(scale=40.0, origin=(300.0, 200.0))
    far, near = item("far", 0, 0, 0, 1, 1, 1, cam), item("near", 1.2, 1.2, 0, 2.2, 2.2, 0.4, cam)
    assert [i.svg for i in order([near, far], cam)] == ["far", "near"]
    assert [i.svg for i in order([far, near], cam)] == ["far", "near"]


def test_a_long_wall_sits_between_the_cable_behind_it_and_the_cable_in_front():
    cam = Camera(scale=40.0, origin=(300.0, 200.0), elevation=36.0)
    wall = item("wall", -3, -0.1, 0, 3, 0.1, 0.45, cam)
    behind = item("behind", 0.0, -0.6, 0, 0.3, -0.55, 0.05, cam)
    front = item("front", 0.0, 0.5, 0, 0.3, 0.55, 0.05, cam)
    assert [i.svg for i in order([front, wall, behind], cam)] == ["behind", "wall", "front"]


def test_a_small_box_in_front_of_the_end_of_a_long_wall_is_drawn_after_it_though_its_centre_is_farther():
    cam = Camera(scale=40.0, origin=(300.0, 200.0), elevation=36.0)
    wall = item("wall", -3, -0.1, 0, 3, 0.1, 0.45, cam)
    box_ = item("box", -2.6, 0.3, 0, -2.3, 0.6, 0.3, cam)
    assert box_.key < wall.key  # sorting by centre depth alone would hide the box behind the wall
    assert [i.svg for i in order([box_, wall], cam)] == ["wall", "box"]


def test_rectangles_skip_the_lines_an_intersection_leaves_behind():
    touching = box(0, 0, 2, 1).intersection(box(2, 0, 3, 1).union(box(0.5, 0, 1, 1)))
    assert rectangles(touching) == [(0.5, 0.0, 1.0, 1.0)]


def test_a_concave_outline_is_filled_by_its_own_faces_not_its_hull():
    cam = Camera(scale=40.0, origin=(300.0, 200.0))
    ell = [(0, 0), (4, 0), (4, 1), (1, 1), (1, 3), (0, 3)]
    fill = extrude(ell, 0.0, 0.1, cam)["fill"]
    notch = cam.iso((1.8, 1.6, 0.1))  # inside the hull, outside the L
    pieces = [Polygon([tuple(map(float, xy.split())) for xy in part.strip("Z").split("L")])
              for part in fill.replace("M", "|M").split("|M")[1:]]
    assert not any(piece.buffer(0).contains(Point(notch)) for piece in pieces)


def test_a_ray_meets_the_face_of_a_box_nearest_the_viewer():
    cam = Camera(scale=40.0, origin=(300.0, 200.0), elevation=36.0)
    p0, v = cam.ray(*cam.iso((0.5, 0.5, 0.5))), cam.view()
    t = box_hit(0, 0, 0, 1, 1, 1)(p0, v)
    near = [p0[k] + t * v[k] for k in range(3)]
    assert max(near) == pytest.approx(1.0)  # it leaves through the +x, +y or top face, the ones the viewer sees
    assert box_hit(0, 0, 0, 1, 1, 1)((p0[0] + 5, p0[1] - 5, p0[2]), v) is None
