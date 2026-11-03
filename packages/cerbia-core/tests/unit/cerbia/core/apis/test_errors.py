import traceback
from typing import assert_never

import httpx
import pytest
from cerbia.core.apis import APIConfigError, APIError
from cerbia.core.apis._http import HTTPClient
from cerbia.core.apis.decisions import DecisionsClient, PredicateQuestion
from cerbia.core.apis.systemone import NoulQuestion, SystemOneClient
from cerbia.core.exceptions import CerbIAConfigError, CerbIAError


@pytest.mark.parametrize("status", [301, 307, 400, 401, 403, 429, 500])
def test_generic_error_without_retry_when_http_status_fails(status: int, monkeypatch: pytest.MonkeyPatch) -> None:
    # Given
    requests: list[httpx.Request] = []

    def handle(self: httpx.HTTPTransport, request: httpx.Request) -> httpx.Response:
        requests.append(request)
        return httpx.Response(status, text="response-secret", headers={"Location": "https://secret.test"})

    monkeypatch.setattr(httpx.HTTPTransport, "handle_request", handle)
    client = HTTPClient(base_url="https://api.test", endpoint_path="/generic", timeout=2)
    body = "request-secret"
    # When / Then
    with pytest.raises(APIError) as error:
        client.request(body)
    assert type(error.value) is APIError
    assert isinstance(error.value, CerbIAError)
    assert str(error.value) == "API request failed"
    assert error.value.__cause__ is None
    assert error.value.__suppress_context__
    assert "secret" not in "".join(traceback.format_exception(error.value))
    assert len(requests) == 1
    assert "Authorization" not in requests[0].headers


@pytest.mark.parametrize("error_type", [httpx.ReadTimeout, httpx.ConnectError, OSError, ValueError, TypeError])
def test_generic_error_when_transport_raises(error_type: type[Exception], monkeypatch: pytest.MonkeyPatch) -> None:
    # Given
    def handle(self: httpx.HTTPTransport, request: httpx.Request) -> httpx.Response:
        raise error_type("transport-secret")

    monkeypatch.setattr(httpx.HTTPTransport, "handle_request", handle)
    client = HTTPClient(base_url="https://api.test", endpoint_path="/generic", timeout=2)
    body = "request-secret"
    # When / Then
    with pytest.raises(APIError) as error:
        client.request(body)
    assert str(error.value) == "API request failed"
    assert error.value.__suppress_context__
    assert "secret" not in "".join(traceback.format_exception(error.value))


@pytest.mark.parametrize("client_type", [DecisionsClient, SystemOneClient])
@pytest.mark.parametrize("model", ["", None, True, 42, b"model-secret"])
def test_generic_config_error_when_protocol_model_invalid(
    client_type: type[DecisionsClient | SystemOneClient], model: str
) -> None:
    # Given / When / Then
    with pytest.raises(APIConfigError) as error:
        client_type(model=model)
    assert type(error.value) is APIConfigError
    assert isinstance(error.value, CerbIAConfigError)
    assert str(error.value) == "Invalid API configuration"
    assert error.value.__suppress_context__


@pytest.mark.parametrize("client_type", [DecisionsClient, SystemOneClient])
@pytest.mark.parametrize("text", [None, True, 42, b"text-secret"])
def test_generic_error_when_protocol_text_is_not_string(
    client_type: type[DecisionsClient | SystemOneClient], text: str, monkeypatch: pytest.MonkeyPatch
) -> None:
    # Given
    monkeypatch.setattr(httpx.HTTPTransport, "handle_request", lambda *args: pytest.fail("must not send"))
    client = client_type(model="m", base_url="https://api.test")
    # When / Then
    with pytest.raises(APIError) as error:
        match client:
            case DecisionsClient():
                client.ask(text, [PredicateQuestion(name="q", instructions="Assess")])
            case SystemOneClient():
                client.ask(text, {"q": NoulQuestion()})
            case unreachable:
                assert_never(unreachable)
    assert type(error.value) is APIError
    assert str(error.value) == "API request failed"
    assert error.value.__cause__ is None
    assert "secret" not in "".join(traceback.format_exception(error.value))


@pytest.mark.parametrize("client_type", [DecisionsClient, SystemOneClient])
def test_generic_error_when_protocol_response_malformed(
    client_type: type[DecisionsClient | SystemOneClient], monkeypatch: pytest.MonkeyPatch
) -> None:
    # Given
    monkeypatch.setattr(
        httpx.HTTPTransport, "handle_request", lambda self, request: httpx.Response(200, content=b"response-secret")
    )
    client = client_type(model="m", base_url="https://api.test")
    text = "request-secret"
    # When / Then
    with pytest.raises(APIError) as error:
        match client:
            case DecisionsClient():
                client.ask(text, [PredicateQuestion(name="q", instructions="Assess")])
            case SystemOneClient():
                client.ask(text, {"q": NoulQuestion()})
            case unreachable:
                assert_never(unreachable)
    assert type(error.value) is APIError
    assert str(error.value) == "API request failed"
    assert error.value.__suppress_context__
    assert "secret" not in "".join(traceback.format_exception(error.value))
