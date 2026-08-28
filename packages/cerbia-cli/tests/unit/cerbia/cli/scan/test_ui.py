from io import StringIO

import pytest
from cerbia.cli.scan._ui import render_scan_result
from cerbia.core.models.entries import Entry
from cerbia.core.models.results import EntryResult, ScanResult
from cerbia.core.models.scans import Finding, MatchSpan, SkippedScanner
from cerbia.core.types import Action, Severity
from rich.console import Console

pytestmark = pytest.mark.unit


def test_render_scan_result_renders_findings_matches_and_skipped_scanners() -> None:
    finding = Finding(
        scanner_id="scanner",
        scanner_name="Threat Scanner",
        risk_score=0.8,
        severity=Severity.HIGH,
        action=Action.BLOCK,
        rationale="Threat found",
        matches=[MatchSpan(start=2, end=5)],
    )
    result = ScanResult(
        entry_results=[
            EntryResult(
                entry=Entry(text="content", source="config.yaml"),
                is_safe=False,
                findings=[finding],
                skipped_scanners=[
                    SkippedScanner(scanner_id="skip", scanner_name="Skipped Scanner", reason="Not supported")
                ],
            )
        ]
    )
    output = StringIO()

    render_scan_result(result, False, Console(file=output, force_terminal=False, width=120))

    assert "matches: 2:5" in output.getvalue()
    assert "Skipped Scanner" in output.getvalue()


def test_render_scan_result_hides_skipped_scanners_when_unsafe_only_is_enabled() -> None:
    result = ScanResult(
        entry_results=[
            EntryResult(
                entry=Entry(text="content", source="config.yaml"),
                is_safe=False,
                skipped_scanners=[
                    SkippedScanner(scanner_id="skip", scanner_name="Skipped Scanner", reason="Not supported")
                ],
            )
        ]
    )
    output = StringIO()

    render_scan_result(result, True, Console(file=output, force_terminal=False))

    assert "Skipped Scanner" not in output.getvalue()


def test_render_scan_result_shows_source_for_single_unsafe_entry_when_unsafe_only_is_enabled() -> None:
    result = ScanResult(
        entry_results=[
            EntryResult(
                entry=Entry(text="content", source="config.yaml", field_path="entries[0]"),
                is_safe=False,
            )
        ]
    )
    output = StringIO()

    render_scan_result(result, True, Console(file=output, force_terminal=False))

    assert "config.yaml:entries[0]" in output.getvalue()


def test_render_scan_result_renders_no_unsafe_entries_message_when_result_is_empty() -> None:
    output = StringIO()

    render_scan_result(ScanResult(), True, Console(file=output, force_terminal=False))

    assert "No unsafe entries found" in output.getvalue()
