import pytest
from cerbia.core.models.scans import MatchSpan, ScanOutcome, SkippedScanner
from cerbia.core.security_gate import SecurityGate
from cerbia.core.types import Action, ContentType, ScannerErrorPolicy, Severity

pytestmark = pytest.mark.unit


class _ScannerStub:
    def __init__(
        self,
        scanner_id: str,
        outcome: ScanOutcome,
        *,
        severity: Severity = Severity.MEDIUM,
        action: Action = Action.PASS,
        content_types: tuple[ContentType, ...] | None = None,
    ) -> None:
        self.scanner_id = scanner_id
        self.scanner_name = scanner_id.replace("-", " ").title()
        self.outcome = outcome
        self.severity = severity
        self.action = action
        self.content_types = content_types

    def scan(self, text: str) -> ScanOutcome:
        return self.outcome


class _FailingScannerStub(_ScannerStub):
    def scan(self, text: str) -> ScanOutcome:
        raise RuntimeError("scanner failed")


def test_security_gate_stores_skip_policy(mocker) -> None:
    gate = SecurityGate("gate", [], mocker.Mock(), on_scanner_error=ScannerErrorPolicy.SKIP)

    assert gate.on_scanner_error is ScannerErrorPolicy.SKIP


def test_security_gate_reraises_original_scanner_error_without_running_trailing_scanner(mocker) -> None:
    failing_scanner = _FailingScannerStub("failing-scanner", ScanOutcome(risk_score=0.0, rationale="Unused"))
    trailing_scanner = _ScannerStub("trailing-scanner", ScanOutcome(risk_score=0.0, rationale="Safe"))
    trailing_scan = mocker.spy(trailing_scanner, "scan")
    gate = SecurityGate(
        "gate", [failing_scanner, trailing_scanner], mocker.Mock(), on_scanner_error=ScannerErrorPolicy.FAIL
    )

    with pytest.raises(RuntimeError, match="scanner failed") as error:
        gate.scan("content")

    assert error.value.args == ("scanner failed",)
    trailing_scan.assert_not_called()


@pytest.mark.parametrize("fail_fast, trailing_called", [(True, False), (False, True)])
def test_security_gate_blocks_after_scanner_error_and_continues(fail_fast: bool, trailing_called: bool, mocker) -> None:
    failing_scanner = _FailingScannerStub("failing-scanner", ScanOutcome(risk_score=0.0, rationale="Unused"))
    succeeding_scanner = _ScannerStub("succeeding-scanner", ScanOutcome(risk_score=0.0, rationale="Safe"))
    succeeding_scan = mocker.spy(succeeding_scanner, "scan")
    aggregator = mocker.Mock()
    gate = SecurityGate(
        "gate",
        [failing_scanner, succeeding_scanner],
        aggregator,
        fail_fast=fail_fast,
        on_scanner_error=ScannerErrorPolicy.BLOCK,
    )

    result = gate.scan("content")

    assert result.is_safe is False
    assert result.score == 0.0
    assert result.rationale == "Scanner execution failed: Failing Scanner"
    assert [finding.scanner_id for finding in result.findings] == ["succeeding-scanner"] * trailing_called
    if trailing_called:
        succeeding_scan.assert_called_once_with("content")
    else:
        succeeding_scan.assert_not_called()
    assert result.skipped_scanners == []
    assert "RuntimeError" not in result.model_dump_json()
    assert "scanner failed" not in result.model_dump_json()
    aggregator.compute.assert_not_called()


def test_security_gate_skips_failed_scanner_and_continues(mocker) -> None:
    failing_scanner = _FailingScannerStub("failing-scanner", ScanOutcome(risk_score=0.0, rationale="Unused"))
    succeeding_scanner = _ScannerStub("succeeding-scanner", ScanOutcome(risk_score=0.0, rationale="Safe"))
    gate = SecurityGate(
        "gate", [failing_scanner, succeeding_scanner], mocker.Mock(), on_scanner_error=ScannerErrorPolicy.SKIP
    )

    result = gate.scan("content")

    assert result.is_safe is True
    assert [finding.scanner_id for finding in result.findings] == ["succeeding-scanner"]
    assert result.skipped_scanners == [
        SkippedScanner(
            scanner_id="failing-scanner",
            scanner_name="Failing Scanner",
            reason="scanner execution failed",
        )
    ]


def test_security_gate_returns_findings_when_scanners_complete(mocker) -> None:
    first_scanner = _build_scanner("first-scanner", risk_score=0.0, rationale="Safe")
    second_scanner = _build_scanner("second-scanner", risk_score=0.2, rationale="Review", action=Action.WARN)
    aggregator = mocker.Mock()
    gate = SecurityGate("gate", [first_scanner, second_scanner], aggregator)

    result = gate.scan("content")

    assert result.is_safe is True
    assert result.score == 0.0
    assert result.rationale == "Passed with warnings: Second Scanner"
    assert [(finding.scanner_id, finding.risk_score) for finding in result.findings] == [
        ("first-scanner", 0.0),
        ("second-scanner", 0.2),
    ]
    assert result.skipped_scanners == []
    aggregator.compute.assert_not_called()


def test_security_gate_returns_safe_verdict_without_scanners(mocker) -> None:
    aggregator = mocker.Mock()
    gate = SecurityGate("gate", [], aggregator)

    result = gate.scan("content")

    assert result.is_safe is True
    assert result.score == 0.0
    assert result.findings == []
    aggregator.compute.assert_not_called()


