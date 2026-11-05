import json
from collections.abc import Callable

import httpx2
import pytest
from cerbia.core.apis import decisions as api


@pytest.mark.parametrize("model,text", [("requested", "Untrusted text"), (" \t ", "")])
def test_typed_answers_when_client_asks_about_text(
    mock_http: Callable[[Callable[[httpx2.Request], httpx2.Response]], None],
    model: str,
    text: str,
) -> None:
    # Given
    question = api.PredicateQuestion(name="q", instructions="Assess text")
    answer = {"type": "predicate", "name": "q", "probability": 0.8}
    requests: list[httpx2.Request] = []

    def handle(request: httpx2.Request) -> httpx2.Response:
        requests.append(request)
        return httpx2.Response(
            200,
            json={
                "model": "resolved",
                "answers": [answer],
                "usage": {
                    "input_tokens": 1,
                    "output_tokens": 0,
                    "total_tokens": 1,
                    "input_tokens_details": {"cached_tokens": 0, "cache_write_tokens": 0},
                    "output_tokens_details": {"reasoning_tokens": 0},
                },
            },
        )

    mock_http(handle)
    client = api.DecisionsClient(model=model, base_url="https://assessment.test")
    # When
    response = client.ask(text, (question,))
    # Then
    assert isinstance(response, api.DecisionsResponse)
    assert response.model == "resolved"
    assert json.loads(requests[0].content) == {
        "model": model,
        "input": text,
        "questions": [question.model_dump(mode="json")],
    }
    assert requests[0].url.path == "/v1/decisions"
    assert "Authorization" not in requests[0].headers
    assert requests[0].headers["Content-Type"] == "application/json"
