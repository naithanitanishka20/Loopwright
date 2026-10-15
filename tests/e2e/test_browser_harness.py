import pytest


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
