"""The demo app in a browser, against a real local server, on its own and as the site's playground."""
import pathlib
import socket
import threading
import time

import pytest

uvicorn = pytest.importorskip("uvicorn", reason="install the serve extra")

from loopwright.api.app import create_app  # noqa: E402

pytestmark = pytest.mark.e2e

SITE = pathlib.Path(__file__).resolve().parents[2] / "site"


def start_server(data_path, site_dir=None):
    with socket.socket() as s:
        s.bind(("127.0.0.1", 0))
        port = s.getsockname()[1]
    server = uvicorn.Server(uvicorn.Config(create_app(data_path=data_path, site_dir=site_dir), host="127.0.0.1", port=port, log_level="warning"))
    thread = threading.Thread(target=server.run, daemon=True)
    thread.start()
    deadline = time.time() + 10
    while not server.started and time.time() < deadline:
        time.sleep(0.05)
    return server, thread, f"http://127.0.0.1:{port}/"


@pytest.fixture(scope="module")
def app_url():
    server, thread, url = start_server(None)
    yield url
    server.should_exit = True
    thread.join(5)


@pytest.fixture
def page(browser, app_url):
    page = browser.new_page(viewport={"width": 1400, "height": 1000})
    errors = []
    page.on("pageerror", lambda e: errors.append(str(e)))
    page.on("console", lambda m: errors.append(m.text) if m.type == "error" else None)
    page.goto(app_url)
    page.wait_for_load_state("networkidle")
    yield page
    assert errors == []
    page.close()


def metric(page, name):
    return page.locator(f'[data-metric="{name}"] b').inner_text()


def wait_metric(page, name, value):
    page.wait_for_function(
        "([n, v]) => { const e = document.querySelector(`[data-metric='${n}'] b`); return e && e.textContent.startsWith(v); }",
        arg=[name, value], timeout=15000)


def drag_room(page, x0, y0, x1, y1):
    """Drag on the drawing grid from (x0, y0) to (x1, y1), in metres."""
    to_screen = """([x, y]) => { const svg = document.getElementById('plan'); const p = svg.createSVGPoint();
                    p.x = x; p.y = y; const s = p.matrixTransform(svg.getScreenCTM()); return [s.x, s.y]; }"""
    a, b = page.evaluate(to_screen, [x0, y0]), page.evaluate(to_screen, [x1, y1])
    page.mouse.move(*a)
    page.mouse.down()
    page.mouse.move((a[0] + b[0]) / 2, (a[1] + b[1]) / 2)
    page.mouse.move(*b)
    page.mouse.up()


def draw_and_solve(page, door=True):
    assert page.locator("#tab-draw").get_attribute("aria-selected") == "true"  # no dataset: the app opens on Draw
    drag_room(page, 0, 0, 6, 6)
    drag_room(page, 6, 0, 10, 6)
    if door:
        page.locator("#draw-doors input[type=checkbox]").check()
    page.click("#draw-solve")
    page.wait_for_selector('[data-metric="hubs"]')


def click_on(page, selector):
    """Click a point on an SVG shape's outline (its midpoint), not its bounding box."""
    x, y = page.evaluate("""(sel) => { const e = document.querySelector(sel); const svg = document.getElementById('plan');
        let p; if (e.getTotalLength) { const q = e.getPointAtLength(e.getTotalLength() / 2); p = svg.createSVGPoint(); p.x = q.x; p.y = q.y; }
        else { const b = e.getBBox(); p = svg.createSVGPoint(); p.x = b.x + b.width / 2; p.y = b.y + b.height / 2; }
        const s = p.matrixTransform(svg.getScreenCTM()); return [s.x, s.y]; }""", selector)
    page.mouse.click(x, y)


def longest_leg(page, ring):
    """The number of the ring's longest leg: the easiest one to click, clear of nodes and labels."""
    return page.evaluate("""(r) => { let best = null, len = -1;
        for (const e of document.querySelectorAll(`[data-hit-ring="${r}"]`)) {
            const l = e.getTotalLength(); if (l > len) { len = l; best = e.dataset.hitLeg; } }
        return best; }""", ring)


@pytest.mark.parametrize("link, check", [
    ("#upload", ("#tab-upload", "aria-selected")),
    ("#dxf", ("#tab-upload", "aria-selected")),
    ("#draw", ("#tab-draw", "aria-selected")),
    ("#cut", ("#mode-cut", "aria-pressed")),
    ("#edit", ("#mode-edit", "aria-pressed")),
])
def test_a_link_opens_the_app_in_that_mode(browser, app_url, link, check):
    page = browser.new_page(viewport={"width": 1400, "height": 1000})
    page.goto(app_url + link)
    page.wait_for_load_state("networkidle")
    selector, attribute = check
    page.wait_for_function("([s, a]) => document.querySelector(s).getAttribute(a) === 'true'", arg=[selector, attribute],
                           timeout=5000)
    page.close()


def test_only_the_chosen_source_pane_shows(page):
    visible = lambda: [p for p in ("id", "upload", "draw") if page.locator(f"#pane-{p}").is_visible()]
    assert visible() == ["draw"]
    page.click("#tab-upload")
    assert visible() == ["upload"]
    assert page.locator("#edit-panel").is_hidden() and page.locator("#cut-panel").is_hidden()


