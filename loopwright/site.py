"""The product site's generated parts.

`build_site` solves the site's plans and draws each as an isometric scale model
(`loopwright.figure`), then writes them, the charts, the solver's settings and the
headline figures from the batch records into the site folder: `data.js` for the page's
scripts, and `assets/` for drawings that also open on their own. The page is hand-written.
"""
import json
import pathlib
from dataclasses import asdict

from loopwright import __version__
from loopwright.batch import p50_p95
from loopwright.charts import extra_hubs_chart, runtime_chart
from loopwright.config import DEFAULT
from loopwright.figure import model_svg
from loopwright.results import load_rows, summarize
from loopwright.solve import solve

SPLITS = ("test", "val", "augmented", "train")
FEASIBLE = ("valid", "invalid", "crash")


def _rows(bench_dir):
    rows = []
    for split in SPLITS:
        path = pathlib.Path(bench_dir) / f"{split}-split.jsonl"
        if path.exists():
            rows += load_rows(path)
    return rows


def site_numbers(bench_dir):
    """Headline figures over every split's batch records; timing from the one-process run."""
    rows = _rows(bench_dir)
    s = summarize(rows)
    latency = pathlib.Path(bench_dir) / "latency-test.jsonl"
    timed = load_rows(latency) if latency.exists() else rows
    p50, p95 = p50_p95([r["runtime_s"] for r in timed]) if timed else (0.0, 0.0)
    at_bound = sum(1 for r in rows if r["status"] in FEASIBLE and r["hubs"] == r["hub_lower_bound"])
    return {"plans": s["plans"], "feasible": s["feasible"], "valid": s["valid"], "hubs": s["hubs"],
            "lower_bound": s["lower_bound"], "greedy": s["greedy"], "at_bound": at_bound,
            "length_m": s["length_m"], "J": s["J"], "p50_s": p50, "p95_s": p95}


def build_site(site_dir, drawings, bench_dir):
    """Write site/data.js and site/assets/. `drawings` is {name: (plan, settings, figure options)};
    the figure styles come from site/figure.css, embedded in each drawing written to assets/."""
    site, assets = pathlib.Path(site_dir), pathlib.Path(site_dir) / "assets"
    assets.mkdir(parents=True, exist_ok=True)
    css = (site / "figure.css").read_text(encoding="utf-8")
    drawn = {}
    for name, (plan, settings, options) in drawings.items():
        out, model = solve(plan, settings)
        svg, meta = model_svg(model, out, **options)
        start = svg.index(">") + 1
        (assets / f"{name}.svg").write_text(f"{svg[:start]}<style>{css}</style>{svg[start:]}", encoding="utf-8")
        m = out["metrics"]
        drawn[name] = {"svg": svg, "plan": out["plan_id"], "hubs": m["hubs"], "lower_bound": m["hub_lower_bound"],
                       "greedy": m["hubs_greedy"], "length_m": m["length_m"], "bends": m["bends"],
                       "crossings": m["crossings"], "overlap_m": m["overlap_m"], "J": m["J"],
                       "valid": out["validation"]["valid"]}
        if options.get("live"):
            drawn[name]["rings"] = meta["rings"]
    rows = _rows(bench_dir)
    latency = pathlib.Path(bench_dir) / "latency-test.jsonl"
    times = [r["runtime_s"] for r in (load_rows(latency) if latency.exists() else rows)]
    charts = {"extra_hubs": extra_hubs_chart(rows, theme="paper"), "runtime": runtime_chart(times, theme="paper")}
    (assets / "extra-hubs.svg").write_text(charts["extra_hubs"], encoding="utf-8")
    (assets / "runtime.svg").write_text(charts["runtime"], encoding="utf-8")
    data = {"version": __version__, "numbers": site_numbers(bench_dir), "drawings": drawn, "charts": charts,
            "settings": asdict(DEFAULT)}
    (site / "data.js").write_text("window.LOOPWRIGHT = " + json.dumps(data, ensure_ascii=False) + ";\n", encoding="utf-8")
    return json.loads(json.dumps(data))
