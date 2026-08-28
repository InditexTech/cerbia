from io import StringIO

import pytest
from cerbia.cli.validate._ui import render_validation_summary
from cerbia.core.config import CerbIAConfig, LoaderConfig, ScannerConfig, ScoreAggregatorConfig
from cerbia.core.runner import Runner
from rich.console import Console

pytestmark = pytest.mark.unit


class _ScannerStub:
    pass


def test_render_validation_summary_renders_gate_scanner_and_loader_details(mocker) -> None:
    config = _build_config(loaders=[LoaderConfig(loader="test.Loader")])
    runner = mocker.Mock()
    runner.gate.name = "test-gate"
    runner.gate.scanners = [_ScannerStub()]
    output = StringIO()

    render_validation_summary(config, runner, Console(file=output, force_terminal=False, width=120))

    rendered = output.getvalue()
    assert "Config valid" in rendered
    assert "test-gate" in rendered
    assert "_ScannerStub" in rendered
    assert "loaders=yes" in rendered


def test_render_validation_summary_renders_no_loader_status_when_no_loaders_are_configured(mocker) -> None:
    runner = mocker.Mock()
    runner.gate.name = "test-gate"
    runner.gate.scanners = []
    output = StringIO()

    render_validation_summary(_build_config(loaders=[]), runner, Console(file=output, force_terminal=False))

    assert "loaders=no" in output.getvalue()


def _build_config(*, loaders: list[LoaderConfig]) -> CerbIAConfig:
    return CerbIAConfig(
        name="test-gate",
        loaders=loaders,
        scanners=[ScannerConfig(scanner="test.Scanner")],
        score_aggregator=ScoreAggregatorConfig(score_aggregator="test.Aggregator"),
    )


def test_render_validation_summary_reports_real_gate_scanners_and_loader_status() -> None:
    config = CerbIAConfig(
        name="summary-gate",
        loaders=[LoaderConfig(loader="cerbia.core.loaders.text.TextLoader", init_args={"texts": ["input"]})],
        scanners=[ScannerConfig(scanner="cerbia.core.scanners.keyword.KeywordScanner")],
        score_aggregator=ScoreAggregatorConfig(score_aggregator="cerbia.core.score_aggregators.max.MaxScoreAggregator"),
    )
    console = Console(record=True, force_terminal=False)

    render_validation_summary(config, Runner(config), console)

    output = console.export_text()
    assert "Config valid" in output
    assert "summary-gate" in output
    assert "KeywordScanner" in output
    assert "loaders=yes" in output
