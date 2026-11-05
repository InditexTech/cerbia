from types import ModuleType
from typing import get_type_hints

import httpx2
import pytest
from cerbia.core.apis.decisions import DecisionsResponse, PredicateQuestion
from cerbia.core.apis.systemone import NoulQuestion, SystemOneResponse
from cerbia.core.exceptions import CerbIAConfigError
from cerbia.core.models.scans import ScanOutcome
from cerbia.core.scanners import DecisionsScanner, SystemOneScanner
from cerbia.core.scanners.decisions import DecisionsEvaluator
from cerbia.core.scanners.systemone import SystemOneEvaluator
from pydantic import JsonValue, ValidationError

from .test_scanner import MockHTTP, usage


def test_decisions_evaluator_when_function_accepts_only_decisions_response(
    mock_http: MockHTTP, application_policy: ModuleType, monkeypatch: pytest.MonkeyPatch
) -> None:
    # Given
    def evaluate(response: DecisionsResponse, /) -> ScanOutcome:
        return ScanOutcome(risk_score=0.2, rationale=response.model)

    evaluator: DecisionsEvaluator = evaluate
    monkeypatch.setattr(application_policy, "evaluate_answers", evaluator)
    mock_http(
        lambda request: httpx2.Response(
            200,
            json={
                "model": "decisions-only",
                "answers": [{"type": "predicate", "name": "q", "probability": 0.8}],
                "usage": usage("decisions"),
            },
        )
    )
    scanner = DecisionsScanner(
        [PredicateQuestion(name="q", instructions="Assess")],
        "application_policy.evaluate_answers",
        "m",
        base_url="https://assessment.test",
    )
    # When
    outcome = scanner.scan("text")
    # Then
    assert outcome == ScanOutcome(risk_score=0.2, rationale="decisions-only")
    assert isinstance(scanner._questions, tuple)
    assert isinstance(scanner._questions[0], PredicateQuestion)
    assert scanner.scanner_id == "decisions"
    assert scanner.scanner_name == "Decisions"
    assert get_type_hints(DecisionsEvaluator.__call__)["response"] is DecisionsResponse


def test_systemone_evaluator_when_function_accepts_only_systemone_response(
    mock_http: MockHTTP, application_policy: ModuleType, monkeypatch: pytest.MonkeyPatch
) -> None:
    # Given
    def evaluate(response: SystemOneResponse, /) -> ScanOutcome:
        return ScanOutcome(risk_score=0.3, rationale=response.model)

    evaluator: SystemOneEvaluator = evaluate
    monkeypatch.setattr(application_policy, "evaluate_answers", evaluator)
    mock_http(
        lambda request: httpx2.Response(
            200,
            json={
                "model": "systemone-only",
                "answers": {"q": {"type": "noul", "noul": 0.8}},
                "usage": usage("systemone"),
            },
        )
    )
    scanner = SystemOneScanner(
        {"q": NoulQuestion()},
        "application_policy.evaluate_answers",
        "m",
        base_url="https://assessment.test",
    )
    # When
    outcome = scanner.scan("text")
    # Then
    assert outcome == ScanOutcome(risk_score=0.3, rationale="systemone-only")
    assert isinstance(scanner._questions, dict)
    assert isinstance(scanner._questions["q"], NoulQuestion)
    assert scanner.scanner_id == "systemone"
    assert scanner.scanner_name == "System One"
    assert get_type_hints(SystemOneEvaluator.__call__)["response"] is SystemOneResponse


@pytest.mark.parametrize("count", [1, 400])
def test_decisions_questions_when_count_within_limits(count: int) -> None:
    # Given
    questions = [PredicateQuestion(name=f"q{index}", instructions="Assess") for index in range(count)]
    # When
    scanner = DecisionsScanner(questions, "application_policy.evaluate_answers", "m")
    # Then
    assert scanner._questions == tuple(questions)


@pytest.mark.parametrize(
    "questions",
    [
        [],
        [{"type": "predicate", "name": f"q{index}", "instructions": "Assess"} for index in range(401)],
        {"q": {"type": "noul"}},
        [{"type": "noul"}],
    ],
)
def test_decisions_rejects_questions_when_shape_or_count_invalid(questions: JsonValue) -> None:
    # Given / When / Then
    with pytest.raises(CerbIAConfigError, match="^Invalid Decisions scanner questions$") as error:
        DecisionsScanner(questions, "application_policy.evaluate_answers", "m")
    assert isinstance(error.value.__cause__, ValidationError)


@pytest.mark.parametrize(
    "questions",
    [{}, [{"type": "predicate", "name": "q", "instructions": "Assess"}], {"q": {"type": "predicate"}}],
)
def test_systemone_rejects_questions_when_shape_or_count_invalid(questions: JsonValue) -> None:
    # Given / When / Then
    with pytest.raises(CerbIAConfigError, match="^Invalid System One scanner questions$") as error:
        SystemOneScanner(questions, "application_policy.evaluate_answers", "m")
    assert isinstance(error.value.__cause__, ValidationError)
