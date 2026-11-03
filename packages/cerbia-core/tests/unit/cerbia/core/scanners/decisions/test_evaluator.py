import traceback
from types import ModuleType

import httpx
import pytest
from cerbia.core.apis import APIConfigError, APIError
from cerbia.core.apis.decisions import DecisionsResponse
from cerbia.core.apis.systemone import SystemOneResponse
from cerbia.core.exceptions import CerbIAConfigError, CerbIAError
from cerbia.core.models.scans import ScanOutcome
from cerbia.core.scanners import DecisionsScanner, SystemOneScanner

from .test_scanner import MockHTTP, usage


def scanner(
    mock_http: MockHTTP,
    evaluator: str = "application_policy.evaluate_answers",
    format: str = "decisions",
) -> DecisionsScanner | SystemOneScanner:
    mock_http(
        lambda request: httpx.Response(
            200,
            json={
                "model": "resolved",
                "answers": [{"type": "predicate", "name": "q", "probability": 0.8}]
                if format == "decisions"
                else {"q": {"type": "noul", "noul": 0.8}},
                "usage": usage(format),
            },
        )
    )
    if format == "decisions":
        return DecisionsScanner(
            questions=[{"type": "predicate", "name": "q", "instructions": "Assess"}],
            model="m",
            base_url="https://assessment.test",
            evaluator=evaluator,
        )
    return SystemOneScanner(
        model="m",
        base_url="https://assessment.test",
        evaluator=evaluator,
        questions={"q": {"type": "noul", "instructions": "Assess"}},
    )


@pytest.mark.parametrize("format", ["decisions", "systemone"])
def test_resolve_once_and_call_once_per_response(
    mock_http: MockHTTP,
    application_policy: ModuleType,
    monkeypatch: pytest.MonkeyPatch,
    evaluations: list[DecisionsResponse | SystemOneResponse],
    application_outcome: ScanOutcome,
    format: str,
) -> None:
    # Given
    subject = scanner(mock_http, format=format)
    monkeypatch.setattr(application_policy, "evaluate_answers", lambda response: pytest.fail("resolved again"))
    # When
    results = [subject.scan("first"), subject.scan("second")]
    # Then
    assert all(result is application_outcome for result in results)
    assert len(evaluations) == 2
    assert all(response.model == "resolved" for response in evaluations)


@pytest.mark.parametrize("risk", [0.0, 1.0])
@pytest.mark.parametrize("format", ["decisions", "systemone"])
def test_same_answer_has_application_owned_risk(
    mock_http: MockHTTP,
    application_policy: ModuleType,
    monkeypatch: pytest.MonkeyPatch,
    risk: float,
    format: str,
) -> None:
    # Given
    outcome = ScanOutcome(risk_score=risk, rationale="My interpretation")
    monkeypatch.setattr(application_policy, "evaluate_answers", lambda response: outcome)
    subject = scanner(mock_http, format=format)
    # When
    result = subject.scan("same text")
    # Then
    assert result is outcome


@pytest.mark.parametrize(
    "path,message,cause_type",
    [
        ("", "Evaluator must be a dotted import path (module.function)", None),
        ("literal", "Evaluator must be a dotted import path (module.function)", None),
        (".evaluate", "Evaluator must be a dotted import path (module.function)", None),
        ("application_policy.", "Evaluator must be a dotted import path (module.function)", None),
        ("secret.module.fn", "Could not import evaluator", ModuleNotFoundError),
        ("application_policy.secret", "Could not import evaluator", AttributeError),
        ("application_policy.__name__", "Evaluator must be callable", None),
        (None, "Evaluator must be a dotted import path (module.function)", AttributeError),
        (42, "Evaluator must be a dotted import path (module.function)", AttributeError),
        (
            lambda response: ScanOutcome(risk_score=0, rationale="wrong surface"),
            "Evaluator must be a dotted import path (module.function)",
            AttributeError,
        ),
    ],
)
@pytest.mark.parametrize("format", ["decisions", "systemone"])
def test_config_error_when_import_invalid(
    mock_http: MockHTTP, path: str, message: str, cause_type: type[Exception] | None, format: str
) -> None:
    # Given / When / Then
    with pytest.raises(CerbIAConfigError) as error:
        scanner(mock_http, path, format)
    assert type(error.value) is CerbIAConfigError
    assert str(error.value) == message
    assert not isinstance(error.value, APIConfigError)
    assert "secret" not in str(error.value)
    if cause_type is None:
        assert error.value.__cause__ is None
    else:
        assert isinstance(error.value.__cause__, cause_type)
        assert error.value.__cause__ is error.value.__context__
        assert error.value.__cause__.__traceback__ is not None


