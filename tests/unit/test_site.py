"""The product site's generated parts: dark plan drawings, numbers from bench/, data.js and assets."""
import json
import re

import pytest

from loopwright.charts import extra_hubs_chart, runtime_chart
from loopwright.config import DEFAULT
from loopwright.io.sketch import build_plan
from loopwright.results import summarize
from loopwright.site import RINGS, WALL, build_site, label_spot, plan_svg, site_numbers
from loopwright.solve import solve


def square(x0, y0, x1, y1):
    return [[x0, y0], [x1, y0], [x1, y1], [x0, y1]]


FLAT = build_plan([{"type": "living", "polygon": square(0, 0, 6, 6)},
                   {"type": "bedroom", "polygon": square(6, 0, 11, 5)},
                   {"type": "kitchen", "polygon": square(0, 6, 4, 10)}], doors=[(0, 1), (0, 2)])


def row(i, status="valid", hubs=2, lb=2, greedy=3, runtime=0.2):
    return {"id": i, "status": status, "hubs": hubs, "hub_lower_bound": lb, "hubs_greedy": greedy, "length_m": 20.0,
            "bends": 8, "crossings": 0, "overlap_m": 0.0, "J": 22.4, "runtime_s": runtime}


def test_a_plan_drawing_tags_every_leg_node_and_hub_for_the_animation():
    out, model = solve(FLAT)
    svg = plan_svg(model, out)
    legs = re.findall(r'<path class="leg"[^>]*data-ring="(H\d+)"[^>]*data-step="(\d+)"', svg)
    assert len(legs) == sum(len(r["legs"]) for r in out["rings"])
    assert len(re.findall(r'class="node"', svg)) == len(out["nodes"])
    assert len(re.findall(r'class="hub"', svg)) == len(out["hubs"])
    assert svg.startswith("<svg") and 'viewBox="' in svg


def test_a_plan_drawing_is_self_contained():
    out, model = solve(FLAT)
    svg = plan_svg(model, out)
    assert "<script" not in svg and "href" not in svg
    assert re.findall(r"https?://[^\"]+", svg) == ["http://www.w3.org/2000/svg"]


def luminance(hex_colour):
    def channel(c):
        c /= 255
        return c / 12.92 if c <= 0.04045 else ((c + 0.055) / 1.055) ** 2.4
    r, g, b = (int(hex_colour[i:i + 2], 16) for i in (1, 3, 5))
    return 0.2126 * channel(r) + 0.7152 * channel(g) + 0.0722 * channel(b)


def test_walls_stay_quieter_than_every_cable_colour():
    assert luminance(WALL) < min(luminance(c) for c in RINGS)


def test_markers_are_drawn_about_their_own_centre_so_the_page_can_scale_them():
    out, model = solve(FLAT)
    svg = plan_svg(model, out)
    nodes = re.findall(r'<g class="node"[^>]*transform="translate\(-?[\d.]+ -?[\d.]+\)"><g class="mark"><circle r="7" '
                       r'fill="currentColor"', svg)
    hubs = re.findall(r'<g class="hub"[^>]*transform="translate\(-?[\d.]+ -?[\d.]+\)"><g class="mark"><rect ', svg)
    assert (len(nodes), len(hubs)) == (len(out["nodes"]), len(out["hubs"]))


def test_hub_labels_use_the_site_font_and_keep_a_halo_over_cable():
    out, model = solve(FLAT)
    svg = plan_svg(model, out)
    labels = re.findall(r'<text [^>]*>H\d+</text>', svg)
    assert len(labels) == len(out["hubs"])
    assert all('font-family="Outfit' in s and 'paint-order="stroke"' in s for s in labels)


def test_a_hub_label_moves_off_a_node_on_its_right():
    free = label_spot((100, 100), nodes=[], legs=[])
    blocked = label_spot((100, 100), nodes=[(120, 100)], legs=[])
    assert free[2] == "start" and free[0] > 100
    assert blocked[2] != "start"


def test_a_hub_label_prefers_a_side_without_cable():
    spot = label_spot((100, 100), nodes=[], legs=[[(100, 100), (160, 100)]])
    assert spot[2] != "start"


