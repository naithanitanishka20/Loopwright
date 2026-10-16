<<<<<<< HEAD
import math

import pytest

from loopwright.routing import axis_aligned_path


def test_axis_aligned_path_uses_one_corner():
    assert axis_aligned_path((1, 2), (4, 6)) == ((1.0, 2.0), (4.0, 2.0), (4.0, 6.0))
    assert axis_aligned_path((1, 2), (1, 6)) == ((1.0, 2.0), (1.0, 6.0))


def test_axis_aligned_path_rejects_non_finite_points():
    with pytest.raises(ValueError):
        axis_aligned_path((math.nan, 2), (4, 6))
=======
from loopwright.routing.straight import l_leg


def test_l_leg_uses_one_corner():
    assert l_leg((1, 2), (4, 6)) == [(1.0, 2.0), (4.0, 2.0), (4.0, 6.0)]
    assert l_leg((1, 2), (1, 6)) == [(1.0, 2.0), (1.0, 6.0)]


def test_l_leg_keeps_two_points_for_a_zero_length_leg():
    # Schema loopwright/2 needs at least two points per leg path.
    assert l_leg((1, 2), (1, 2)) == [(1, 2), (1, 2)]
>>>>>>> e93d1bc4ec002a5c7592ba84d9672f2712ba5fd4
