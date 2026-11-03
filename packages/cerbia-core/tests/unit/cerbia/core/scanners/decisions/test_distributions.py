from collections.abc import Callable

import httpx
import pytest
from cerbia.core.apis import APIError
from cerbia.core.apis.decisions import DecisionsResponse
from cerbia.core.apis.systemone import SystemOneResponse
from cerbia.core.scanners import DecisionsScanner, SystemOneScanner
from pydantic import JsonValue

type MockHTTP = Callable[[Callable[[httpx.Request], httpx.Response]], None]


def build(
    mock_http: MockHTTP, format: str, kind: str, answer: dict[str, JsonValue]
) -> DecisionsScanner | SystemOneScanner:
    question: dict[str, JsonValue] = {"type": kind, "instructions": "Assess"}
    if kind == "choice":
        question.update(
            {"choices": [{"value": "a"}, {"value": "b"}, {"value": "c"}]}
            if format == "decisions"
            else {"criteria": {"a": None, "b": None, "c": None}}
        )
    else:
        question.update(
            {"levels": [{"label": "L"}, {"label": "M"}, {"label": "H"}]}
            if format == "decisions"
            else {"criteria": ["L", "M", "H"]}
        )
    if format == "decisions":
        question["name"] = "q"
        answer = {**answer, "name": "q"}
    usage: dict[str, JsonValue] = {"input_tokens": 1, "output_tokens": 0}
    if format == "decisions":
        usage.update(
            total_tokens=1,
            input_tokens_details={"cached_tokens": 0, "cache_write_tokens": 0},
            output_tokens_details={"reasoning_tokens": 0},
        )
    body = {"model": "m", "answers": [answer] if format == "decisions" else {"q": answer}, "usage": usage}
    mock_http(lambda request: httpx.Response(200, json=body))
    if format == "decisions":
        return DecisionsScanner(
            questions=[question],
            model="m",
            base_url="https://assessment.test",
            evaluator="application_policy.evaluate_answers",
        )
    return SystemOneScanner(
        model="m",
        base_url="https://assessment.test",
        questions={"q": question},
        evaluator="application_policy.evaluate_answers",
    )


def choice(format: str) -> dict[str, JsonValue]:
    return {
        "type": "choice",
        "choice": "a",
        "confidence": 0.01,
        "probabilities": (
            [{"value": "a", "probability": 0.5}, {"value": "b", "probability": 0.3}, {"value": "c", "probability": 0.2}]
            if format == "decisions"
            else {"a": 0.5, "b": 0.3, "c": 0.2}
        ),
    }


def score(format: str) -> dict[str, JsonValue]:
    answer: dict[str, JsonValue] = {
        "type": "score",
        "score": 1.1,
        "confidence": 0.02,
        "probabilities": (
            [
                {"value": 0, "label": "L", "probability": 0.1},
                {"value": 1, "label": "M", "probability": 0.7},
                {"value": 2, "label": "H", "probability": 0.2},
            ]
            if format == "decisions"
            else {"0": 0.1, "1": 0.7, "2": 0.2}
        ),
    }
    if format == "systemone":
        answer["legend"] = {"0": "L", "1": "M", "2": "H"}
    return answer


@pytest.mark.parametrize("format", ["decisions", "systemone"])
@pytest.mark.parametrize(
    "kind,field,value",
    [
        ("choice", "choice", "unknown"),
        ("choice", "choice", "b"),
        ("choice", "confidence", -0.1),
        ("choice", "confidence", 1.1),
        ("choice", "probabilities", {}),
        ("choice", "probabilities", []),
        ("score", "score", -0.1),
        ("score", "score", 2.1),
        ("score", "score", 1.5),
        ("score", "score", "1.1"),
        ("score", "confidence", True),
        ("score", "probabilities", {}),
        ("score", "probabilities", []),
    ],
)
def test_rejection_when_answer_inconsistent(
    mock_http: MockHTTP,
    format: str,
    kind: str,
    field: str,
    value: JsonValue,
    evaluations: list[DecisionsResponse | SystemOneResponse],
) -> None:
    # Given
    answer = choice(format) if kind == "choice" else score(format)
    answer[field] = value
    scanner = build(mock_http, format, kind, answer)
    # When / Then
    with pytest.raises(APIError):
        scanner.scan("text")
    assert evaluations == []