def test_site_numbers_come_from_the_batch_records(tmp_path):
    rows = [row(1), row(2, hubs=3), row(3, status="infeasible", hubs=1, lb=1)]
    (tmp_path / "test-split.jsonl").write_text("\n".join(json.dumps(r) for r in rows), encoding="utf-8")
    (tmp_path / "latency-test.jsonl").write_text("\n".join(json.dumps(row(i, runtime=t)) for i, t in enumerate([0.1, 0.2, 0.3, 0.4, 1.0])),
                                                 encoding="utf-8")
    n = site_numbers(tmp_path)
    s = summarize(rows)
    assert (n["plans"], n["feasible"], n["valid"], n["hubs"], n["lower_bound"], n["greedy"]) == \
        (s["plans"], s["feasible"], s["valid"], s["hubs"], s["lower_bound"], s["greedy"])
    assert n["at_bound"] == 1
    assert (n["p50_s"], n["p95_s"]) == (0.3, 0.4)


def test_build_site_writes_the_data_file_and_the_assets(tmp_path):
    bench = tmp_path / "bench"
    bench.mkdir()
    (bench / "test-split.jsonl").write_text(json.dumps(row(1)), encoding="utf-8")
    (bench / "latency-test.jsonl").write_text(json.dumps(row(1)), encoding="utf-8")
    site = tmp_path / "site"
    build_site(site, {"hero": (FLAT, DEFAULT)}, bench)
    text = (site / "data.js").read_text(encoding="utf-8")
    assert text.startswith("window.LOOPWRIGHT = ")
    data = json.loads(text[len("window.LOOPWRIGHT = "):].rstrip().rstrip(";"))
    assert data["numbers"]["valid"] == 1
    assert data["drawings"]["hero"]["svg"].startswith("<svg") and data["drawings"]["hero"]["hubs"] == 1
    assert (site / "assets" / "hero.svg").exists()
    assert (site / "assets" / "extra-hubs.svg").exists() and (site / "assets" / "runtime.svg").exists()


def test_the_data_file_carries_the_charts_inline_the_version_and_the_greedy_count(tmp_path):
    import loopwright

    bench = tmp_path / "bench"
    bench.mkdir()
    (bench / "test-split.jsonl").write_text(json.dumps(row(1)), encoding="utf-8")
    data = build_site(tmp_path / "site", {"hero": (FLAT, DEFAULT)}, bench)
    assert data["charts"]["extra_hubs"].startswith("<svg") and data["charts"]["runtime"].startswith("<svg")
    assert data["version"] == loopwright.__version__
    out, _ = solve(FLAT)
    assert data["drawings"]["hero"]["greedy"] == out["metrics"]["hubs_greedy"]


def test_charts_have_a_dark_theme_for_the_site():
    rows = [row(1), row(2, hubs=3)]
    dark = extra_hubs_chart(rows, theme="dark")
    assert 'fill="#000000"' in dark and "#0AA5C8" in dark and "#6A7DFF" in dark
    assert 'fill="#000000"' in runtime_chart([0.1, 0.2, 0.3], theme="dark")
    assert 'fill="#FFFFFF"' in extra_hubs_chart(rows)  # light stays the default


@pytest.mark.dataset
def test_the_site_command_builds_every_drawing_from_real_plans(tmp_path):
    from loopwright.cli import main
    from tests.conftest import DATA

    bench = tmp_path / "bench"
    bench.mkdir()
    (bench / "test-split.jsonl").write_text(json.dumps(row(1)), encoding="utf-8")
    assert main(["site", "--out", str(tmp_path / "site"), "--bench", str(bench), "--data", str(DATA)]) == 0
    data = json.loads((tmp_path / "site" / "data.js").read_text(encoding="utf-8")[len("window.LOOPWRIGHT = "):].rstrip().rstrip(";"))
    assert set(data["drawings"]) == {"hero", "rule_strict", "rule_through", "before", "after"}
    assert data["drawings"]["rule_strict"]["hubs"] > data["drawings"]["rule_through"]["hubs"]
    assert data["drawings"]["after"]["J"] < data["drawings"]["before"]["J"]
