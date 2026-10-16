"""The product site in a real browser: it loads clean, the scale model runs its signal and can be cut by
pointer, keyboard or button, the features menu, the settings gear and the How it works answers work, the
comparisons answer the pointer and the keys, the copy buttons work, and it fits a phone. Served over HTTP
the way a static host serves it, once opened straight from disk, and once as the hosted app serves it."""
import functools
import http.server
import json
import pathlib
import threading

import pytest

pytestmark = pytest.mark.e2e

SITE = pathlib.Path(__file__).resolve().parents[2] / "site"
DATA = json.loads((SITE / "data.js").read_text(encoding="utf-8")[len("window.LOOPWRIGHT = "):].rstrip().rstrip(";"))
FEATURES = {"edit": "Edit a plan, re-solve live", "cut": "Cut-the-cable simulation",
            "installer": "Installer pack + loop resistance", "draw": "Draw a plan from scratch",
            "dxf": "DXF import", "upload": "Photo or PDF upload"}


class _Quiet(http.server.SimpleHTTPRequestHandler):
    def log_message(self, *args):
        pass


@pytest.fixture(scope="module")
def site_url():
    server = http.server.ThreadingHTTPServer(("127.0.0.1", 0), functools.partial(_Quiet, directory=str(SITE)))
    threading.Thread(target=server.serve_forever, daemon=True).start()
    yield f"http://127.0.0.1:{server.server_address[1]}/"
    server.shutdown()
    server.server_close()


@pytest.fixture
def visit(browser, site_url):
    """Open a page of the site in a fresh context; returns the page and a list that collects every problem."""
    contexts = []

    def open_page(path="index.html", url=None, **options):
        context = browser.new_context(**options)
        contexts.append(context)
        page = context.new_page()
        problems = []
        page.on("console", lambda m: problems.append(f"console: {m.text}") if m.type == "error" else None)
        page.on("pageerror", lambda e: problems.append(f"script: {e}"))
        page.on("requestfailed", lambda r: problems.append(f"failed: {r.url}"))
        page.on("response", lambda r: problems.append(f"{r.status}: {r.url}") if r.status >= 400 else None)
        page.goto(url or site_url + path)
        return page, problems

    yield open_page
    for context in contexts:
        context.close()


def whole(v):
    return f"{round(v):,}"


def midpoint(page, selector):
    """The screen point halfway along an SVG path."""
    return page.evaluate("""(sel) => { const e = document.querySelector(sel), svg = e.ownerSVGElement;
        const q = e.getPointAtLength(e.getTotalLength() / 2), p = svg.createSVGPoint(); p.x = q.x; p.y = q.y;
        const s = p.matrixTransform(e.getScreenCTM()); return [s.x, s.y]; }""", selector)


def walk(page):
    """Scroll the whole page in steps, so every lazy image comes near the viewport and loads."""
    page.evaluate("""async () => { for (let y = 0; y < document.body.scrollHeight; y += 600) {
        window.scrollTo(0, y); await new Promise(r => setTimeout(r, 40)); } }""")
    page.wait_for_function("() => [...document.images].every(i => i.complete)", timeout=10000)


def test_both_pages_load_every_asset_without_an_error(visit):
    for path in ("index.html", "settings.html"):
        page, problems = visit(path)
        walk(page)
        broken = page.evaluate("[...document.images].filter(i => !i.complete || !i.naturalWidth).map(i => i.src)")
        assert broken == [] and problems == [], path
        assert page.evaluate("""document.fonts.check('700 16px Outfit') && document.fonts.check('600 16px "Instrument Sans"')""")


def test_the_model_runs_a_signal_round_the_ring_and_lights_each_socket(visit):
    page, problems = visit()
    page.locator("#model").scroll_into_view_if_needed()
    page.wait_for_selector("html[data-model='live']")
    page.wait_for_function("() => [...document.querySelectorAll('#model .core')].some(c => c.style.visibility === 'visible')",
                           timeout=5000)
    page.wait_for_selector("#model .socket.fed", timeout=8000)
    readout = page.locator("#fig-1 [data-readout]")
    page.wait_for_function("() => /H1 signal at [0-9.]+ of [0-9.]+ m|H1 ring closed/.test(document.querySelector('#fig-1 [data-readout]').textContent)",
                           timeout=8000)
    assert "41.5" in readout.inner_text() or "closed" in readout.inner_text()
    assert problems == []


