"""Synthetic plans in metres (area == inner area, so m_per_unit == 1)."""
from shapely.geometry import box
from shapely.ops import unary_union


def two_room_plan():
    """Living (left) and bedroom (right), one door in the shared wall at y 1.5-2.4."""
    door = box(4.95, 1.5, 5.05, 2.4)
    outer = unary_union([box(0, 0, 10, 0.1), box(0, 3.9, 10, 4), box(0, 0, 0.1, 4), box(9.9, 0, 10, 4)])
    middle = box(4.95, 0.1, 5.05, 3.9).difference(door)
    return {
        "id": 1,
        "area": 40.0,
        "wall_depth": 0.1,
        "inner": box(0, 0, 10, 4),
        "living": box(0.1, 0.1, 4.95, 3.9),
        "bedroom": box(5.05, 0.1, 9.9, 3.9),
        "wall": unary_union([outer, middle]),
        "door": door,
        "window": box(2, 3.9, 3, 4),
    }
