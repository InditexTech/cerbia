import pytest
from cerbia.core.config import CerbIAConfig, LoaderConfig, PreprocessorConfig, ScannerConfig, ScoreAggregatorConfig
from cerbia.core.exceptions import CerbIAConfigError
from cerbia.core.models.entries import Entry
from cerbia.core.models.scans import Finding, SkippedScanner
from cerbia.core.runner import Runner
from cerbia.core.security_gate._models import GateVerdict
from cerbia.core.types import Action, ContentType, ScannerErrorPolicy, Severity

pytestmark = pytest.mark.unit


def test_runner_builds_configured_components_and_security_gate(mocker) -> None:
    config = _build_config(
        preprocessors=[PreprocessorConfig(preprocessor="test.Preprocessor")], on_scanner_error=ScannerErrorPolicy.SKIP
    )
    loader = mocker.Mock()
    preprocessor = mocker.Mock()
    first_scanner, second_scanner = mocker.Mock(), mocker.Mock()
    score_aggregator = mocker.Mock()
    loader_factory = mocker.patch("cerbia.core.runner.LoaderFactory.build", return_value=loader)
    preprocessor_factory = mocker.patch("cerbia.core.runner.PreprocessorFactory.build", return_value=preprocessor)
    scanner_factory = mocker.patch(
        "cerbia.core.runner.ScannerFactory.build", side_effect=[first_scanner, second_scanner]
    )
    score_aggregator_factory = mocker.patch(
        "cerbia.core.runner.ScoreAggregatorFactory.build", return_value=score_aggregator
    )
    security_gate = mocker.patch("cerbia.core.runner.SecurityGate")

    runner = Runner(config)

    assert runner.loaders == [loader]
    assert runner.preprocessors == [preprocessor]
    assert runner.scanners == [first_scanner, second_scanner]
    assert runner.score_aggregator is score_aggregator
    loader_factory.assert_called_once_with(config.loaders[0])
    preprocessor_factory.assert_called_once_with(config.preprocessors[0])
    assert scanner_factory.call_args_list[0].args == (config.scanners[0],)
    assert scanner_factory.call_args_list[1].args == (config.scanners[1],)
    assert (
        scanner_factory.call_args_list[0].kwargs["url_registry"]
        is scanner_factory.call_args_list[1].kwargs["url_registry"]
    )
    score_aggregator_factory.assert_called_once_with(config.score_aggregator)
    security_gate.assert_called_once_with(
        name="test-gate",
        scanners=[first_scanner, second_scanner],
        fail_fast=False,
        score_aggregator=score_aggregator,
        threshold=0.7,
        on_scanner_error=ScannerErrorPolicy.SKIP,
    )


def test_runner_raises_config_error_when_loaders_are_not_configured() -> None:
    config = _build_config(loaders=[])

    with pytest.raises(CerbIAConfigError, match="No loaders configured"):
        Runner(config)


def test_runner_raises_config_error_when_scanners_are_not_configured(mocker) -> None:
    config = _build_config(scanners=[])
    mocker.patch("cerbia.core.runner.LoaderFactory.build", return_value=mocker.Mock())

    with pytest.raises(CerbIAConfigError, match="No scanners configured"):
        Runner(config)


def test_runner_applies_preprocessors_sequentially(mocker) -> None:
    first_entries = [Entry(text="original", source="inline")]
    second_entries = [Entry(text="normalized", source="inline")]
    first_preprocessor = mocker.Mock()
    first_preprocessor.process.return_value = second_entries
    second_preprocessor = mocker.Mock()
    second_preprocessor.process.return_value = []
    runner = object.__new__(Runner)
    runner.preprocessors = [first_preprocessor, second_preprocessor]

    result = runner._preprocess(first_entries)

    assert result == []
    first_preprocessor.process.assert_called_once_with(first_entries)
    second_preprocessor.process.assert_called_once_with(second_entries)


def test_runner_scans_loaded_entry_when_no_preprocessors_are_configured(mocker) -> None:
    config = _build_config()
    entry = Entry(text="loaded text", source="loader", content_type=ContentType.TEXT)
    loader = mocker.Mock()
    loader.load.return_value = [entry]
    gate = mocker.Mock()
    gate.scan.return_value = GateVerdict(
        is_safe=True,
        score=0.0,
        rationale="All scanners passed",
        findings=[],
        skipped_scanners=[],
    )
    mocker.patch("cerbia.core.runner.LoaderFactory.build", return_value=loader)
    mocker.patch("cerbia.core.runner.ScannerFactory.build", return_value=mocker.Mock())
    mocker.patch("cerbia.core.runner.ScoreAggregatorFactory.build", return_value=mocker.Mock())
    mocker.patch("cerbia.core.runner.SecurityGate", return_value=gate)

    runner = Runner(config)

    result = runner.scan()

    assert result.entry_results[0].entry == entry
    loader.load.assert_called_once_with()
    gate.scan.assert_called_once_with("loaded text", content_type=ContentType.TEXT)


