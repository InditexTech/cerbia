import pytest
from cerbia.core.models.entries import Entry
from cerbia.core.models.results import EntryResult, ScanResult
from cerbia.core.models.scans import Finding
from cerbia.core.types import Action, Severity

pytestmark = pytest.mark.unit


def test_scan_result_aggregates_empty_entry_results() -> None:
    result = ScanResult(entry_results=[])

    assert result.is_safe is True
    assert result.total_findings == 0
    assert result.unsafe_entries == 0


def test_scan_result_is_safe_if_all_entry_results_are_safe() -> None:
    safe_entry_result = EntryResult(
        entry=Entry(text="safe", source="stdin"),
        is_safe=True,
        aggregated_score=0.0,
        rationale="no threats found",
        findings=[],
        skipped_scanners=[],
    )

    result = ScanResult(entry_results=[safe_entry_result])

    assert result.is_safe is True
    assert result.total_findings == 0
    assert result.unsafe_entries == 0


def test_scan_result_is_unsafe_if_any_entry_result_is_unsafe() -> None:
    finding = Finding(
        scanner_id="scanner",
        scanner_name="Scanner",
        risk_score=0.8,
        severity=Severity.HIGH,
        action=Action.BLOCK,
        rationale="threat found",
    )
    safe_result = EntryResult(
        entry=Entry(text="safe", source="stdin"),
        is_safe=True,
        aggregated_score=0.0,
        rationale="no threats found",
        findings=[],
        skipped_scanners=[],
    )
    unsafe_result = EntryResult(
        entry=Entry(text="unsafe", source="stdin"),
        is_safe=False,
        aggregated_score=0.8,
        rationale="threat found",
        findings=[finding, finding],
        skipped_scanners=[],
    )

    result = ScanResult(entry_results=[safe_result, unsafe_result])

    assert result.is_safe is False
    assert result.total_findings == 2
    assert result.unsafe_entries == 1
