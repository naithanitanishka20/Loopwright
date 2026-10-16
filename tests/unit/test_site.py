"""The product site's generated parts: scale-model drawings, numbers from bench/, settings, data.js and assets."""
import json
from dataclasses import asdict

import pytest

import loopwright
from loopwright.charts import extra_hubs_chart, runtime_chart
from loopwright.config import DEFAULT
from loopwright.io.sketch import build_plan
from loopwright.results import summarize
from loopwright.site import build_site, site_numbers
from loopwright.solve import solve


def square(x0, y0, x1, y1):
    return [[x0, y0], [x1, y0], [x1, y1], [x0, y1]]


FLAT = build_plan([{"type": "living", "polygon": square(0, 0, 6, 6)},
                   {"type": "bedroom", "polygon": square(6, 0, 11, 5)},
                   {"type": "kitchen", "polygon": square(0, 6, 4, 10)}], doors=[(0, 1), (0, 2)])


def row(i, status="valid", hubs=2, lb=2, greedy=3, runtime=0.2):
    return {"id": i, "status": status, "hubs": hubs, "hub_lower_bound": lb, "hubs_greedy": greedy, "length_m": 20.0,
            "bends": 8, "crossings": 0, "overlap_m": 0.0, "J": 22.4, "runtime_s": runtime}


def read_data(site):
    text = (site / "data.js").read_text(encoding="utf-8")
    assert text.startswith("window.LOOPWRIGHT = ")
    return json.loads(text[len("window.LOOPWRIGHT = "):].rstrip().rstrip(";"))


@pytest.fixture
def built(tmp_path):
    bench = tmp_path / "bench"
    bench.mkdir()
    (bench / "test-split.jsonl").write_text(json.dumps(row(1)), encoding="utf-8")
    site = tmp_path / "site"
    site.mkdir()
    (site / "figure.css").write_text(".iso-svg{--paper:#000}", encoding="utf-8")
    data = build_site(site, {"hero": (FLAT, DEFAULT, {"live": True}), "still": (FLAT, DEFAULT, {})}, bench)
    return site, data


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


def test_build_site_writes_the_data_file_and_the_drawings(built):
    site, data = built
    assert read_data(site) == data
    assert data["numbers"]["valid"] == 1
    out, _ = solve(FLAT)
    hero = data["drawings"]["hero"]
    assert hero["svg"].startswith("<svg") and hero["hubs"] == len(out["hubs"]) and hero["greedy"] == out["metrics"]["hubs_greedy"]
    assert (site / "assets" / "hero.svg").exists() and (site / "assets" / "still.svg").exists()
    assert (site / "assets" / "extra-hubs.svg").exists() and (site / "assets" / "runtime.svg").exists()


def test_drawings_on_disk_carry_their_styles_and_the_inline_copies_do_not(built):
    site, data = built
    on_disk = (site / "assets" / "hero.svg").read_text(encoding="utf-8")
    assert "<style>.iso-svg{--paper:#000}</style>" in on_disk
    assert "<style>" not in data["drawings"]["hero"]["svg"]


def test_only_the_live_drawing_carries_its_rings_for_the_signal(built):
    _, data = built
    rings = data["drawings"]["hero"]["rings"]
    assert rings and all(r["length"] > 0 and r["stops"] for r in rings)
    assert "rings" not in data["drawings"]["still"]
    assert 'class="iso-svg model"' in data["drawings"]["still"]["svg"]


def test_the_data_file_carries_the_charts_the_version_and_the_settings(built):
    _, data = built
    assert data["charts"]["extra_hubs"].startswith("<svg") and data["charts"]["runtime"].startswith("<svg")
    assert data["version"] == loopwright.__version__
    assert data["settings"] == json.loads(json.dumps(asdict(DEFAULT)))


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
    site = tmp_path / "site"
    site.mkdir()
    (site / "figure.css").write_text("", encoding="utf-8")
    assert main(["site", "--out", str(site), "--bench", str(bench), "--data", str(DATA)]) == 0
    data = read_data(site)
    assert set(data["drawings"]) == {"hero", "rule_strict", "rule_through", "before", "after"}
    assert data["drawings"]["rule_strict"]["hubs"] > data["drawings"]["rule_through"]["hubs"]
    assert data["drawings"]["after"]["J"] < data["drawings"]["before"]["J"]
    assert "rings" in data["drawings"]["hero"]
