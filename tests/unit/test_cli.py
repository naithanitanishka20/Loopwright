import json

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
