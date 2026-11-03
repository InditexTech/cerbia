from collections.abc import Callable

import httpx
import pytest
from cerbia.core.apis import APIConfigError, APIError
from cerbia.core.apis.decisions import DecisionsResponse
from cerbia.core.apis.systemone import SystemOneResponse
from cerbia.core.scanners import DecisionsScanner, SystemOneScanner
from pydantic import JsonValue

type MockHTTP = Callable[[Callable[[httpx.Request], httpx.Response]], None]


def scanner_with(
    mock_http: MockHTTP, body: JsonValue | bytes, format: str = "decisions"
) -> DecisionsScanner | SystemOneScanner:
    def handle(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, content=body) if isinstance(body, bytes) else httpx.Response(200, json=body)

    mock_http(handle)
    if format == "decisions":
        return DecisionsScanner(
            questions=[{"type": "predicate", "name": "q", "instructions": "Assess"}],
            model="model",
            base_url="https://assessment.test",
            evaluator="application_policy.evaluate_answers",
        )
    return SystemOneScanner(
        model="model",
        base_url="https://assessment.test",
        questions={"q": {"type": "noul", "instructions": "Assess"}},
        evaluator="application_policy.evaluate_answers",
    )


@pytest.mark.parametrize(
    "answers",
    [
        [],
        [{"type": "predicate", "name": "other", "probability": 0.5}],
        [{"type": "predicate", "name": "q", "probability": 0.5}] * 2,
        [{"type": "predicate", "name": "q", "probability": -0.1}],
        [{"type": "predicate", "name": "q", "probability": 1.1}],
        [{"type": "predicate", "name": "q", "probability": "0.8"}],
        [{"type": "predicate", "name": None, "probability": 0.5}],
        [{"type": "predicate", "name": "q", "probability": True}],
        [{"type": "predicate", "name": "q", "probability": 0.8, "secret": "credential"}],
        [{"type": "refusal", "name": "q"}],
        [{"type": "refusal", "name": None}],
        [{"type": "noul", "name": "q", "noul": 0.5}],
    ],
)
def test_sanitized_error_when_answer_invalid(
    mock_http: MockHTTP,
    answers: JsonValue,
    evaluations: list[DecisionsResponse | SystemOneResponse],
) -> None:
    # Given
    scanner = scanner_with(
        mock_http,
        {
            "model": "model",
            "answers": answers,
            "usage": {
                "input_tokens": 1,
                "output_tokens": 0,
                "input_tokens_details": {"cached_tokens": 0, "cache_write_tokens": 0},
                "output_tokens_details": {"reasoning_tokens": 0},
                "total_tokens": 1,
            },
        },
    )
    # When / Then
    with pytest.raises(APIError) as error:
        scanner.scan("credential")
    assert str(error.value) == "API request failed"
    assert error.value.__suppress_context__
    assert evaluations == []


@pytest.mark.parametrize(
    "body",
    [
        b"not-json-secret",
        b'{"model":"secret"}',
        b'{"answers":{"q":{},"q":{}}}',
        b'{"model":"m","answers":[{"type":"predicate","name":"q","probability":NaN}],"usage":{}}',
        b'{"model":"m","answers":[{"type":"predicate","name":"q","probability":Infinity}],"usage":{}}',
    ],
)
def test_error_when_payload_malformed(
    mock_http: MockHTTP,
    body: bytes,
    evaluations: list[DecisionsResponse | SystemOneResponse],
) -> None:
    # Given
    scanner = scanner_with(mock_http, body)
    # When / Then
    with pytest.raises(APIError):
        scanner.scan("text")
    assert evaluations == []


@pytest.mark.parametrize(
    "answer",
    [
        {},
        {"q": {"type": "refusal"}},
        {"q": {"type": "predicate", "probability": 1}},
        {"q": {"type": "noul", "noul": 0.5}, "extra": {"type": "noul", "noul": 0}},
    ],
)
def test_error_when_systemone_answer_invalid(
    mock_http: MockHTTP,
    answer: JsonValue,
    evaluations: list[DecisionsResponse | SystemOneResponse],
) -> None:
    # Given
    scanner = scanner_with(
        mock_http, {"model": "m", "answers": answer, "usage": {"input_tokens": 1, "output_tokens": 0}}, "systemone"
    )
    # When / Then
    with pytest.raises(APIError):
        scanner.scan("text")
    assert evaluations == []


@pytest.mark.parametrize("status", [301, 307, 400, 401, 403, 429, 500])
def test_error_without_retry_or_redirect_when_http_fails(mock_http: MockHTTP, status: int) -> None:
    # Given
    requests: list[httpx.Request] = []

    def handle(request: httpx.Request) -> httpx.Response:
        requests.append(request)
        return httpx.Response(status, text="body-secret", headers={"Location": "https://secret.test"})

    mock_http(handle)
    scanner = DecisionsScanner(
        model="m",
        base_url="https://assessment.test",
        questions=[{"type": "predicate", "name": "q", "instructions": "Assess"}],
        evaluator="application_policy.evaluate_answers",
    )
    # When / Then
    with pytest.raises(APIError) as error:
        scanner.scan("text")
    assert len(requests) == 1
    assert "secret" not in str(error.value)


@pytest.mark.parametrize(
    "url",
    [
        "https://user:secret@assessment.test",
        "https://assessment.test?key=secret",
        "https://assessment.test#secret",
        "file:///secret",
        "not-a-url",
    ],
)
def test_config_error_when_url_unsafe(url: str) -> None:
    # Given / When / Then
    with pytest.raises(APIConfigError) as error:
        DecisionsScanner(
            model="m",
            base_url=url,
            questions=[{"type": "predicate", "name": "q", "instructions": "Assess"}],
            evaluator="application_policy.evaluate_answers",
        )
    assert "secret" not in str(error.value)


def test_timeout_when_transport_fails(mock_http: MockHTTP) -> None:
    # Given
    requests: list[httpx.Request] = []

    def handle(request: httpx.Request) -> httpx.Response:
        requests.append(request)
        raise httpx.ReadTimeout("secret", request=request)

    mock_http(handle)
    scanner = DecisionsScanner(
        model="m",
        base_url="https://assessment.test",
        timeout=2,
        questions=[{"type": "predicate", "name": "q", "instructions": "Assess"}],
        evaluator="application_policy.evaluate_answers",
    )
    # When / Then
    with pytest.raises(APIError) as error:
        scanner.scan("text")
    assert requests[0].extensions["timeout"] == {"connect": 2, "read": 2, "write": 2, "pool": 2}
    assert len(requests) == 1
    assert "secret" not in str(error.value)
