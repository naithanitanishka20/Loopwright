"""Cable passes through a bathroom or stair only when no other route exists (Eval-01 meeting)."""
from shapely.geometry import LineString

from loopwright.config import DEFAULT
from loopwright.io.sketch import build_plan
from loopwright.solve import solve


def square(x0, y0, x1, y1):
    return [[x0, y0], [x1, y0], [x1, y1], [x0, y1]]


def through(out, area):
    return [(r["hub"], leg["n"]) for r in out["rings"] for leg in r["legs"]
            if LineString(leg["path"]).intersection(area).length > 1e-6]


def test_a_ring_takes_the_longer_way_round_rather_than_cross_a_bathroom():
    # Living (left) and bedroom (right) join through the kitchen along the top (12 m between their
    # nodes) or straight through the bathroom between them (7 m).
    plan = build_plan([{"type": "living", "polygon": square(0, 0, 5, 5)},
                       {"type": "bathroom", "polygon": square(5, 0, 7, 5)},
                       {"type": "bedroom", "polygon": square(7, 0, 12, 5)},
                       {"type": "kitchen", "polygon": square(0, 5, 12, 7)}],
                      doors=[(0, 1), (1, 2), (0, 3), (2, 3)])
    out, _ = solve(plan)
    assert out["validation"]["valid"] is True and out["metrics"]["hubs"] == 1
    assert through(out, plan["bathroom"]) == []
    assert not any(d["code"] == "THROUGH_EXCLUDED" for d in out["diagnostics"])


def test_a_bathroom_that_is_the_only_way_through_is_used_and_reported():
    plan = build_plan([{"type": "living", "polygon": square(0, 0, 5, 4)},
                       {"type": "bathroom", "polygon": square(5, 0, 7, 4)},
                       {"type": "bedroom", "polygon": square(7, 0, 12, 4)}],
                      doors=[(0, 1), (1, 2)])
    out, _ = solve(plan, DEFAULT.with_overrides(zone_link="through_rooms"))
    assert out["validation"]["valid"] is True and out["metrics"]["hubs"] == 1
    assert through(out, plan["bathroom"])
    assert any(d["code"] == "THROUGH_EXCLUDED" for d in out["diagnostics"])
