import logging

import pytest
from cerbia.core.models.scans import ScanOutcome
from cerbia.core.security_gate import SecurityGate
from cerbia.core.types import Action, ContentType, ScannerErrorPolicy, Severity

pytestmark = pytest.mark.unit


class _CanaryFailureScanner:
    scanner_id = "configured-scanner-CANARY"
    scanner_name = "Configured Scanner CANARY"
    severity = Severity.HIGH
    action = Action.BLOCK
    content_types: tuple[ContentType, ...] | None = None

    def scan(self, text: str) -> ScanOutcome:
        raise RuntimeError("Bearer CANARY")


def test_security_gate_does_not_log_handled_scanner_failure_details(mocker, caplog) -> None:
    gate = SecurityGate(
        "configured-gate-CANARY", [_CanaryFailureScanner()], mocker.Mock(), on_scanner_error=ScannerErrorPolicy.BLOCK
    )

    with caplog.at_level(logging.ERROR, logger="cerbia"):
        result = gate.scan("input-CANARY")

    assert result.is_safe is False
    assert "Bearer CANARY" not in caplog.text
    assert "Blocking gate due to error policy." in caplog.text
