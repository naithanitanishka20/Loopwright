import pytest

from loopwright.config import DEFAULT, Settings


def test_defaults_match_the_assumptions_ledger():
    assert DEFAULT.zone_link == "strict"          # Q1
    assert DEFAULT.max_nodes == 5                 # Q4
    assert DEFAULT.max_area_m2 == 100.0
    assert DEFAULT.lane_gap_m == 0.4              # Q3
    assert DEFAULT.living_pieces == "merge"       # Q9
    assert (DEFAULT.bend_m, DEFAULT.crossing_m, DEFAULT.overlap_factor) == (0.3, 3.0, 2.0)  # Q2


def test_overrides_and_validation():
    s = DEFAULT.with_overrides(zone_link="through_rooms", max_nodes=None)
    assert s.zone_link == "through_rooms" and s.max_nodes == 5
    with pytest.raises(ValueError):
        DEFAULT.with_overrides(zone_link="sideways")
    with pytest.raises(ValueError):
        DEFAULT.with_overrides(not_a_setting=1)
    with pytest.raises(ValueError):
        Settings(max_nodes=0)
