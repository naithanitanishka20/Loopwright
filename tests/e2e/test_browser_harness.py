import pytest

<<<<<<< HEAD

@pytest.mark.e2e
def test_playwright_harness_can_render_a_status_page():
    sync_api = pytest.importorskip("playwright.sync_api", reason="install the e2e extra and a Playwright browser")
    try:
        with sync_api.sync_playwright() as playwright:
            browser = playwright.chromium.launch(headless=True)
            page = browser.new_page()
            page.set_content("<main id='status'>Loopwright validator ready</main>")
            assert page.locator("#status").inner_text() == "Loopwright validator ready"
            browser.close()
    except sync_api.Error as exc:
        pytest.skip(f"Playwright browser is not installed: {exc}")
=======
from loopwright.output.overlay import render_svg
from loopwright.solve import solve
from tests.helpers import two_room_plan


@pytest.mark.e2e
def test_playwright_renders_the_loopwright_overlay(browser):
    page = browser.new_page()
    output, model = solve(two_room_plan())
    page.set_content(render_svg(model, output))
    assert page.locator("svg").count() == 1
    assert page.locator("polyline").count() > 0
    assert "H1" in " ".join(page.locator("text").all_text_contents())
    page.close()
>>>>>>> e93d1bc4ec002a5c7592ba84d9672f2712ba5fd4