@pytest.mark.parametrize(
    "probabilities",
    [
        [{"value": "a", "probability": 0.5}, {"value": "b", "probability": 0.3}],
        [{"value": "a", "probability": 0.5}, {"value": "b", "probability": 0.3}, {"value": "c", "probability": 0.3}],
        [{"value": "a", "probability": 0.5}, {"value": "a", "probability": 0.3}, {"value": "c", "probability": 0.2}],
        [{"value": "a", "probability": 0.5}, {"value": "b", "probability": -0.1}, {"value": "c", "probability": 0.6}],
        [{"value": "a", "probability": 0.5}, {"value": "b", "probability": 0.3}, {"value": "x", "probability": 0.2}],
    ],
)
def test_rejection_when_decisions_distribution_invalid(
    mock_http: MockHTTP,
    probabilities: JsonValue,
    evaluations: list[DecisionsResponse | SystemOneResponse],
) -> None:
    # Given
    answer = {**choice("decisions"), "probabilities": probabilities}
    scanner = build(mock_http, "decisions", "choice", answer)
    # When / Then
    with pytest.raises(APIError):
        scanner.scan("text")
    assert evaluations == []


@pytest.mark.parametrize(
    "probabilities",
    [
        {"a": 0.5, "b": 0.3},
        {"a": 0.5, "b": 0.3, "x": 0.2},
        {"a": 0.5, "b": 0.3, "c": 0.3},
        {"a": 0.5, "b": -0.1, "c": 0.6},
    ],
)
def test_rejection_when_systemone_distribution_invalid(
    mock_http: MockHTTP,
    probabilities: JsonValue,
    evaluations: list[DecisionsResponse | SystemOneResponse],
) -> None:
    # Given
    scanner = build(mock_http, "systemone", "choice", {**choice("systemone"), "probabilities": probabilities})
    # When / Then
    with pytest.raises(APIError):
        scanner.scan("text")
    assert evaluations == []


@pytest.mark.parametrize(
    "probabilities",
    [
        [{"value": 0, "label": "L", "probability": 0.1}, {"value": 1, "label": "M", "probability": 0.9}],
        [
            {"value": 0, "label": "L", "probability": 0.1},
            {"value": 1, "label": "M", "probability": 0.7},
            {"value": 1, "label": "M", "probability": 0.2},
        ],
        [
            {"value": 0, "label": "Wrong", "probability": 0.1},
            {"value": 1, "label": "M", "probability": 0.7},
            {"value": 2, "label": "H", "probability": 0.2},
        ],
    ],
)
def test_rejection_when_score_domain_invalid(
    mock_http: MockHTTP,
    probabilities: JsonValue,
    evaluations: list[DecisionsResponse | SystemOneResponse],
) -> None:
    # Given
    scanner = build(mock_http, "decisions", "score", {**score("decisions"), "probabilities": probabilities})
    # When / Then
    with pytest.raises(APIError):
        scanner.scan("text")
    assert evaluations == []


def test_rejection_when_legend_changed(
    mock_http: MockHTTP,
    evaluations: list[DecisionsResponse | SystemOneResponse],
) -> None:
    # Given
    scanner = build(
        mock_http, "systemone", "score", {**score("systemone"), "legend": {"0": "Wrong", "1": "M", "2": "H"}}
    )
    # When / Then
    with pytest.raises(APIError):
        scanner.scan("text")
    assert evaluations == []


def test_all_answers_preserved_when_arriving_out_of_order(
    mock_http: MockHTTP,
    evaluations: list[DecisionsResponse | SystemOneResponse],
) -> None:
    # Given
    payload = {
        "model": "m",
        "answers": [
            {"type": "predicate", "name": "b", "probability": 0.2},
            {"type": "predicate", "name": "a", "probability": 0.8},
        ],
        "usage": {
            "input_tokens": 2,
            "output_tokens": 0,
            "total_tokens": 2,
            "input_tokens_details": {"cached_tokens": 0, "cache_write_tokens": 0},
            "output_tokens_details": {"reasoning_tokens": 0},
        },
    }
    mock_http(lambda request: httpx.Response(200, json=payload))
    scanner = DecisionsScanner(
        model="m",
        base_url="https://assessment.test",
        questions=[{"type": "predicate", "name": key, "instructions": "Assess"} for key in ["a", "b"]],
        evaluator="application_policy.evaluate_answers",
    )
    # When
    scanner.scan("text")
    # Then
    assert len(evaluations) == 1
    assert evaluations[0].model_dump(mode="json") == payload
