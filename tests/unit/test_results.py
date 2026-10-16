import json

from loopwright.cli import main
from loopwright.results import render_results, summarize


def row(i, status="valid", hubs=2, lb=2, greedy=2, length=20.0, bends=8, J=22.4, runtime=0.2):
    return {"id": i, "status": status, "hubs": hubs, "hub_lower_bound": lb, "hubs_greedy": greedy,
            "length_m": length, "bends": bends, "crossings": 0, "overlap_m": 0.0, "J": J, "runtime_s": runtime}


ROWS = [row(1), row(2, hubs=3, greedy=4, length=30.0, bends=10, J=33.0, runtime=0.4),
        row(3, status="invalid", hubs=2, length=99.0, J=99.0, runtime=0.3),
        row(4, status="infeasible", hubs=2, runtime=1.0)]


def test_summary_counts_validity_on_feasible_plans_only():
    s = summarize(ROWS)
    assert (s["plans"], s["feasible"], s["valid"]) == (4, 3, 2)
    assert s["valid_pct"] == 66.7


def test_hub_totals_cover_feasible_plans_and_cable_covers_valid_ones():
    s = summarize(ROWS)
    assert (s["hubs"], s["lower_bound"], s["greedy"], s["above_bound"]) == (7, 6, 8, 1)
    assert (s["length_m"], s["bends"], s["J"]) == (50.0, 18, 55.4)


def test_runtime_percentiles_use_every_plan_and_the_batch_report_definition():
    s = summarize([row(i, runtime=t) for i, t in enumerate([0.1, 0.2, 0.3, 0.4, 1.0])])
    assert (s["p50_s"], s["p95_s"]) == (0.3, 0.4)   # times[n // 2], times[int(0.95 n) - 1]


def test_rendered_table_has_one_row_per_run():
    text = render_results({"test": summarize(ROWS), "val": summarize(ROWS[:2])})
    rows = [line for line in text.splitlines() if line.startswith("| test") or line.startswith("| val")]
    assert len(rows) == 2 and "66.7%" in rows[0] and "100.0%" in rows[1]


def test_results_command_reads_batch_files_and_writes_the_table(tmp_path, capsys):
    a = tmp_path / "test-split.jsonl"
    a.write_text("\n".join(json.dumps(r) for r in ROWS), encoding="utf-8")
    out = tmp_path / "results.md"

    assert main(["results", str(a), "--out", str(out)]) == 0
    assert "| test-split" in out.read_text(encoding="utf-8")


def test_several_runs_also_get_a_row_for_all_their_plans_together(tmp_path, capsys):
    a, b = tmp_path / "test-split.jsonl", tmp_path / "val-split.jsonl"
    a.write_text("\n".join(json.dumps(r) for r in ROWS), encoding="utf-8")
    b.write_text("\n".join(json.dumps(r) for r in ROWS[:2]), encoding="utf-8")
    out = tmp_path / "results.md"

    assert main(["results", str(a), str(b), "--out", str(out)]) == 0
    assert "| all | 6 | 5 | 4 (80.0%) |" in out.read_text(encoding="utf-8")
    assert main(["results", str(a), "--out", str(out)]) == 0
    assert "| all |" not in out.read_text(encoding="utf-8")  # one run needs no total
