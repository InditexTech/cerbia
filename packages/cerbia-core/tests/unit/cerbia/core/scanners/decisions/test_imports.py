import subprocess
import sys
import textwrap
from collections.abc import Callable
from typing import get_type_hints

import httpx2
import pytest
from cerbia.core.apis import decisions as api
from cerbia.core.apis import systemone
from cerbia.core.apis._http import HTTPClient
from cerbia.core.config import ScannerConfig
from cerbia.core.factories.scanner import ScannerFactory
from cerbia.core.scanners import DecisionsScanner, SystemOneScanner
from cerbia.core.scanners import decisions as policy
from cerbia.core.scanners import systemone as systemone_policy
from cerbia.core.scanners.decisions import DecisionsEvaluator
from cerbia.core.scanners.systemone import SystemOneEvaluator

type MockHTTP = Callable[[Callable[[httpx2.Request], httpx2.Response]], None]


def test_independent_public_scanners_when_importing_packages() -> None:
    # Given
    from cerbia.core import scanners

    # When / Then
    assert hasattr(scanners, "DecisionsScanner")
    assert hasattr(scanners, "SystemOneScanner")
    assert not hasattr(scanners, "DecisionScanner")


def test_provider_annotations_when_resolved_at_runtime() -> None:
    # Given
    constructors = (
        HTTPClient.__init__,
        api.DecisionsClient.__init__,
        systemone.SystemOneClient.__init__,
        DecisionsScanner.__init__,
        SystemOneScanner.__init__,
    )
    # When
    hints = [get_type_hints(constructor) for constructor in constructors]
    # Then
    assert [hint["api_key_provider"] for hint in hints] == [str | None] * 5


@pytest.mark.parametrize("protocol", ["decisions", "systemone"])
def test_wire_imports_when_scanner_policy_is_unavailable(protocol: str) -> None:
    # Given
    script = """
        import importlib.abc
        import sys

        class BlockPolicy(importlib.abc.MetaPathFinder):
            def find_spec(self, fullname, path=None, target=None):
                if fullname.startswith("cerbia.core.scanners") or fullname == "cerbia.core.apis.OTHER":
                    raise ModuleNotFoundError(fullname)
                return None

        sys.meta_path.insert(0, BlockPolicy())
        import cerbia.core.apis.PROTOCOL as api
        for name in api.__all__:
            assert getattr(api, name) is not None
        assert not any(name.startswith("cerbia.core.scanners") for name in sys.modules)
    """
    script = script.replace("PROTOCOL", protocol).replace(
        "OTHER", "systemone" if protocol == "decisions" else "decisions"
    )
    # When
    result = subprocess.run([sys.executable, "-c", textwrap.dedent(script)], capture_output=True, text=True, timeout=30)
    # Then
    assert result.returncode == 0, result.stderr


@pytest.mark.parametrize("namespace", ["cerbia.core.scanners", "cerbia.core.scanners.FORMAT"])
@pytest.mark.parametrize("format", ["decisions", "systemone"])
def test_plain_outcome_when_factory_builds_public_scanner(mock_http: MockHTTP, namespace: str, format: str) -> None:
    # Given
    config = ScannerConfig(
        scanner=namespace.replace("FORMAT", format)
        + (".DecisionsScanner" if format == "decisions" else ".SystemOneScanner"),
        init_args={
            "model": "m",
            "base_url": "https://assessment.test",
            "questions": [{"type": "predicate", "name": "q", "instructions": "Assess"}]
            if format == "decisions"
            else {"q": {"type": "noul", "instructions": "Assess"}},
            "evaluator": "application_policy.evaluate_answers",
        },
    )
    response = {
        "model": "resolved",
        "answers": [{"type": "predicate", "name": "q", "probability": 0.8}],
        "usage": {
            "input_tokens": 1,
            "output_tokens": 0,
            "total_tokens": 1,
            "input_tokens_details": {"cached_tokens": 0, "cache_write_tokens": 0},
            "output_tokens_details": {"reasoning_tokens": 0},
        },
    }
    if format == "systemone":
        response = {
            "model": "resolved",
            "answers": {"q": {"type": "noul", "noul": 0.8}},
            "usage": {"input_tokens": 1, "output_tokens": 0},
        }
    requests: list[httpx2.Request] = []

    def handle(request: httpx2.Request) -> httpx2.Response:
        requests.append(request)
        return httpx2.Response(200, json=response)

    mock_http(handle)
    # When
    scanner = ScannerFactory.build(config)
    assert isinstance(scanner, DecisionsScanner if format == "decisions" else SystemOneScanner)
    outcome = scanner.scan("evidence")
    # Then
    assert outcome.risk_score == 0.8
    assert set(outcome.model_dump()) == {"risk_score", "rationale", "matches"}
    assert not hasattr(scanner, "scan_structured")
    assert requests[0].url.path == f"/v1/{format}"


def test_separate_exports_when_importing_api_and_policy() -> None:
    # Given / When / Then
    assert "DecisionScanner" not in api.__all__
    assert "DecisionResult" not in api.__all__
    assert "PredicateRiskRule" not in api.__all__
    assert "DecisionsInput" not in policy.__all__
    assert "PredicateQuestion" not in policy.__all__
    assert set(policy.__all__) == {"DecisionsEvaluator", "DecisionsScanner"}
    assert policy.DecisionsEvaluator is DecisionsEvaluator
    assert set(systemone_policy.__all__) == {"SystemOneEvaluator", "SystemOneScanner"}
    assert systemone_policy.SystemOneEvaluator is SystemOneEvaluator