def test_cutting_a_leg_by_clicking_it_feeds_every_socket_from_both_ends(visit):
    page, problems = visit()
    page.locator("#model").scroll_into_view_if_needed()
    page.wait_for_selector("html[data-model='live']")
    page.mouse.click(*midpoint(page, '#model .hit[data-ring="H1"][data-leg="2"]'))
    assert page.locator('#model .tb.joint.cut[data-ring="H1"][data-leg="2"]').count() == 1
    assert "Every socket is still fed" in page.locator("#model-live").inner_text()
    stops = len(DATA["drawings"]["hero"]["rings"][0]["stops"])
    page.wait_for_function(f"() => document.querySelector('#fig-1 [data-readout]').textContent === 'H1 leg 2 cut, {stops} of {stops} sockets fed'",
                           timeout=10000)
    page.mouse.click(*midpoint(page, '#model .hit[data-ring="H1"][data-leg="2"]'))
    assert page.locator("#model .tb.joint.cut").count() == 0
    assert problems == []


def test_the_keyboard_picks_a_leg_cuts_it_and_rejoins_every_leg(visit):
    page, _ = visit()
    page.focus("#model")
    page.keyboard.press("ArrowRight")
    assert page.locator("#model .tb.on").count() > 0
    page.keyboard.press("Enter")
    assert page.locator("#model .tb.joint.cut").count() == 1
    assert page.locator("[data-cut]").get_attribute("aria-pressed") == "true"
    page.keyboard.press("Escape")
    assert page.locator("#model .tb.joint.cut").count() == 0
    assert page.locator("[data-cut]").get_attribute("aria-pressed") == "false"


def test_the_cut_button_cuts_the_longest_leg_and_rejoins_it(visit):
    page, _ = visit()
    rings = DATA["drawings"]["hero"]["rings"][0]
    ends = [s["s"] for s in rings["stops"]] + [rings["length"]]
    longest = max(range(len(ends)), key=lambda i: ends[i] - (ends[i - 1] if i else 0)) + 1
    button = page.locator("[data-cut]")
    button.click()
    assert page.locator(f'#model .tb.joint.cut[data-ring="H1"][data-leg="{longest}"]').count() == 1
    assert button.inner_text().lower() == "rejoin" and button.get_attribute("aria-pressed") == "true"
    button.click()
    assert page.locator("#model .tb.joint.cut").count() == 0 and button.inner_text().lower() == "cut a leg"


def test_reduced_motion_shows_every_socket_fed_and_still_cuts(visit):
    page, problems = visit(reduced_motion="reduce")
    page.wait_for_selector("html[data-model='still']", timeout=2000)
    sockets = page.locator("#model .socket")
    assert sockets.count() == page.locator("#model .socket.fed").count() > 0
    assert page.evaluate("() => [...document.querySelectorAll('#model .core')].every(c => c.style.visibility !== 'visible')")
    assert page.locator("#fig-1 [data-readout]").inner_text().endswith("sockets fed")
    page.click("[data-cut]")
    assert page.locator("#fig-1 [data-readout]").inner_text().endswith("every socket still fed")
    assert page.locator(".top .wm .loop path").evaluate("p => getComputedStyle(p).animationName") == "none"
    assert problems == []


def test_the_features_menu_lists_every_feature_and_goes_to_it(visit):
    page, problems = visit()
    button = page.locator(".menu-button")
    button.click()
    assert button.get_attribute("aria-expanded") == "true"
    items = page.locator(".menu-list a")
    assert items.count() == len(FEATURES)
    for i, (slug, name) in enumerate(FEATURES.items()):
        assert name in items.nth(i).inner_text()
        assert items.nth(i).get_attribute("href") == f"index.html#{slug}"
    page.keyboard.press("ArrowDown")
    assert page.evaluate("document.activeElement.getAttribute('href')") == "index.html#cut"
    page.keyboard.press("Escape")
    assert button.get_attribute("aria-expanded") == "false" and page.locator(".menu-list").is_hidden()
    button.click()
    page.click("text=DXF import")
    page.wait_for_function("() => location.hash === '#dxf'")
    assert page.locator(".menu-list").is_hidden()
    assert problems == []


def test_each_feature_has_a_button_that_opens_the_app_in_that_mode(visit):
    page, _ = visit()
    for slug, name in FEATURES.items():
        block = page.locator(f"article#{slug}")
        assert block.locator("h3").inner_text() == name
        assert block.locator("a.button").get_attribute("href") == f"http://127.0.0.1:8000/#{slug}"
        block.locator("img").scroll_into_view_if_needed()
        block.locator("img").evaluate("i => i.decode()")
        assert block.locator("img").evaluate("i => i.complete && i.naturalWidth > 0")


