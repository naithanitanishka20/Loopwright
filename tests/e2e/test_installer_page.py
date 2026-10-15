"""The installer pack page in a browser: tables render and the cost estimate follows the inputs."""
import pytest

from loopwright.config import DEFAULT
from loopwright.io.edits import door_parts
from loopwright.io.sketch import build_plan
from loopwright.output.installer import render_installer
from loopwright.solve import solve

pytestmark = pytest.mark.e2e


def stacked_rooms():
    sq = lambda x0, y0, x1, y1: [[x0, y0], [x1, y0], [x1, y1], [x0, y1]]
    return build_plan([{"type": "living", "polygon": sq(0, 0, 6, 6)},
                       {"type": "bedroom", "polygon": sq(0, 6, 6, 12)}], doors=[(0, 1)])


def test_cost_estimate_follows_rate_and_hub_price(browser, tmp_path):
    plan = stacked_rooms()
    design, model = solve(plan, DEFAULT)
    page_file = tmp_path / "installer.html"
    page_file.write_text(render_installer(model, design, door_parts(plan)), encoding="utf-8")
    page = browser.new_page()
    errors = []
    page.on("pageerror", lambda e: errors.append(str(e)))
    page.goto(page_file.as_uri())

    assert page.locator("#schedule tbody tr").count() == 1
    assert page.locator("#addresses tbody tr").count() == 2
    page.fill("#rate", "50")
    page.fill("#hubprice", "1000")
    # 12 m ring + 10 % slack = 13.2 m at 50 per metre, plus one hub at 1000.
    assert page.locator("#total").inner_text() == "1,660"
    assert errors == []
    page.close()
