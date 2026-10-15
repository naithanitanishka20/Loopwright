import pytest

from loopwright.output.overlay import render_svg
from loopwright.solve import solve
from tests.helpers import two_room_plan

@pytest.mark.e2e
def test_playwright_renders_the_loopwright_overlay():
    sync_api = pytest.importorskip("playwright.sync_api", reason="install the e2e extra and a Playwright browser")
    try:
        with sync_api.sync_playwright() as playwright:
            browser = playwright.chromium.launch(headless=True)
            page = browser.new_page()
            output, model = solve(two_room_plan())
            page.set_content(render_svg(model, output))
            assert page.locator("svg").count() == 1
            assert page.locator("polyline").count() > 0
            assert "H1" in " ".join(page.locator("text").all_text_contents())
            browser.close()
    except sync_api.Error as exc:
        pytest.skip(f"Playwright browser is not installed: {exc}")
