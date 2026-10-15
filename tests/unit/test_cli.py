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


def test_validate_command_rejects_nan_in_json(tmp_path, capsys):
    path = tmp_path / "nan.json"
    path.write_text('{"schema": "loopwright/2", "plan_id": NaN}', encoding="utf-8")

    assert main(["validate", str(path)]) == 1
    assert "invalid JSON" in capsys.readouterr().out