@pytest.mark.parametrize(
    "outcome",
    [
        ScanOutcome(risk_score=0.2, rationale="Detected", matches=[MatchSpan(start=2, end=5)]),
        ScanOutcome(risk_score=0.2, rationale="Detected"),
    ],
    ids=["explicit_match_span", "default_empty_matches"],
)
def test_security_gate_propagates_outcome_matches_to_findings(mocker, outcome: ScanOutcome) -> None:
    scanner = _ScannerStub("scanner", outcome)
    aggregator = mocker.Mock()
    gate = SecurityGate("gate", [scanner], aggregator)

    result = gate.scan("content")

    assert result.findings[0].matches == outcome.matches


def test_security_gate_skips_incompatible_scanner_when_content_type_is_provided(mocker) -> None:
    incompatible_scanner = _build_scanner(
        "text-scanner",
        risk_score=1.0,
        rationale="Should not run",
        content_types=(ContentType.TEXT,),
    )
    scan = mocker.spy(incompatible_scanner, "scan")
    aggregator = mocker.Mock()
    gate = SecurityGate("gate", [incompatible_scanner], aggregator)

    result = gate.scan("https://example.com", content_type=ContentType.URL)

    assert result.is_safe is True
    assert result.findings == []
    assert result.skipped_scanners[0].scanner_id == "text-scanner"
    scan.assert_not_called()
    aggregator.compute.assert_not_called()


def test_security_gate_stops_after_blocking_scanner_when_fail_fast_is_enabled(mocker) -> None:
    risk_score = 0.8
    weighted_score = risk_score * Severity.HIGH.weight
    blocking_scanner = _build_scanner(
        "blocking-scanner", risk_score=risk_score, rationale="Blocked", severity=Severity.HIGH, action=Action.BLOCK
    )
    trailing_scanner = _build_scanner("trailing-scanner", risk_score=0.4, rationale="Should not run")
    scan = mocker.spy(trailing_scanner, "scan")
    aggregator = mocker.Mock()
    aggregator.compute.return_value = weighted_score
    gate = SecurityGate("gate", [blocking_scanner, trailing_scanner], aggregator, threshold=weighted_score)

    result = gate.scan("content")

    assert result.is_safe is False
    assert result.score == weighted_score
    assert [finding.scanner_id for finding in result.findings] == ["blocking-scanner"]
    scan.assert_not_called()
    aggregator.compute.assert_called_once_with([weighted_score])


def test_security_gate_runs_remaining_scanners_when_fail_fast_is_disabled(mocker) -> None:
    blocking_scanner = _build_scanner(
        "blocking-scanner", risk_score=0.8, rationale="Blocked", severity=Severity.HIGH, action=Action.BLOCK
    )
    trailing_scanner = _build_scanner("trailing-scanner", risk_score=0.0, rationale="Safe")
    scan = mocker.spy(trailing_scanner, "scan")
    aggregator = mocker.Mock()
    aggregator.compute.return_value = 0.6
    gate = SecurityGate("gate", [blocking_scanner, trailing_scanner], aggregator, fail_fast=False, threshold=0.5)

    result = gate.scan("content")

    assert result.is_safe is False
    assert [finding.scanner_id for finding in result.findings] == ["blocking-scanner", "trailing-scanner"]
    scan.assert_called_once_with("content")
    aggregator.compute.assert_called_once_with([0.6000000000000001])


@pytest.mark.parametrize(
    ("action", "severity", "risk_score", "threshold", "aggregated_score", "expected_is_safe", "expected_score"),
    [
        (Action.BLOCK, Severity.HIGH, 0.8, 0.61, 0.6, True, 0.6),
        (Action.BLOCK, Severity.HIGH, 0.8, 0.6, 0.6, False, 0.6),
        (Action.WARN, Severity.CRITICAL, 1.0, 0.0, 1.0, True, 0.0),
    ],
    ids=["score_below_threshold", "score_at_threshold", "warn_finding"],
)
def test_security_gate_returns_verdict_based_on_weighted_blocking_scores(
    mocker,
    action: Action,
    severity: Severity,
    risk_score: float,
    threshold: float,
    aggregated_score: float,
    expected_is_safe: bool,
    expected_score: float,
) -> None:
    scanner = _build_scanner("scanner", risk_score=risk_score, rationale="Detected", severity=severity, action=action)
    aggregator = mocker.Mock()
    aggregator.compute.return_value = aggregated_score
    gate = SecurityGate("gate", [scanner], aggregator, threshold=threshold)

    result = gate.scan("content")

    assert result.is_safe is expected_is_safe
    assert result.score == expected_score
    if action is Action.BLOCK:
        aggregator.compute.assert_called_once_with([risk_score * severity.weight])
    else:
        aggregator.compute.assert_not_called()


def _build_scanner(
    scanner_id: str,
    *,
    risk_score: float,
    rationale: str,
    severity: Severity = Severity.MEDIUM,
    action: Action = Action.PASS,
    content_types: tuple[ContentType, ...] | None = None,
) -> _ScannerStub:
    return _ScannerStub(
        scanner_id,
        ScanOutcome(risk_score=risk_score, rationale=rationale),
        severity=severity,
        action=action,
        content_types=content_types,
    )
