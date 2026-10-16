"""The product site in a real browser: it loads clean, the hero draws and finishes, the
comparisons answer the pointer and the keyboard, the copy buttons work, and it fits a phone.

Served over HTTP the way GitHub Pages serves it, and once opened straight from disk.
"""
import functools
import http.server
import json
import pathlib
import threading

import pytest

SITE = pathlib.Path(__file__).resolve().parents[2] / "site"
DATA = json.loads((SITE / "data.js").read_text(encoding="utf-8")[len("window.LOOPWRIGHT = "):].rstrip().rstrip(";"))


class _Quiet(http.server.SimpleHTTPRequestHandler):
    def log_message(self, *args):
        pass


@pytest.fixture(scope="module")
def site_url():
    server = http.server.ThreadingHTTPServer(("127.0.0.1", 0), functools.partial(_Quiet, directory=str(SITE)))
    threading.Thread(target=server.serve_forever, daemon=True).start()
    yield f"http://127.0.0.1:{server.server_address[1]}/index.html"
    server.shutdown()
    server.server_close()


@pytest.fixture
def visit(browser, site_url):
    """Open the site in a fresh context; returns the page and a list that collects every problem."""
    contexts = []

    def open_page(url=None, **options):
        context = browser.new_context(**options)
        contexts.append(context)
        page = context.new_page()
        problems = []
        page.on("console", lambda m: problems.append(f"console: {m.text}") if m.type == "error" else None)
        page.on("pageerror", lambda e: problems.append(f"script: {e}"))
        page.on("requestfailed", lambda r: problems.append(f"failed: {r.url}"))
        page.on("response", lambda r: problems.append(f"{r.status}: {r.url}") if r.status >= 400 else None)
        page.goto(url or site_url)
        return page, problems

    yield open_page
    for context in contexts:
        context.close()


def whole(v):
    return f"{round(v):,}"


def test_the_site_loads_every_asset_without_an_error(visit):
    page, problems = visit()
    page.wait_for_load_state("networkidle")
    broken = page.evaluate("[...document.images].filter(i => !i.complete || !i.naturalWidth).map(i => i.src)")
    assert broken == [] and problems == []
    assert page.evaluate("document.fonts.check('700 16px Outfit')")


def test_the_hero_draws_its_rings_leg_by_leg_and_then_reports_done(visit):
    page, problems = visit()
    page.wait_for_selector("html[data-hero='running']", timeout=5000)
    assert page.locator("[data-drawing='hero'] .node.unlit").count() > 0
    # a node lights when its cable arrives, so partway through some are lit and some are not
    page.wait_for_function("""() => document.documentElement.dataset.hero === 'running'
        && document.querySelector("[data-drawing='hero'] .node.unlit")
        && document.querySelector("[data-drawing='hero'] .node:not(.unlit)")""", timeout=10000)
    page.wait_for_selector("html[data-hero='done']", timeout=15000)
    hero = page.locator("[data-drawing='hero'] svg")
    assert hero.locator(".node.unlit").count() == 0
    assert hero.evaluate("s => [...s.querySelectorAll('.leg')].every(l => !l.style.strokeDasharray)")
    assert hero.locator(".leg").count() == sum(1 for _ in DATA["drawings"]["hero"]["svg"].split('class="leg"')[1:])
    assert problems == []


def test_drawing_it_again_replays_the_hero(visit):
    page, _ = visit()
    page.wait_for_selector("html[data-hero='done']", timeout=15000)
    page.click(".replay")
    page.wait_for_selector("html[data-hero='running']", timeout=3000)
    page.wait_for_selector("html[data-hero='done']", timeout=15000)
    assert page.locator("[data-drawing='hero'] .node.unlit").count() == 0


def test_reduced_motion_shows_the_finished_drawing_at_once(visit):
    page, problems = visit(reduced_motion="reduce")
    page.wait_for_selector("html[data-hero='done']", timeout=1000)
    assert page.locator("[data-drawing='hero'] .node.unlit").count() == 0
    assert page.locator(".wm .loop path").evaluate("p => getComputedStyle(p).animationName") == "none"
    assert not page.locator(".replay").is_visible()
    assert problems == []


def test_the_numbers_on_the_page_come_from_the_data_file(visit):
    page, _ = visit()
    n = DATA["numbers"]
    text = {k: page.locator(f"[data-num='{k}']").first.inner_text() for k in
            ("plans", "valid", "feasible", "infeasible", "hubs", "lower_bound", "greedy", "at_bound", "p50_s")}
    assert text == {"plans": whole(n["plans"]), "valid": whole(n["valid"]), "feasible": whole(n["feasible"]),
                    "infeasible": whole(n["plans"] - n["feasible"]), "hubs": whole(n["hubs"]),
                    "lower_bound": whole(n["lower_bound"]), "greedy": whole(n["greedy"]),
                    "at_bound": whole(n["at_bound"]), "p50_s": f"{n['p50_s']:.2f}"}
    hero = DATA["drawings"]["hero"]
    assert page.locator("[data-fig='hero.hubs']").inner_text() == str(hero["hubs"])
    assert page.locator("[data-fig='hero.length_m']").inner_text() == f"{hero['length_m']:.1f}"
    assert page.locator("[data-num='version']").inner_text() == DATA["version"]


