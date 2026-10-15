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
    output = json.loads(capsys.readouterr().out)
    assert output["valid"] is False