@pytest.mark.parametrize(
    "result",
    [
        None,
        {},
        {"risk_score": 0, "rationale": "secret"},
        True,
        0.5,
    ],
)
@pytest.mark.parametrize("format", ["decisions", "systemone"])
def test_error_when_application_result_invalid(
    mock_http: MockHTTP,
    application_policy: ModuleType,
    monkeypatch: pytest.MonkeyPatch,
    result: ScanOutcome,
    format: str,
) -> None:
    # Given
    monkeypatch.setattr(application_policy, "evaluate_answers", lambda response: result)
    subject = scanner(mock_http, format=format)
    # When / Then
    with pytest.raises(CerbIAError) as error:
        subject.scan("text")
    assert type(error.value) is CerbIAError
    assert str(error.value) == "Evaluator must return ScanOutcome"
    assert not isinstance(error.value, APIError)
    assert error.value.__cause__ is None
    assert error.value.__context__ is None
    assert "secret" not in "".join(traceback.format_exception(error.value))


@pytest.mark.parametrize(
    "error_type", [RuntimeError, ValueError, KeyError, TypeError, OSError, APIError, APIConfigError]
)
@pytest.mark.parametrize("format", ["decisions", "systemone"])
def test_error_when_application_raises(
    mock_http: MockHTTP,
    application_policy: ModuleType,
    monkeypatch: pytest.MonkeyPatch,
    error_type: type[Exception],
    format: str,
) -> None:
    # Given
    original = error_type() if error_type in (APIError, APIConfigError) else error_type("application-secret")

    def fail(response: DecisionsResponse | SystemOneResponse) -> ScanOutcome:
        raise original

    monkeypatch.setattr(application_policy, "evaluate_answers", fail)
    subject = scanner(mock_http, format=format)
    # When / Then
    with pytest.raises(CerbIAError) as error:
        subject.scan("text")
    assert type(error.value) is CerbIAError
    label = "Decision" if format == "decisions" else "System One"
    assert str(error.value) == f"{label} evaluator raised an exception"
    assert not isinstance(error.value, APIError)
    assert error.value.__suppress_context__
    assert error.value.__cause__ is original
    assert "fail" in [frame.name for frame in traceback.extract_tb(original.__traceback__)]
    assert str(original) in "".join(traceback.format_exception(error.value))


@pytest.mark.parametrize("format", ["decisions", "systemone"])
def test_chained_error_when_evaluator_module_execution_fails(
    mock_http: MockHTTP,
    monkeypatch: pytest.MonkeyPatch,
    format: str,
) -> None:
    # Given
    original = RuntimeError("import-secret")

    def fail(name: str) -> None:
        raise original

    monkeypatch.setattr("importlib.import_module", fail)
    # When / Then
    with pytest.raises(CerbIAConfigError) as error:
        scanner(mock_http, format=format)
    assert type(error.value) is CerbIAConfigError
    assert str(error.value) == "Could not import evaluator"
    assert error.value.__suppress_context__
    assert error.value.__cause__ is original
    assert "fail" in [frame.name for frame in traceback.extract_tb(original.__traceback__)]
    assert "import-secret" in "".join(traceback.format_exception(error.value))


@pytest.mark.parametrize("scanner_type", [DecisionsScanner, SystemOneScanner])
def test_evaluator_is_required(scanner_type: type[DecisionsScanner] | type[SystemOneScanner]) -> None:
    # Given / When / Then
    import inspect

    parameters = inspect.signature(scanner_type).parameters
    assert parameters["evaluator"].default is inspect.Parameter.empty
    assert parameters["questions"].default is inspect.Parameter.empty
    assert parameters["model"].default is inspect.Parameter.empty
    assert "format" not in parameters
