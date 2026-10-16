import json

import pytest

from loopwright.batch import run_batch
from loopwright.cli import main


def test_config_command_prints_json(capsys):
    assert main(["config"]) == 0
    output = json.loads(capsys.readouterr().out)
    assert output["max_nodes"] == 5


def test_validate_command_reports_bad_json(tmp_path, capsys):
    path = tmp_path / "bad.json"
    path.write_text("[]", encoding="utf-8")

    assert main(["validate", str(path)]) == 1
    output = capsys.readouterr().out
    assert "structure  FAIL  document must be an object" in output
    assert output.rstrip().endswith("INVALID")


def test_batch_command_samples_runs_and_writes_both_reports(tmp_path, monkeypatch, capsys):
    import loopwright.batch as batch
    import loopwright.io.resplan as resplan

    seen = {}
    monkeypatch.setattr(resplan, "load_plans", lambda path: {1: "a", 2: "b", 3: "c"})
    monkeypatch.setattr(batch, "sample", lambda plans, n, seed: (seen.update(n=n, seed=seed), {1: "a"})[1])

    def fake_run(plans, settings, workers):
        seen.update(plans=plans, zone_link=settings.zone_link, workers=workers)
        return [{"id": 1, "status": "valid"}]

    monkeypatch.setattr(batch, "run_batch", fake_run)
    monkeypatch.setattr(batch, "report", lambda rows, settings: "# Batch report\n")
    report = tmp_path / "bench" / "r.md"

    code = main(["batch", "--sample", "1", "--seed", "3", "--workers", "2",
                 "--zone-link", "through_rooms", "--report", str(report)])

    assert code == 0
    assert seen == {"n": 1, "seed": 3, "plans": {1: "a"}, "zone_link": "through_rooms", "workers": 2}
    assert report.read_text(encoding="utf-8") == "# Batch report\n"
    assert json.loads(report.with_suffix(".jsonl").read_text(encoding="utf-8").splitlines()[0])["id"] == 1
    assert "# Batch report" in capsys.readouterr().out


qa/phase3-phase4
@pytest.mark.parametrize("workers", [0, -1, True, 1.5])
def test_run_batch_rejects_invalid_worker_counts(workers):
    with pytest.raises(ValueError, match="workers must be a positive integer"):
        run_batch([], workers=workers)


def test_batch_command_rejects_nonpositive_worker_count_before_loading_data(tmp_path, capsys):
    with pytest.raises(SystemExit) as exc:
        main(["batch", "--workers", "0", "--data", str(tmp_path / "missing.zip")])

    assert exc.value.code == 2
    assert "argument --workers: must be a positive integer" in capsys.readouterr().err


@pytest.mark.parametrize(
    ("command", "option", "value"),
    [
        ("batch", "--sample", "0"),
        ("solve", "--max-nodes", "0"),
        ("solve", "--max-area", "nan"),
    ],
)
def test_commands_reject_invalid_numeric_options_before_loading_data(tmp_path, capsys, command, option, value):
    args = [command, "--data", str(tmp_path / "missing.zip"), option, value]
    if command == "solve":
        args.extend(["--id", "1"])

    with pytest.raises(SystemExit) as exc:
        main(args)

    assert exc.value.code == 2
    assert f"argument {option}:" in capsys.readouterr().err


def test_index_skips_malformed_and_incomplete_designs(tmp_path, capsys):
    (tmp_path / "broken.json").write_text("{", encoding="utf-8")
    (tmp_path / "incomplete.json").write_text(
        json.dumps({"schema": "loopwright/2", "plan_id": "incomplete"}), encoding="utf-8"
    )
    (tmp_path / "incomplete.html").write_text("placeholder", encoding="utf-8")

    assert main(["index", str(tmp_path)]) == 0

    assert "0 plans" in (tmp_path / "index.html").read_text(encoding="utf-8")
    assert "skipped broken.json" in capsys.readouterr().err

def test_solve_writes_design_drawing_viewer_and_installer_pack(tmp_path, capsys):
    from shapely.geometry import box

    plan = {"id": "flat-1", "m_per_unit": 1.0, "wall_depth": 0.1,
            "inner": box(0, 0, 10, 4).wkt, "living": box(0.1, 0.1, 4.95, 3.9).wkt,
            "bedroom": box(5.05, 0.1, 9.9, 3.9).wkt, "door": box(4.95, 1.5, 5.05, 2.4).wkt,
            "wall": box(0, 0, 10, 4).difference(box(0.1, 0.1, 4.95, 3.9)).difference(box(5.05, 0.1, 9.9, 3.9)).wkt}
    src = tmp_path / "flat.json"
    src.write_text(json.dumps(plan), encoding="utf-8")

    assert main(["solve", "--json", str(src), "--out", str(tmp_path / "out")]) == 0

    out = tmp_path / "out"
    assert sorted(p.name for p in out.iterdir()) == [
        "flat-1.html", "flat-1.installer.csv", "flat-1.installer.html", "flat-1.json", "flat-1.svg"]
    rows = (out / "flat-1.installer.csv").read_text(encoding="utf-8").strip().splitlines()
    assert len(rows) == 1 + 2  # header and one row per device
    assert json.loads((out / "flat-1.json").read_text(encoding="utf-8"))["validation"]["valid"] is True


def test_serve_runs_the_app_on_localhost_by_default(monkeypatch, tmp_path):
    import pytest

    uvicorn = pytest.importorskip("uvicorn")
    seen = {}
    monkeypatch.setattr(uvicorn, "run", lambda app, host, port, **kw: seen.update(host=host, port=port, app=app))

    assert main(["serve", "--port", "8123", "--data", str(tmp_path / "missing.zip")]) == 0
    assert (seen["host"], seen["port"]) == ("127.0.0.1", 8123)
    assert seen["app"].title == "Loopwright"
 main


def test_validate_command_rejects_nan_in_json(tmp_path, capsys):
    path = tmp_path / "nan.json"
    path.write_text('{"schema": "loopwright/2", "plan_id": NaN}', encoding="utf-8")

    assert main(["validate", str(path)]) == 1
    assert "invalid JSON" in capsys.readouterr().out


def test_solve_and_validate_commands_use_organiser_json(tmp_path, capsys):
    plan_path = tmp_path / "plan.json"
    plan_path.write_text(json.dumps({
        "id": "cli-demo",
        "area": 40,
        "inner": "POLYGON ((0 0, 10 0, 10 4, 0 4, 0 0))",
        "living": "POLYGON ((0.1 0.1, 4.95 0.1, 4.95 3.9, 0.1 3.9, 0.1 0.1))",
        "bedroom": "POLYGON ((5.05 0.1, 9.9 0.1, 9.9 3.9, 5.05 3.9, 5.05 0.1))",
    }), encoding="utf-8")
    out_dir = tmp_path / "out"

    assert main(["solve", "--json", str(plan_path), "--out", str(out_dir)]) == 0
    solve_output = capsys.readouterr().out
    assert "wrote" in solve_output
    design_path = out_dir / "cli-demo.json"
    assert design_path.exists()
    assert (out_dir / "cli-demo.svg").exists()

    assert main(["validate", str(design_path), "--json", str(plan_path)]) == 0
    assert capsys.readouterr().out.rstrip().endswith("valid")
