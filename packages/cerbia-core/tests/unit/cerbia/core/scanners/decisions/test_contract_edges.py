import json
from collections.abc import Callable

import httpx
import pytest
from cerbia.core.apis import _base
from cerbia.core.apis.decisions import DecisionsResponse, PredicateQuestion, RefusalAnswer
from cerbia.core.apis.systemone import NoulAnswer, NoulQuestion, SystemOneResponse, SystemOneScoreQuestion
from cerbia.core.exceptions import CerbIAConfigError
from cerbia.core.scanners import DecisionsScanner, SystemOneScanner
from pydantic import BaseModel, JsonValue, ValidationError

type MockHTTP = Callable[[Callable[[httpx.Request], httpx.Response]], None]


def test_boolean_choice_when_string_has_same_spelling(
    mock_http: MockHTTP,
    evaluations: list[DecisionsResponse | SystemOneResponse],
) -> None:
    # Given
    response = {
        "model": "m",
        "answers": [
            {
                "type": "choice",
                "name": "q",
                "choice": True,
                "confidence": 0.1,
                "probabilities": [{"value": True, "probability": 0.8}, {"value": "true", "probability": 0.2}],
            }
        ],
        "usage": {
            "input_tokens": 1,
            "output_tokens": 0,
            "total_tokens": 1,
            "input_tokens_details": {"cached_tokens": 0, "cache_write_tokens": 0},
            "output_tokens_details": {"reasoning_tokens": 0},
        },
    }
    mock_http(lambda request: httpx.Response(200, json=response))
    scanner = DecisionsScanner(
        model="m",
        base_url="https://assessment.test",
        questions=[
            {"type": "choice", "name": "q", "instructions": "Assess", "choices": [{"value": True}, {"value": "true"}]}
        ],
        evaluator="application_policy.evaluate_answers",
    )
    # When
    scanner.scan("text")
    # Then
    assert evaluations[0].model_dump(mode="json") == response


def test_default_question_type_when_typed_systemone_question_supplied(mock_http: MockHTTP) -> None:
    # Given
    requests: list[httpx.Request] = []

    def handle(request: httpx.Request) -> httpx.Response:
        requests.append(request)
        return httpx.Response(
            200,
            json={
                "model": "m",
                "answers": {"q": {"type": "noul", "noul": 0.3}},
                "usage": {"input_tokens": 1, "output_tokens": 0},
            },
        )

    mock_http(handle)
    scanner = SystemOneScanner(
        model="m",
        base_url="https://assessment.test",
        questions={"q": NoulQuestion()},
        evaluator="application_policy.evaluate_answers",
    )
    # When
    scanner.scan("text")
    # Then
    assert json.loads(requests[0].content)["questions"] == {"q": {"type": "noul"}}


@pytest.mark.parametrize(
    "questions,cause",
    [
        ([{"type": "predicate", "name": "q", "instructions": "Assess"}] * 2, ValueError),
        ([{"type": "predicate", "instructions": "Assess"}], ValidationError),
        ([{"type": "score", "name": "q", "instructions": "Assess", "levels": [{"label": "L"}]}], ValidationError),
        (
            [{"type": "choice", "name": "q", "instructions": "Assess", "choices": [{"value": "a"}, {"value": "a"}]}],
            ValidationError,
        ),
    ],
)
def test_config_rejection_when_questions_invalid(questions: list[JsonValue], cause: type[ValueError]) -> None:
    # Given / When / Then
    with pytest.raises(CerbIAConfigError) as error:
        DecisionsScanner(model="m", questions=questions, evaluator="application_policy.evaluate_answers")
    assert type(error.value) is CerbIAConfigError
    assert str(error.value) == "Invalid Decisions scanner questions"
    assert error.value.__suppress_context__
    assert isinstance(error.value.__cause__, cause)
    assert error.value.__cause__ is error.value.__context__
    assert error.value.__cause__.__traceback__ is not None


def test_refusal_when_parsing_preserves_nullable_id() -> None:
    # Given / When
    answer = RefusalAnswer.model_validate({"type": "refusal", "name": None})
    # Then
    assert answer.model_dump(mode="json") == {"type": "refusal", "name": None}


def test_rejection_when_systemone_score_has_single_level() -> None:
    # Given / When / Then
    with pytest.raises(ValidationError):
        SystemOneScoreQuestion(criteria=("Only",))


