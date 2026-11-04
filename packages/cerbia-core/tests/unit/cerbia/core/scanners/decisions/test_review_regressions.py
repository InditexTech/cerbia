import json
from collections.abc import Callable

import httpx2
import pytest
from cerbia.core.exceptions import CerbIAConfigError
from cerbia.core.scanners import SystemOneScanner
from pydantic import JsonValue

type MockHTTP = Callable[[Callable[[httpx2.Request], httpx2.Response]], None]


def assessment(format: str, kind: str) -> tuple[dict[str, JsonValue], dict[str, JsonValue]]:
    question: dict[str, JsonValue] = {"type": kind, "instructions": "Assess"}
    answer: dict[str, JsonValue] = {"type": kind}
    match kind:
        case "predicate" | "noul":
            answer["probability" if format == "decisions" else "noul"] = 0.8
        case "score":
            question.update(
                {"levels": [{"label": "L"}, {"label": "H"}]} if format == "decisions" else {"criteria": ["L", "H"]}
            )
            answer.update(score=0.8, confidence=0.5)
            answer["probabilities"] = (
                [{"value": 0, "label": "L", "probability": 0.2}, {"value": 1, "label": "H", "probability": 0.8}]
                if format == "decisions"
                else {"0": 0.2, "1": 0.8}
            )
            if format == "systemone":
                answer["legend"] = {"0": "L", "1": "H"}
        case "choice":
            question.update(
                {"choices": [{"value": "a"}, {"value": "b"}, {"value": "c"}]}
                if format == "decisions"
                else {"criteria": {"a": None, "b": None, "c": None}}
            )
            answer.update(choice="b", confidence=0.5)
            answer["probabilities"] = (
                [
                    {"value": "a", "probability": 0.1},
                    {"value": "b", "probability": 0.7},
                    {"value": "c", "probability": 0.2},
                ]
                if format == "decisions"
                else {"a": 0.1, "b": 0.7, "c": 0.2}
            )
        case _:
            raise AssertionError(kind)
    if format == "decisions":
        question["name"] = "q"
        answer["name"] = "q"
    return question, answer


@pytest.mark.parametrize(
    "kind,field",
    [
        ("noul", "instructions"),
        ("choice", "instructions"),
        ("score", "instructions"),
        ("noul", "true"),
        ("noul", "false"),
        ("choice", "description"),
        ("score", "description"),
    ],
)
@pytest.mark.parametrize("value", [True, False, 1, 0.5])
def test_config_rejected_before_request_when_systemone_outer_scalar_invalid(
    mock_http: MockHTTP,
    kind: str,
    field: str,
    value: JsonValue,
) -> None:
    # Given
    question, _ = assessment("systemone", kind)
    if field == "instructions":
        question["instructions"] = value
    elif kind == "noul":
        question["criteria"] = {field: value}
    elif kind == "choice":
        question["criteria"] = {"a": value, "b": None, "c": None}
    else:
        question["criteria"] = [value, "High"]
    requests: list[httpx2.Request] = []

    def handle(request: httpx2.Request) -> httpx2.Response:
        requests.append(request)
        return httpx2.Response(500)

    mock_http(handle)
    # When / Then
    with pytest.raises(CerbIAConfigError, match="^Invalid System One scanner questions$"):
        SystemOneScanner(
            model="m",
            base_url="https://assessment.test",
            questions={"q": question},
            evaluator="application_policy.evaluate_answers",
        )
    assert requests == []


@pytest.mark.parametrize("description", ["Text"])
def test_request_when_systemone_uses_text_instructions(mock_http: MockHTTP, description: JsonValue) -> None:
    # Given
    requests: list[httpx2.Request] = []

    def handle(request: httpx2.Request) -> httpx2.Response:
        requests.append(request)
        return httpx2.Response(
            200,
            json={
                "model": "m",
                "answers": {"q": {"type": "noul", "noul": 0}},
                "usage": {"input_tokens": 1, "output_tokens": 0},
            },
        )

    question: dict[str, JsonValue] = {
        "type": "noul",
        "instructions": description,
        "criteria": {"true": description, "false": None},
    }
    mock_http(handle)
    scanner = SystemOneScanner(
        model="m",
        base_url="https://assessment.test",
        questions={"q": question},
        evaluator="application_policy.evaluate_answers",
    )
    # When
    scanner.scan("text")
    # Then: retain text instructions.
    assert json.loads(requests[0].content)["questions"]["q"] == question


@pytest.mark.parametrize("kind", ["noul", "choice", "score"])
@pytest.mark.parametrize("description", ["Text"])
def test_descriptions_preserved_when_systemone_uses_text(kind: str, description: JsonValue) -> None:
    # Given
    question, _ = assessment("systemone", kind)
    question["instructions"] = description
    match kind:
        case "noul":
            question["criteria"] = {"true": description, "false": None}
        case "choice":
            question["criteria"] = {"a": description, "b": None, "c": description}
        case "score":
            question["criteria"] = [description, "High"]
    # When
    scanner = SystemOneScanner(questions={"q": question}, evaluator="application_policy.evaluate_answers", model="m")
    # Then
    assert scanner._questions["q"].model_dump(mode="json", exclude_unset=True) == question


@pytest.mark.parametrize("field", ["instructions", "true", "false", "description"])
@pytest.mark.parametrize("value", [float("nan"), float("inf"), -float("inf")])
def test_config_rejected_when_description_contains_nonfinite_json(field: str, value: float) -> None:
    # Given
    kind = "choice" if field == "description" else "noul"
    question, _ = assessment("systemone", kind)
    nested: dict[str, JsonValue] = {"nested": [value]}
    if field == "instructions":
        question["instructions"] = nested
    elif field == "description":
        question["criteria"] = {"a": nested, "b": None, "c": None}
    else:
        question["criteria"] = {field: nested}
    # When / Then
    with pytest.raises(CerbIAConfigError, match="^Invalid System One scanner questions$"):
        SystemOneScanner(model="m", questions={"q": question}, evaluator="application_policy.evaluate_answers")


def test_config_rejected_when_score_description_is_null() -> None:
    # Given
    question, _ = assessment("systemone", "score")
    question["criteria"] = [None, "High"]
    # When / Then
    with pytest.raises(CerbIAConfigError, match="^Invalid System One scanner questions$"):
        SystemOneScanner(model="m", questions={"q": question}, evaluator="application_policy.evaluate_answers")
