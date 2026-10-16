from shapely.geometry import box
from shapely.ops import unary_union

from loopwright.geometry.walkable import open_walls


def test_a_door_opens_its_wall_face_to_face_but_leaves_a_wall_that_meets_its_side():
    # The door stops 3 cm short of its wall's far face (x = 5.05); another wall runs into the door's side.
    door, side = box(4.95, 1.0, 5.02, 3.0), box(4.0, 1.9, 4.95, 2.0)
    opened = open_walls({"wall": unary_union([box(4.95, 0.0, 5.05, 4.0), side]), "door": door}, wall_depth=0.1)
    assert opened.intersection(box(4.95, 1.0, 5.05, 3.0)).area < 1e-9   # the doorway is open from face to face
    assert abs(opened.intersection(side).area - side.area) < 1e-9       # the wall meeting its side keeps its end
