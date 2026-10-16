import json
import re

from loopwright.charts import extra_hub_counts, extra_hubs_chart, runtime_chart
from loopwright.cli import main


def row(extra_exact, extra_greedy, status="valid", lb=2, runtime=0.2):
    return {"status": status, "hub_lower_bound": lb, "hubs": lb + extra_exact,
            "hubs_greedy": lb + extra_greedy, "runtime_s": runtime}


ROWS = [row(0, 0), row(0, 1), row(1, 1), row(2, 3), row(3, 5), row(0, 0, status="infeasible"), row(0, 0, status="invalid")]


def test_plans_are_counted_by_hubs_above_the_bound_over_feasible_plans():
    assert extra_hub_counts(ROWS, "hubs") == {"0": 3, "1": 1, "2": 1, "3+": 1}
    assert extra_hub_counts(ROWS, "hubs_greedy") == {"0": 2, "1": 2, "2": 0, "3+": 2}


def bars(svg):
    """{tooltip: top y of the column} for every column."""
    found = re.findall(r'<path class="bar" d="([^"]*)"[^>]*>\s*<title>([^<]*)</title>', svg)
    return {title: min(float(y) for _, y in re.findall(r"([\d.]+),([\d.]+)", d)) for d, title in found}


def test_extra_hubs_chart_draws_one_column_per_bucket_and_series_with_a_tooltip():
    svg = extra_hubs_chart(ROWS)
    found = bars(svg)
    assert len(found) == 8
    assert "Exact: 3 plans with 0 hubs above the bound" in found
    assert "Greedy: 2 plans with 3+ hubs above the bound" in found
    assert "Exact" in svg and "Greedy" in svg  # legend for two series


def test_column_heights_are_proportional_to_their_counts():
    found = bars(extra_hubs_chart(ROWS))
    base = max(found.values())  # the empty bucket sits on the baseline
    tall = base - found["Exact: 3 plans with 0 hubs above the bound"]
    one = base - found["Exact: 1 plan with 1 hub above the bound"]
    assert abs(tall / one - 3) < 0.05


def test_value_labels_in_a_bucket_leave_room_for_five_digit_counts():
    svg = extra_hubs_chart([row(0, 0)] * 12893 + [row(1, 0)] * 820)
    xs = [float(x) for x in re.findall(r'<text x="([\d.]+)"[^>]*font-size="12"[^>]*text-anchor="middle">[\d,]+</text>', svg)]
    assert len(xs) == 2 and abs(xs[1] - xs[0]) >= 44  # "12,893" is about 40 px wide at 12 px


def test_count_axis_ends_on_a_round_tick_close_to_the_tallest_column():
    svg = extra_hubs_chart([row(0, 0)] * 12893)
    ticks = re.findall(r'text-anchor="end">([\d.]+K?)</text>', svg)
    assert ticks == ["0", "4K", "8K", "12K", "16K"]


def test_runtime_axis_stops_near_the_99th_percentile_and_names_the_slowest_plan():
    svg = runtime_chart([0.1] * 98 + [0.2, 30.0])
    ticks = [float(v) for v in re.findall(r'>([\d.]+) s</text>', svg)]
    assert max(ticks) < 1
    assert "slowest plan: 30.0 s" in svg


def test_runtime_chart_marks_p50_and_p95():
    svg = runtime_chart([0.1, 0.2, 0.3, 0.4, 1.0])
    assert svg.count('class="marker"') == 2
    assert "p50 0.30 s" in svg and "p95 0.40 s" in svg
    assert 'class="cdf"' in svg


def test_charts_command_writes_both_figures(tmp_path):
    runs = tmp_path / "test-split.jsonl"
    runs.write_text("\n".join(json.dumps(r) for r in ROWS), encoding="utf-8")
    sample = tmp_path / "latency.jsonl"
    sample.write_text("\n".join(json.dumps(row(0, 0, runtime=v)) for v in (0.1, 0.2, 0.3, 0.4, 1.0)), encoding="utf-8")
    out = tmp_path / "figures"

    assert main(["charts", str(runs), "--runtime", str(sample), "--out", str(out)]) == 0
    assert "Exact: 3 plans with 0 hubs above the bound" in (out / "extra-hubs.svg").read_text(encoding="utf-8")
    runtime = (out / "runtime.svg").read_text(encoding="utf-8")
    assert "Share of 5 plans" in runtime and "single process" in runtime


def test_charts_command_falls_back_to_the_batch_times(tmp_path):
    runs = tmp_path / "test-split.jsonl"
    runs.write_text("\n".join(json.dumps(r) for r in ROWS), encoding="utf-8")

    assert main(["charts", str(runs), "--out", str(tmp_path)]) == 0
    assert "parallel batch" in (tmp_path / "runtime.svg").read_text(encoding="utf-8")
