import pytest

from loopwright.config import DEFAULT, Settings


def test_defaults_match_the_assumptions_ledger():
    assert DEFAULT.zone_link == "strict"          # Q1
    assert DEFAULT.max_nodes == 5                 # Q4
    assert DEFAULT.max_area_m2 == 100.0
    assert DEFAULT.tolerance_m == 0.001           # Q3, slide 7
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


@pytest.mark.parametrize(
    ("field", "value"),
    [
        ("bend_m", float("nan")),
        ("crossing_m", float("inf")),
        ("overlap_factor", float("-inf")),
        ("max_area_m2", float("nan")),
<<<<<<< HEAD
        ("lane_gap_m", -0.1),
=======
        ("tolerance_m", -0.1),
>>>>>>> e93d1bc4ec002a5c7592ba84d9672f2712ba5fd4
        ("min_hub_node_m", -1.0),
        ("clearance_m", -0.01),
        ("sliver_m2", -0.01),
        ("time_limit_s", 0.0),
    ],
)
def test_numeric_settings_reject_non_finite_or_invalid_values(field, value):
    with pytest.raises(ValueError):
        Settings(**{field: value})


def test_integer_and_boolean_settings_have_exact_types():
    with pytest.raises(ValueError):
        Settings(max_nodes=True)
    with pytest.raises(ValueError):
        Settings(max_nodes=5.0)
    with pytest.raises(ValueError):
        Settings(bend_at_node=1)
    with pytest.raises(ValueError):
        Settings(count_self_crossings="yes")


def test_pass_through_is_normalized_and_rejects_malformed_values():
    settings = Settings(pass_through=["circulation"])
    assert settings.pass_through == ("circulation",)

    with pytest.raises(ValueError):
        Settings(pass_through="circulation")
    with pytest.raises(ValueError):
        Settings(pass_through=["unknown"])