def test_evidence_when_response_contains_text_legend(
    mock_http: MockHTTP,
    evaluations: list[DecisionsResponse | SystemOneResponse],
) -> None:
    # Given
    criteria: list[JsonValue] = ["Low", "High"]
    response = {
        "model": "m",
        "answers": {
            "q": {
                "type": "score",
                "score": 0.7,
                "confidence": 0.9,
                "probabilities": {"0": 0.3, "1": 0.7},
                "legend": {"0": criteria[0], "1": criteria[1]},
            }
        },
        "usage": {"input_tokens": 2, "output_tokens": 0},
    }
    mock_http(lambda request: httpx.Response(200, json=response))
    scanner = SystemOneScanner(
        model="m",
        base_url="https://assessment.test",
        questions={"q": {"type": "score", "criteria": criteria}},
        evaluator="application_policy.evaluate_answers",
    )
    # When
    scanner.scan("text")
    # Then
    assert evaluations[0].model_dump(mode="json") == response


def test_rejection_when_question_instructions_are_multimodal() -> None:
    # Given
    instructions = [
        {"type": "input_text", "text": "Assess"},
        {"type": "input_image", "image_url": "https://images.test/a", "detail": "low"},
        {"type": "input_json", "data": [{"key": [1, None]}]},
    ]
    # When
    with pytest.raises(ValidationError):
        PredicateQuestion.model_validate({"name": "q", "instructions": instructions})


def test_frozen_question_when_scanner_parses_mapping() -> None:
    # Given
    scanner = DecisionsScanner(
        questions=[{"type": "predicate", "name": "q", "instructions": "x"}],
        evaluator="application_policy.evaluate_answers",
        model="m",
    )
    # When / Then
    with pytest.raises(ValidationError):
        scanner._questions[0].name = "other"


def test_ordinary_fields_visible_when_api_question_is_represented() -> None:
    # Given
    question = PredicateQuestion(name="q", instructions="Assess")
    # When
    representation = repr(question)
    # Then
    assert "name='q'" in representation
    assert "instructions='Assess'" in representation


@pytest.mark.parametrize("model", [PredicateQuestion, NoulAnswer])
def test_shared_api_validation_when_model_inherits_base(model: type[BaseModel]) -> None:
    # Given / When / Then
    assert issubclass(model, _base.APIModel)
    assert model.model_config == {
        "frozen": True,
        "extra": "forbid",
        "allow_inf_nan": False,
        "hide_input_in_errors": True,
    }


@pytest.mark.parametrize("identifier", ["", 1, True, None])
def test_rejection_when_systemone_question_id_is_empty_or_not_string(identifier: str | int | None) -> None:
    # Given / When / Then
    with pytest.raises(CerbIAConfigError, match="^Invalid System One scanner questions$") as error:
        SystemOneScanner(
            questions={identifier: {"type": "noul"}}, evaluator="application_policy.evaluate_answers", model="m"
        )
    assert isinstance(error.value.__cause__, ValidationError)


@pytest.mark.parametrize("value", [float("nan"), float("inf"), float("-inf")])
def test_rejection_when_api_number_is_nonfinite(value: float) -> None:
    # Given / When / Then
    with pytest.raises(ValidationError):
        NoulAnswer(type="noul", noul=value)


def test_rejection_when_api_model_has_extra_fields() -> None:
    # Given
    payload = {"name": "q", "instructions": "Assess", "extra": "private-input"}
    # When / Then
    with pytest.raises(ValidationError) as error:
        PredicateQuestion.model_validate(payload)
    assert error.value.errors()[0]["type"] == "extra_forbidden"
    assert "private-input" not in str(error.value)


def test_frozen_when_api_question_is_constructed() -> None:
    # Given
    question = PredicateQuestion(name="q", instructions="Assess")
    # When / Then
    with pytest.raises(ValidationError) as error:
        question.name = "other"
    assert error.value.errors()[0]["type"] == "frozen_instance"


def test_rubric_when_level_descriptions_are_configured(
    mock_http: MockHTTP,
    evaluations: list[DecisionsResponse | SystemOneResponse],
) -> None:
    # Given
    levels: list[JsonValue] = [
        {"label": "L", "description": "Low severity"},
        {"label": "H", "description": "High severity"},
    ]
    response = {
        "model": "m",
        "answers": [
            {
                "type": "score",
                "name": "q",
                "score": 0.7,
                "confidence": 0.1,
                "probabilities": [
                    {"value": 0, "label": "L", "probability": 0.3},
                    {"value": 1, "label": "H", "probability": 0.7},
                ],
            }
        ],
        "usage": {
            "input_tokens": 1,
            "output_tokens": 0,
            "total_tokens": 1,
            "input_tokens_details": {"cached_tokens": 0, "cache_write_tokens": 0},
            "output_tokens_details": {"reasoning_tokens": 0},
        },
    }
    mock_http(lambda request: httpx.Response(200, json=response))
    scanner = DecisionsScanner(
        model="m",
        base_url="https://assessment.test",
        questions=[{"type": "score", "name": "q", "instructions": "Assess", "levels": levels}],
        evaluator="application_policy.evaluate_answers",
    )
    # When
    scanner.scan("text")
    # Then
    assert evaluations[0].model_dump(mode="json") == response