def test_the_settings_icon_opens_the_settings_page_with_every_value_from_the_data(visit):
    page, problems = visit()
    page.click(".gear")
    page.wait_for_url("**/settings.html")
    assert page.locator(".gear").get_attribute("aria-current") == "page"
    shown = page.evaluate("Object.fromEntries([...document.querySelectorAll('[data-setting]')].map(e => [e.dataset.setting, e.textContent]))")
    assert set(shown) == set(DATA["settings"])
    for key, value in DATA["settings"].items():
        if isinstance(value, list):
            expected = ", ".join(value)
        elif isinstance(value, bool):
            expected = str(value).lower()
        elif isinstance(value, (int, float)):
            expected = str(int(value)) if float(value).is_integer() else str(value)
        else:
            expected = value
        assert shown[key] == expected, key
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
    assert page.locator("[data-num='version']").inner_text() == DATA["version"]


def test_the_door_rule_switch_swaps_the_model_its_figures_and_its_readout(visit):
    page, problems = visit()
    through = DATA["drawings"]["rule_through"]
    page.click("[data-show='rule_through']")
    assert page.locator("[data-show='rule_through']").get_attribute("aria-pressed") == "true"
    assert page.locator("[data-drawing='rule_through']").evaluate("d => d.classList.contains('on')")
    assert page.locator("[data-drawing='rule_strict']").get_attribute("aria-hidden") == "true"
    assert page.locator("#doors [data-figures] [data-key='hubs']").inner_text() == str(through["hubs"])
    assert page.locator("#fig-2 [data-readout]").inner_text() == f"{through['hubs']} hubs, {through['length_m']:.1f} m"
    page.click("[data-show='rule_strict']")
    assert page.locator("#doors [data-figures] [data-key='hubs']").inner_text() == str(DATA["drawings"]["rule_strict"]["hubs"])
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
    # the top model is opaque, so each side shows one design and never both
    assert page.locator(".wipe .before").evaluate("d => getComputedStyle(d).backgroundColor") != "rgba(0, 0, 0, 0)"


def test_copy_puts_the_commands_for_the_chosen_system_on_the_clipboard(visit):
    page, problems = visit(permissions=["clipboard-read", "clipboard-write"])
    page.click("[data-os-pick='unix']")
    button = page.locator("#run .copy").first
    button.click()
    page.wait_for_selector("#run .copy.done", timeout=3000)
    pasted = page.evaluate("navigator.clipboard.readText()")
    assert pasted.startswith("git clone") and ".venv/bin/loopwright serve" in pasted and "Scripts" not in pasted
    assert problems == []


@pytest.mark.parametrize("width", [1440, 1024, 390])
def test_the_logo_plate_holds_the_whole_wordmark_and_the_claim_fits_the_page(visit, width):
    page, _ = visit(viewport={"width": width, "height": 900})
    page.wait_for_load_state("networkidle")
    plate, mark = page.locator(".top .logo").bounding_box(), page.locator(".top .wm").bounding_box()
    assert plate["x"] <= mark["x"] and mark["x"] + mark["width"] <= plate["x"] + plate["width"]
    claim = page.locator(".claim").bounding_box()
    assert claim["x"] >= 0 and claim["x"] + claim["width"] <= width
    assert page.evaluate("document.scrollingElement.scrollWidth") <= width


@pytest.mark.parametrize("width", [1440, 390])
def test_the_settings_gear_sits_in_the_right_corner_of_the_section_links(visit, width):
    page, _ = visit(viewport={"width": width, "height": 900})
    links, gear = page.locator(".top .links").bounding_box(), page.locator(".top .links .gear").bounding_box()
    assert page.evaluate("document.querySelector('.top .links').lastElementChild.classList.contains('gear')")
    assert abs(gear["x"] + gear["width"] - (links["x"] + links["width"])) <= 1.5
    assert links["x"] + links["width"] >= width - 60  # the header's right-hand pane
    if width == 1440:
        assert page.locator(".top .links a").all_inner_texts()[:4] == ["How it works", "Results", "Run it", "GitHub"]


def answer_height(page, i):
    return page.evaluate(f"document.querySelectorAll('.ask')[{i}].querySelector('.ask-a').getBoundingClientRect().height")


def wait_answer(page, i, opened):
    test = "> 20" if opened else "< 1"
    page.wait_for_function(f"document.querySelectorAll('.ask')[{i}].querySelector('.ask-a').getBoundingClientRect().height {test}")


def test_an_answer_opens_only_while_its_question_is_hovered_or_has_the_focus(visit):
    page, problems = visit(viewport={"width": 1440, "height": 900})
    assert page.locator(".ask").count() == 6
    question = page.locator(".ask-q").nth(2)
    question.scroll_into_view_if_needed()
    page.mouse.move(2, 400)
    page.wait_for_timeout(450)
    assert all(answer_height(page, i) < 1 for i in range(6))
    question.hover()
    wait_answer(page, 2, True)
    assert question.get_attribute("aria-expanded") == "true" and answer_height(page, 1) < 1
    page.mouse.move(2, 400)
    wait_answer(page, 2, False)
    assert question.get_attribute("aria-expanded") == "false"
    question.focus()
    wait_answer(page, 2, True)
    assert problems == []