def test_runner_preserves_entry_result_fields_when_scanning(mocker) -> None:
    entry = Entry(text="characterized text", source="characterized-source", content_type=ContentType.TEXT)
    loader = mocker.Mock()
    loader.load.return_value = [entry]
    gate = mocker.Mock()
    gate.scan.return_value = GateVerdict(
        is_safe=False,
        score=0.7,
        rationale="characterized rationale",
        findings=[],
        skipped_scanners=[],
    )
    mocker.patch("cerbia.core.runner.LoaderFactory.build", return_value=loader)
    mocker.patch("cerbia.core.runner.ScannerFactory.build", return_value=mocker.Mock())
    mocker.patch("cerbia.core.runner.ScoreAggregatorFactory.build", return_value=mocker.Mock())
    mocker.patch("cerbia.core.runner.SecurityGate", return_value=gate)

    result = Runner(_build_config()).scan()

    assert [
        (entry_result.entry, entry_result.is_safe, entry_result.aggregated_score, entry_result.rationale)
        for entry_result in result.entry_results
    ] == [(entry, False, 0.7, "characterized rationale")]


def test_runner_returns_entry_results_when_loaders_provide_entries(mocker) -> None:
    config = _build_config(
        loaders=[LoaderConfig(loader="test.FirstLoader"), LoaderConfig(loader="test.SecondLoader")],
        preprocessors=[PreprocessorConfig(preprocessor="test.Preprocessor")],
    )
    first_entry = Entry(text="first", source="first-source", content_type=ContentType.TEXT)
    second_entry = Entry(text="second", source="second-source", field_path="body", content_type=ContentType.CODE)
    first_loader, second_loader = mocker.Mock(), mocker.Mock()
    first_loader.load.return_value = [first_entry]
    second_loader.load.return_value = [second_entry]
    preprocessor = mocker.Mock()
    preprocessor.process.return_value = [second_entry, first_entry]
    finding = Finding(
        scanner_id="scanner",
        scanner_name="Scanner",
        risk_score=0.8,
        severity=Severity.HIGH,
        action=Action.BLOCK,
        rationale="Threat detected",
    )
    skipped_scanner = SkippedScanner(scanner_id="skipped", scanner_name="Skipped", reason="Unsupported")
    gate = mocker.Mock()
    gate.scan.side_effect = [
        GateVerdict(
            is_safe=False,
            score=0.6,
            rationale="Scanner: Threat detected",
            findings=[finding],
            skipped_scanners=[skipped_scanner],
        ),
        GateVerdict(is_safe=True, score=0.0, rationale="All scanners passed", findings=[], skipped_scanners=[]),
    ]
    mocker.patch("cerbia.core.runner.LoaderFactory.build", side_effect=[first_loader, second_loader])
    mocker.patch("cerbia.core.runner.PreprocessorFactory.build", return_value=preprocessor)
    mocker.patch("cerbia.core.runner.ScannerFactory.build", return_value=mocker.Mock())
    mocker.patch("cerbia.core.runner.ScoreAggregatorFactory.build", return_value=mocker.Mock())
    mocker.patch("cerbia.core.runner.SecurityGate", return_value=gate)

    runner = Runner(config)

    result = runner.scan()

    assert result.is_safe is False
    assert result.total_findings == 1
    assert result.unsafe_entries == 1
    assert [
        (entry_result.entry, entry_result.is_safe, entry_result.aggregated_score)
        for entry_result in result.entry_results
    ] == [
        (second_entry, False, 0.6),
        (first_entry, True, 0.0),
    ]
    assert result.entry_results[0].rationale == "Scanner: Threat detected"
    assert result.entry_results[0].findings == [finding]
    assert result.entry_results[0].skipped_scanners == [skipped_scanner]
    assert gate.scan.call_args_list == [
        mocker.call("second", content_type=ContentType.CODE),
        mocker.call("first", content_type=ContentType.TEXT),
    ]


def test_runner_returns_empty_safe_result_when_loaders_provide_no_entries(mocker) -> None:
    config = _build_config()
    loader = mocker.Mock()
    loader.load.return_value = []
    gate = mocker.Mock()
    mocker.patch("cerbia.core.runner.LoaderFactory.build", return_value=loader)
    mocker.patch("cerbia.core.runner.ScannerFactory.build", return_value=mocker.Mock())
    mocker.patch("cerbia.core.runner.ScoreAggregatorFactory.build", return_value=mocker.Mock())
    mocker.patch("cerbia.core.runner.SecurityGate", return_value=gate)

    runner = Runner(config)

    result = runner.scan()

    assert result.entry_results == []
    assert result.is_safe is True
    assert result.total_findings == 0
    assert result.unsafe_entries == 0
    gate.scan.assert_not_called()


def _build_config(
    *,
    loaders: list[LoaderConfig] | None = None,
    preprocessors: list[PreprocessorConfig] | None = None,
    scanners: list[ScannerConfig] | None = None,
    on_scanner_error: ScannerErrorPolicy = ScannerErrorPolicy.BLOCK,
) -> CerbIAConfig:
    return CerbIAConfig(
        name="test-gate",
        loaders=loaders if loaders is not None else [LoaderConfig(loader="test.Loader")],
        preprocessors=preprocessors if preprocessors is not None else [],
        fail_fast=False,
        threshold=0.7,
        on_scanner_error=on_scanner_error,
        scanners=scanners
        if scanners is not None
        else [ScannerConfig(scanner="test.FirstScanner"), ScannerConfig(scanner="test.SecondScanner")],
        score_aggregator=ScoreAggregatorConfig(score_aggregator="test.ScoreAggregator"),
    )
