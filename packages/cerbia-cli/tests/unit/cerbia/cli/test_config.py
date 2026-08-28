from pathlib import Path

import pytest
import typer
from cerbia.cli.config import load_config_from_yaml
from cerbia.core.exceptions import CerbIAConfigError
from rich.console import Console

pytestmark = pytest.mark.unit


def test_load_config_from_yaml_returns_config_when_valid_yaml_mapping_is_provided(tmp_path: Path) -> None:
    path = tmp_path / "config.yaml"
    path.write_text(
        """name: gate
loaders:
  - loader: cerbia.core.loaders.text.TextLoader
scanners:
  - scanner: cerbia.core.scanners.keyword.KeywordScanner
score_aggregator:
  score_aggregator: cerbia.core.score_aggregators.max.MaxScoreAggregator
"""
    )

    result = load_config_from_yaml(path, Console(record=True))

    assert result.name == "gate"
    assert len(result.loaders) == 1


def test_load_config_from_yaml_exits_when_yaml_is_not_a_mapping(tmp_path: Path) -> None:
    path = tmp_path / "config.yaml"
    path.write_text("- item")
    console = Console(record=True)

    with pytest.raises(typer.Exit) as exc_info:
        load_config_from_yaml(path, console)

    assert exc_info.value.exit_code == 2
    assert "invalid configuration" in console.export_text()


def test_load_config_from_yaml_exits_when_configuration_error_is_raised(mocker, tmp_path: Path) -> None:
    path = tmp_path / "config.yaml"
    path.write_text("name: gate")
    console = mocker.Mock()
    mocker.patch("cerbia.cli.config.CerbIAConfig.model_validate", side_effect=CerbIAConfigError("Invalid"))

    with pytest.raises(typer.Exit) as exc_info:
        load_config_from_yaml(path, console)

    assert exc_info.value.exit_code == 2
    console.print.assert_called_once_with(f"[red]Error:[/red] invalid configuration in file: {path}")


def test_load_config_from_yaml_exits_with_actionable_error_when_file_is_missing(tmp_path: Path) -> None:
    path = tmp_path / "missing.yaml"
    console = Console(record=True)

    with pytest.raises(typer.Exit) as exc_info:
        load_config_from_yaml(path, console)

    output = console.export_text()
    assert exc_info.value.exit_code == 2
    assert "not found" in output.lower()
    assert path.name in output


def test_load_config_from_yaml_exits_with_actionable_error_when_path_is_directory(tmp_path: Path) -> None:
    path = tmp_path / "configs"
    path.mkdir()
    console = Console(record=True)

    with pytest.raises(typer.Exit) as exc_info:
        load_config_from_yaml(path, console)

    output = console.export_text()
    assert exc_info.value.exit_code == 2
    assert "directory" in output.lower()
    assert path.name in output


def test_load_config_from_yaml_exits_with_actionable_error_when_file_cannot_be_read(mocker, tmp_path: Path) -> None:
    path = tmp_path / "restricted.yaml"
    console = Console(record=True)
    mocker.patch("builtins.open", side_effect=PermissionError("access denied"))

    with pytest.raises(typer.Exit) as exc_info:
        load_config_from_yaml(path, console)

    output = console.export_text()
    assert exc_info.value.exit_code == 2
    assert "permission denied" in output.lower()
    assert path.name in output


def test_load_config_from_yaml_exits_with_actionable_error_when_yaml_is_malformed(tmp_path: Path) -> None:
    path = tmp_path / "malformed.yaml"
    path.write_text("loaders: [", encoding="utf-8")
    console = Console(record=True)

    with pytest.raises(typer.Exit) as exc_info:
        load_config_from_yaml(path, console)

    output = console.export_text()
    assert exc_info.value.exit_code == 2
    assert "YAML" in output
    assert path.name in output