def test_on_a_touch_screen_a_tap_opens_one_answer_at_a_time(visit):
    page, _ = visit(viewport={"width": 390, "height": 844}, has_touch=True, is_mobile=True)
    assert page.evaluate("matchMedia('(hover: none)').matches")
    questions = page.locator(".ask-q")
    questions.nth(0).scroll_into_view_if_needed()
    questions.nth(0).tap()
    wait_answer(page, 0, True)
    questions.nth(3).tap()
    wait_answer(page, 3, True)
    wait_answer(page, 0, False)
    assert questions.nth(3).get_attribute("aria-expanded") == "true"
    assert questions.nth(0).get_attribute("aria-expanded") == "false"
    questions.nth(3).tap()  # a second tap closes it again
    wait_answer(page, 3, False)
    assert questions.nth(3).get_attribute("aria-expanded") == "false"


def test_served_with_a_hosted_app_the_feature_buttons_open_it(browser, site_url):
    context = browser.new_context()
    page = context.new_page()

    def as_hosted(route):
        response = route.fetch()
        body = response.text().replace("</head>", '<meta name="loopwright:app" content="/app/">\n</head>')
        route.fulfill(response=response, body=body)
    page.route("**/index.html", as_hosted)
    page.goto(site_url + "index.html")
    for slug in FEATURES:
        assert page.locator(f"article#{slug} a.button").get_attribute("href") == f"/app/#{slug}"
    assert page.locator("[data-local]").first.is_hidden()
    context.close()


@pytest.mark.parametrize("width", [1440, 390])
def test_every_card_keeps_its_corner_labels_inside(visit, width):
    page, _ = visit(viewport={"width": width, "height": 900})
    page.wait_for_load_state("networkidle")
    for fig in ("#fig-1", "#fig-2", "#fig-3"):
        plate = page.locator(f"{fig} .plate").bounding_box()
        for corner in page.locator(f"{fig} .corners span").all():  # nested number spans too
            box = corner.bounding_box()
            if not box or not box["width"]:
                continue
            assert plate["x"] <= box["x"] and box["x"] + box["width"] <= plate["x"] + plate["width"] + 0.5, (fig, corner.inner_text())
            assert plate["y"] <= box["y"] and box["y"] + box["height"] <= plate["y"] + plate["height"] + 0.5, (fig, corner.inner_text())


def test_the_site_fits_a_phone_and_the_card_corners_keep_apart(visit):
    page, problems = visit(viewport={"width": 390, "height": 844}, device_scale_factor=2, has_touch=True)
    assert page.evaluate("document.scrollingElement.scrollWidth") <= 390
    page.locator("#fig-1").scroll_into_view_if_needed()
    pill, readout = page.locator("[data-cut]").bounding_box(), page.locator("#fig-1 [data-readout]").bounding_box()
    apart = pill["y"] + pill["height"] <= readout["y"] or readout["y"] + readout["height"] <= pill["y"] or \
        pill["x"] + pill["width"] <= readout["x"]
    assert apart, (pill, readout)
    top = page.locator(".top").bounding_box()
    assert top["height"] < 90  # the header stays on one line
    assert problems == []


def test_the_site_works_opened_straight_from_disk(visit):
    page, problems = visit(url=(SITE / "index.html").as_uri())
    page.wait_for_selector("html[data-model='live']", timeout=5000)
    assert page.locator("[data-drawing] svg").count() == page.locator("[data-drawing]").count() == len(DATA["drawings"])
    assert page.locator("[data-chart] svg").count() == 2
    assert problems == []


def test_without_scripts_every_drawing_and_number_still_shows(visit):
    page, problems = visit(java_script_enabled=False)
    for img in page.locator("img").all():
        img.scroll_into_view_if_needed()
        img.evaluate("i => i.decode()")
    images = page.evaluate("[...document.images].map(i => [i.complete && i.naturalWidth > 0, getComputedStyle(i).visibility])")
    assert images and all(ok and seen == "visible" for ok, seen in images)
    assert page.locator("[data-num='valid']").inner_text() == whole(DATA["numbers"]["valid"])
    assert not page.locator(".switch").first.is_visible() and not page.locator("[data-cut]").is_visible()
    assert page.locator(".menu-fallback").is_visible() and not page.locator(".menu-button").is_visible()
    assert all(p.is_visible() for p in page.locator(".ask-a p").all())  # every answer stays open
    assert problems == []


def test_the_skip_link_is_the_first_stop_and_shows_when_focused(visit):
    page, _ = visit()
    page.keyboard.press("Tab")
    assert page.evaluate("document.activeElement.className") == "skip"
    assert page.locator(".skip").bounding_box()["y"] >= 0
