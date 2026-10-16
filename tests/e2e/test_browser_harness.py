import pytest

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
