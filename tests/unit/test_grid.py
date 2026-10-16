import math
from types import SimpleNamespace

from shapely.geometry import box

from loopwright.routing.grid import GridRouter


def test_grid_router_reports_an_unreachable_stop():
    model = SimpleNamespace(
        m_per_unit=1.0,
        layers={
            "inner": box(0, 0, 10, 2),
            "wall": box(4.5, 0, 5.5, 2),
            "door": None,
        },
    )
    settings = SimpleNamespace(clearance_m=0.0, bend_m=0.5)
    router = GridRouter(model, {"hub": (1.0, 1.0), "node": (9.0, 1.0)}, settings)

    assert router.cost("hub", "node") == math.inf
    assert router.path("hub", "node") is None
