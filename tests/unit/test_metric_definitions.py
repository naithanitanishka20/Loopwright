"""The four metrics exactly as the organisers' slide 7 defines them (plan units are metres here)."""
import pytest

from loopwright.validate.score import interactions, ring_metrics


def ring(*paths):
    return {"legs": [{"path": [list(p) for p in path]} for path in paths]}


def test_cable_length_includes_the_return_leg():
    r = ring([(0, 0), (4, 0)], [(4, 0), (4, 2)], [(4, 2), (1, 2)], [(1, 2), (1, 0), (0, 0)])
    assert ring_metrics(r, 1.0)[0] == pytest.approx(12.0)  # 4 + 2 + 3 + 3


def test_a_retraced_stretch_counts_each_time_it_is_run_and_as_overlap():
    r = ring([(0, 0), (3, 0)], [(3, 0), (0, 0)])
    length, bends = ring_metrics(r, 1.0)
    assert length == pytest.approx(6.0)                    # 3 m out + 3 m back
    assert bends == 2                                       # a reversal at the node and one at the hub
    assert interactions([r], 1.0)[1] == pytest.approx(3.0)  # the stretch is covered twice


def test_cables_meeting_in_the_open_cross_once():
    a, b = ring([(0, 1), (4, 1)]), ring([(2, 0), (2, 3)])
    assert interactions([a, b], 1.0)[0] == 1


def test_legs_meeting_at_a_node_do_not_cross():
    r = ring([(0, 0), (2, 0)], [(2, 0), (2, 2)])
    assert interactions([r], 1.0)[0] == 0


def test_a_ring_crossing_itself_counts():
    r = ring([(0, 1), (4, 1)], [(4, 1), (4, 3), (2, 3), (2, 0), (1, 0)])
    assert interactions([r], 1.0)[0] == 1


def test_three_cables_through_one_point_count_once():
    rings = [ring([(0, 1), (4, 1)]), ring([(2, 0), (2, 3)]), ring([(2, 3), (2, 0)])]
    assert interactions(rings, 1.0)[0] == 1


def test_overlap_is_the_length_on_the_same_line():
    a, b = ring([(0, 0), (4, 0)]), ring([(2, 0), (6, 0)])
    assert interactions([a, b], 1.0)[1] == pytest.approx(2.0)


def test_parallel_runs_on_different_lines_do_not_overlap():
    a, b = ring([(0, 0), (4, 0)]), ring([(0, 0.01), (4, 0.01)])
    assert interactions([a, b], 1.0) == (0, 0.0)


def test_lines_within_1_mm_are_the_same_line():
    a, b = ring([(0, 0), (4, 0)]), ring([(0, 0.0005), (4, 0.0005)])
    assert interactions([a, b], 1.0)[1] == pytest.approx(4.0)


def test_a_stretch_covered_by_k_legs_counts_k_minus_1_times():
    rings = [ring([(0, 0), (3, 0)]), ring([(3, 0), (0, 0)]), ring([(0, 0), (3, 0)])]
    assert interactions(rings, 1.0)[1] == pytest.approx(6.0)


def test_each_turn_is_one_bend_and_straight_through_is_none():
    assert ring_metrics(ring([(0, 0), (2, 0), (2, 1), (4, 1)]), 1.0)[1] == 2
    # A rectangle: corners inside legs, at a node and at the hub each count; straight through N1 does not.
    r = ring([(0, 0), (2, 0)], [(2, 0), (4, 0), (4, 2)], [(4, 2), (0, 2), (0, 0)])
    assert ring_metrics(r, 1.0)[1] == 4


def test_a_jog_shorter_than_1_mm_is_no_bend():
    assert ring_metrics(ring([(0, 0), (2, 0), (2, 0.0004), (4, 0.0004)]), 1.0)[1] == 0


def test_the_scale_converts_the_tolerance():
    # 1 plan unit = 1 cm: a 0.05-unit jog is 0.5 mm, inside the tolerance.
    assert ring_metrics(ring([(0, 0), (200, 0), (200, 0.05), (400, 0.05)]), 0.01) == (pytest.approx(4.0, abs=1e-3), 0)
