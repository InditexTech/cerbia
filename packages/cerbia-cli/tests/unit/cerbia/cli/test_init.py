from importlib import import_module
from types import ModuleType

import pytest
from cerbia.cli import app
from typer.testing import CliRunner

pytestmark = pytest.mark.unit


def test_package_is_importable() -> None:
    # Given: the CLI package import path
    package_name = "cerbia.cli"

    # When: importing the package
    module: ModuleType = import_module(package_name)

    # Then: the CLI package is available at its public import path
    assert module.__name__ == package_name


def test_root_help_lists_registered_commands() -> None:
    # Given: the root CerbIA application
    runner = CliRunner()

    # When: requesting root help
    result = runner.invoke(app, ["--help"])

    # Then: both public commands are registered
    assert result.exit_code == 0
    assert "scan" in result.output
    assert "validate" in result.output


def test_unknown_command_reports_usage_error() -> None:
    # Given: the root CerbIA application
    runner = CliRunner()

    # When: invoking an unknown command
    result = runner.invoke(app, ["unknown-command"])

    # Then: the CLI rejects it with actionable usage or error output
    assert result.exit_code != 0
    assert "Usage:" in result.output or "Error:" in result.output
