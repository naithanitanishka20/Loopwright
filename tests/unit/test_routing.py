import math

import pytest

from loopwright.routing import axis_aligned_path


def test_axis_aligned_path_uses_one_corner():
    assert axis_aligned_path((1, 2), (4, 6)) == ((1.0, 2.0), (4.0, 2.0), (4.0, 6.0))
    assert axis_aligned_path((1, 2), (1, 6)) == ((1.0, 2.0), (1.0, 6.0))


def test_axis_aligned_path_rejects_non_finite_points():
    with pytest.raises(ValueError):
        axis_aligned_path((math.nan, 2), (4, 6))
