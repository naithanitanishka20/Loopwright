"""Browser tests for viewer v1 (Playwright).

Skipped when Playwright isn't installed. Uses Playwright's own Chromium if it was
installed with `python -m playwright install chromium`, else the system's Edge or
Chrome, so no browser download is needed on most machines.
"""
import copy

import pytest

sync_api = pytest.importorskip("playwright.sync_api")

from loopwright.config import DEFAULT  # noqa: E402
from loopwright.output.viewer import render_index, render_viewer  # noqa: E402
from loopwright.solve import solve  # noqa: E402
from loopwright.validate.rules import validate  # noqa: E402
from tests.helpers import two_room_plan  # noqa: E402

pytestmark = pytest.mark.e2e


@pytest.fixture(scope="module")
def browser():
    with sync_api.sync_playwright() as p:
        launched = None
        for kwargs in ({}, {"channel": "msedge"}, {"channel": "chrome"}):
            try:
                launched = p.chromium.launch(**kwargs)
                break
            except Exception:
                continue
        if launched is None:
            pytest.skip("no Chromium, Edge or Chrome available to Playwright")
        yield launched
        launched.close()


def open_viewer(browser, tmp_path, out, model):
    page_file = tmp_path / "viewer.html"
    page_file.write_text(render_viewer(model, out), encoding="utf-8")
    page = browser.new_page()
    errors = []
    page.on("pageerror", lambda e: errors.append(str(e)))
    page.goto(page_file.as_uri())
    return page, errors


def test_viewer_draws_every_leg_and_lists_all_fifteen_rules(browser, tmp_path):
    out, model = solve(two_room_plan())
    page, errors = open_viewer(browser, tmp_path, out, model)
    assert errors == []
    assert page.locator("#title").inner_text() == "Plan 1"
    assert page.locator("polyline.leg").count() == sum(len(r["legs"]) for r in out["rings"])
    assert page.locator("#rules li").count() == 15
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


def test_index_links_to_each_plan(browser, tmp_path):
    out, _ = solve(two_room_plan())
    index_file = tmp_path / "index.html"
    index_file.write_text(render_index([out]), encoding="utf-8")
    page = browser.new_page()
    page.goto(index_file.as_uri())
    link = page.locator("a")
    assert link.count() == 1 and link.get_attribute("href") == "1.html"