def test_the_door_rule_switch_swaps_the_drawing_and_its_figures(visit):
    page, problems = visit()
    figures = page.locator("#doors [data-figures]")
    page.click("text=Through other rooms")
    assert page.locator("[data-show='rule_through']").get_attribute("aria-pressed") == "true"
    assert page.locator("[data-show='rule_strict']").get_attribute("aria-pressed") == "false"
    assert page.locator("[data-drawing='rule_through']").evaluate("d => d.classList.contains('on')")
    assert page.locator("[data-drawing='rule_strict']").get_attribute("aria-hidden") == "true"
    assert figures.locator("[data-key='hubs']").inner_text() == str(DATA["drawings"]["rule_through"]["hubs"])
    page.click("text=Own doors only")
    assert figures.locator("[data-key='hubs']").inner_text() == str(DATA["drawings"]["rule_strict"]["hubs"])
    assert page.locator("[data-drawing='rule_through']").get_attribute("aria-hidden") == "true"
    assert problems == []


def test_the_before_and_after_wipe_follows_the_pointer_and_the_arrow_keys(visit):
    page, _ = visit()
    wipe = page.locator(".wipe")
    wipe.scroll_into_view_if_needed()
    box = wipe.bounding_box()
    y = box["y"] + box["height"] / 2
    page.mouse.move(box["x"] + box["width"] * 0.2, y)
    page.mouse.down()
    page.mouse.move(box["x"] + box["width"] * 0.8, y, steps=6)
    page.mouse.up()
    assert wipe.evaluate("w => w.style.getPropertyValue('--pos')") == "80%"
    page.focus(".wipe input")
    page.keyboard.press("ArrowLeft")
    assert wipe.evaluate("w => w.style.getPropertyValue('--pos')") == "79%"
    clip = page.locator(".wipe .before").evaluate("d => getComputedStyle(d).clipPath")
    assert "21%" in clip
    # the top drawing is opaque, so each side shows one design and never both
    assert page.locator(".wipe .before").evaluate("d => getComputedStyle(d).backgroundColor") == "rgb(0, 0, 0)"


@pytest.mark.parametrize("width", [1440, 1024, 390])
def test_the_wordmark_fits_beside_the_plan(visit, width):
    page, _ = visit(viewport={"width": width, "height": 900})
    page.wait_for_load_state("networkidle")
    mark = page.locator(".wm").bounding_box()
    column = page.locator(".hero-text").bounding_box()
    assert mark["x"] + mark["width"] <= column["x"] + column["width"] + 1


def test_copy_puts_the_commands_for_the_chosen_system_on_the_clipboard(visit):
    page, problems = visit(permissions=["clipboard-read", "clipboard-write"])
    page.click("[data-os-pick='unix']")
    assert page.locator("#run").get_attribute("data-os-current") == "unix"
    button = page.locator("#run .copy").first
    button.click()
    page.wait_for_selector("#run .copy.done", timeout=3000)
    assert button.inner_text() == "Copied"
    pasted = page.evaluate("navigator.clipboard.readText()")
    assert pasted.startswith("git clone") and ".venv/bin/loopwright serve" in pasted and "Scripts" not in pasted
    page.click("[data-os-pick='windows']")
    button.click()
    page.wait_for_function("navigator.clipboard.readText().then(t => t.includes('Scripts'))", timeout=3000)
    assert ".venv\\Scripts\\loopwright serve" in page.evaluate("navigator.clipboard.readText()")
    assert problems == []


def test_the_site_fits_a_phone_and_keeps_markers_readable(visit):
    page, problems = visit(viewport={"width": 390, "height": 844}, device_scale_factor=2, has_touch=True)
    assert page.evaluate("document.scrollingElement.scrollWidth") <= 390
    page.locator("[data-drawing='hero']").scroll_into_view_if_needed()
    page.wait_for_selector("html[data-hero='done']", timeout=15000)
    node = page.locator("[data-drawing='hero'] .node circle").first.bounding_box()
    assert node["width"] >= 9
    assert page.evaluate("document.scrollingElement.scrollWidth") <= 390
    assert problems == []


def test_the_site_works_opened_straight_from_disk(visit):
    page, problems = visit((SITE / "index.html").as_uri())
    page.wait_for_selector("html[data-hero='done']", timeout=15000)
    assert page.locator("[data-drawing] svg").count() == page.locator("[data-drawing]").count() == len(DATA["drawings"])
    assert page.locator("[data-chart] svg").count() == 2
    assert problems == []


def test_without_scripts_every_drawing_and_number_still_shows(visit):
    page, problems = visit(java_script_enabled=False)
    page.wait_for_load_state("networkidle")
    images = page.evaluate("[...document.images].map(i => [i.complete && i.naturalWidth > 0, getComputedStyle(i).visibility])")
    assert images and all(ok and seen == "visible" for ok, seen in images)
    assert page.locator("[data-num='valid']").inner_text() == whole(DATA["numbers"]["valid"])
    assert not page.locator(".switch").first.is_visible()
    assert problems == []


def test_the_skip_link_is_the_first_stop_and_shows_when_focused(visit):
    page, _ = visit()
    page.keyboard.press("Tab")
    focused = page.evaluate("document.activeElement.className")
    assert focused == "skip"
    assert page.locator(".skip").bounding_box()["y"] >= 0
