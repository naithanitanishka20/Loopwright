"""Browser tests for viewer v1 (Playwright). The browser comes from tests/e2e/conftest.py."""
import copy

import pytest

from loopwright.config import DEFAULT
from loopwright.output.viewer import render_index, render_viewer
from loopwright.solve import solve
from loopwright.validate.rules import validate
from tests.helpers import two_room_plan

pytestmark = pytest.mark.e2e


def open_viewer(browser, tmp_path, out, model):
    page_file = tmp_path / "viewer.html"
    page_file.write_text(render_viewer(model, out), encoding="utf-8")
    page = browser.new_page()
    errors = []
    page.on("pageerror", lambda e: errors.append(str(e)))
    page.goto(page_file.as_uri())
    return page, errors


def test_viewer_draws_every_leg_and_lists_all_seventeen_rules(browser, tmp_path):
    out, model = solve(two_room_plan())
    page, errors = open_viewer(browser, tmp_path, out, model)
    assert errors == []
    assert page.locator("#title").inner_text() == "Plan 1"
    assert page.locator("polyline.leg").count() == sum(len(r["legs"]) for r in out["rings"])
    assert page.locator("#rules li").count() == 17
    assert page.locator("#rules li.fail").count() == 0
    page.uncheck("#toggle-walls")
    assert page.locator("#layer-walls").is_hidden()
    page.check("#toggle-walls")
    assert page.locator("#layer-walls").is_visible()


def test_clicking_a_failed_rule_highlights_the_failing_leg(browser, tmp_path):
    plan = two_room_plan()
    out, model = solve(plan)
    bad = copy.deepcopy(out)
    leg = bad["rings"][0]["legs"][1]
    leg["path"] = [leg["path"][0], [leg["path"][-1][0], leg["path"][-1][1] + 0.5]]
    bad["validation"] = validate(plan, bad, DEFAULT)
    page, errors = open_viewer(browser, tmp_path, bad, model)
    assert errors == []
    page.click("button[data-rule='V14']")
    highlighted = page.locator("polyline.leg.hl")
    assert highlighted.count() == 1
    assert highlighted.get_attribute("data-leg") == "2"


def test_plan_text_cannot_inject_script(browser, tmp_path):
    out, model = solve(two_room_plan())
    out["plan_id"] = "</script><script>window.pwned = 1</script>"
    page, errors = open_viewer(browser, tmp_path, out, model)
    assert page.evaluate("window.pwned") is None
    assert "</script>" in page.locator("#title").inner_text()


def test_index_metrics_cannot_inject_script(browser, tmp_path):
    out, _ = solve(two_room_plan())
    payload = "<script>window.pwned = 1</script>"
    out["metrics"]["hubs"] = payload
    index_file = tmp_path / "index.html"
    index_file.write_text(render_index([out]), encoding="utf-8")
    page = browser.new_page()
    page.goto(index_file.as_uri())
    assert page.evaluate("window.pwned") is None
    assert page.locator("script").count() == 0
    assert payload in page.locator("tbody").inner_text()


def test_index_links_to_each_plan(browser, tmp_path):
    out, _ = solve(two_room_plan())
    index_file = tmp_path / "index.html"
    index_file.write_text(render_index([out]), encoding="utf-8")
    page = browser.new_page()
    page.goto(index_file.as_uri())
    link = page.locator("a")
    assert link.count() == 1 and link.get_attribute("href") == "1.html"