def test_drawing_two_rooms_with_a_door_gives_one_hub(page):
    draw_and_solve(page)
    wait_metric(page, "hubs", "1")
    assert "1 hub" in page.locator("#explain").inner_text()
    assert page.locator("#rules li").count() == 17
    assert page.locator(".leg").count() == 3


def test_without_the_door_the_rooms_need_two_hubs(page):
    draw_and_solve(page, door=False)
    wait_metric(page, "hubs", "2")


def test_removing_the_door_in_edit_mode_then_undo(page):
    draw_and_solve(page)
    wait_metric(page, "hubs", "1")
    page.click("#mode-edit")
    click_on(page, '[data-door="0"]')
    wait_metric(page, "hubs", "2")
    page.click("#undo")
    wait_metric(page, "hubs", "1")


def test_changing_a_room_type_from_the_edit_panel(page):
    draw_and_solve(page)
    wait_metric(page, "hubs", "1")
    page.click("#mode-edit")
    page.select_option("#edit-room", "bedroom_0")
    page.select_option("#edit-type", "bathroom")
    page.click("#apply-type")
    page.wait_for_function("() => document.querySelectorAll('[data-node]').length === 1", timeout=15000)


def test_cutting_a_leg_keeps_every_device_fed(page):
    draw_and_solve(page)
    wait_metric(page, "hubs", "1")
    page.click("#mode-cut")
    click_on(page, f'[data-hit-ring="H1"][data-hit-leg="{longest_leg(page, "H1")}"]')
    summary = page.locator("[data-cut-summary]")
    summary.wait_for(timeout=10000)
    assert "No device lost" in summary.inner_text()
    assert page.locator(".leg.cut").count() == 1
    assert "N" in page.locator("#cut").inner_text()


def test_importing_a_plan_image(page, tmp_path):
    from tests.unit.test_import_image import M_PER_PX, plan_image

    img = tmp_path / "plan.png"
    img.write_bytes(plan_image())
    page.click("#tab-upload")
    page.set_input_files("#file", str(img))
    page.fill("#m-per-px", str(M_PER_PX))
    page.click("#import")
    page.wait_for_selector('[data-metric="hubs"]', timeout=20000)
    wait_metric(page, "hubs", "1")
    assert not page.locator("#notes-panel").is_hidden()
    assert "guesses" in page.locator("#notes").inner_text()


def test_installer_pack_opens_in_a_new_window(page):
    draw_and_solve(page)
    wait_metric(page, "hubs", "1")
    with page.expect_popup() as popup:
        page.click("#installer")
    pack = popup.value
    pack.wait_for_selector("#addresses", timeout=15000)
    assert pack.locator("#addresses tbody tr").count() == 2
    pack.close()


@pytest.mark.dataset
def test_zone_rule_switch_on_plan_16448(browser):
    from tests.conftest import DATA

    server, thread, url = start_server(str(DATA))
    try:
        page = browser.new_page(viewport={"width": 1400, "height": 1000})
        page.goto(url)
        page.wait_for_load_state("networkidle")
        page.fill("#plan-id", "16448")
        page.click("#load-id")
        page.wait_for_selector('[data-metric="hubs"]', timeout=60000)
        wait_metric(page, "hubs", "4")
        page.select_option("#zone-rule", "through_rooms")
        wait_metric(page, "hubs", "2")
        assert page.locator(".room.flag").count() == 0
        page.close()
    finally:
        server.should_exit = True
        thread.join(5)


@pytest.fixture(scope="module")
def playground_url():
    server, thread, url = start_server(None, SITE)
    yield url + "app/"
    server.should_exit = True
    thread.join(5)


def test_the_playground_shows_the_design_as_the_sites_scale_model(browser, playground_url):
    page = browser.new_page(viewport={"width": 1400, "height": 1000})
    errors = []
    page.on("pageerror", lambda e: errors.append(str(e)))
    page.on("console", lambda m: errors.append(m.text) if m.type == "error" else None)
    page.goto(playground_url)
    page.wait_for_load_state("networkidle")
    assert page.locator(".top .title").inner_text() == "Playground"
    assert page.locator('.links a[href="/"]').count() == 1 and page.locator(".links .gear").get_attribute("href") == "/settings.html"
    draw_and_solve(page)
    page.click("#view-model")
    page.wait_for_selector("#model svg.live")
    assert page.locator("#canvas").is_hidden() and page.locator("#model-figure").is_visible()
    page.wait_for_selector("html[data-model='live']")
    page.wait_for_selector("#model .socket.fed", timeout=10000)
    page.click("#model-figure [data-cut]")
    assert page.locator("#model .tb.joint.cut").count() == 1
    page.evaluate("document.querySelector('#model svg').dataset.first = '1'")
    page.select_option("#zone-rule", "through_rooms")  # re-solved: a new model replaces the old one
    page.wait_for_function("() => { const s = document.querySelector('#model svg'); return s && !s.dataset.first; }")
    assert page.locator("#model svg").count() == 1
    page.click("#model-figure [data-cut]")  # one cut, not one per model ever shown
    assert page.locator("#model .tb.joint.cut").count() == 1
    page.click("#view-plan")
    assert page.locator("#canvas").is_visible() and page.locator("#model-figure").is_hidden()
    assert errors == []
    page.close()
