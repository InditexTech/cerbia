import inspect
import traceback
from collections.abc import Callable

import httpx
import pytest
from cerbia.core.apis import APIConfigError, APIError
from cerbia.core.apis._http import HTTPClient
from cerbia.core.apis.decisions import DecisionsClient
from cerbia.core.apis.systemone import SystemOneClient
from cerbia.core.scanners import DecisionsScanner, SystemOneScanner


def test_auth_rotation_when_each_request_calls_imported_provider(monkeypatch: pytest.MonkeyPatch) -> None:
    # Given
    requests: list[httpx.Request] = []
    calls: list[int] = []

    def provider() -> str:
        calls.append(1)
        return f"secret-{len(calls)}"

    monkeypatch.setattr("uuid.uuid4", provider)
    monkeypatch.setattr(
        httpx.HTTPTransport,
        "handle_request",
        lambda self, request: requests.append(request) or httpx.Response(200, content=b"{}"),
    )
    http = HTTPClient(
        base_url="https://assessment.test", endpoint_path="/custom/evaluate", timeout=2, api_key_provider="uuid.uuid4"
    )
    assert calls == []
    monkeypatch.setattr("uuid.uuid4", lambda: pytest.fail("must resolve only once"))
    # When
    http.request("{}")
    http.request("{}")
    # Then
    assert calls == [1, 1]
    assert [request.headers["Authorization"] for request in requests] == ["Bearer secret-1", "Bearer secret-2"]
    assert requests[0].url.path == "/custom/evaluate"
    assert "secret" not in repr(http)


@pytest.mark.parametrize("error_type", [RuntimeError, ValueError, KeyError, OSError, TypeError])
def test_sanitized_error_when_provider_fails(error_type: type[Exception], monkeypatch: pytest.MonkeyPatch) -> None:
    # Given
    def provider() -> str:
        raise error_type("credential-secret")

    monkeypatch.setattr("uuid.uuid4", provider)
    monkeypatch.setattr(httpx.HTTPTransport, "handle_request", lambda *args: pytest.fail("must not send"))
    http = HTTPClient(
        base_url="https://assessment.test", endpoint_path="/v1/decisions", timeout=2, api_key_provider="uuid.uuid4"
    )
    # When / Then
    with pytest.raises(APIError) as error:
        http.request("{}")
    assert str(error.value) == "API request failed"
    assert error.value.__suppress_context__
    assert "credential-secret" not in "".join(traceback.format_exception(error.value))


@pytest.mark.parametrize("result", [None, 42, True, b"secret", {}, [], "", " \t\r\n"])
def test_sanitized_error_when_provider_result_invalid(result: object, monkeypatch: pytest.MonkeyPatch) -> None:
    # Given
    monkeypatch.setattr("uuid.uuid4", lambda: result)
    monkeypatch.setattr(httpx.HTTPTransport, "handle_request", lambda *args: pytest.fail("must not send"))
    http = HTTPClient(
        base_url="https://assessment.test", endpoint_path="/v1/decisions", timeout=2, api_key_provider="uuid.uuid4"
    )
    # When / Then
    with pytest.raises(APIError) as error:
        http.request("{}")
    assert str(error.value) == "API request failed"
    assert error.value.__suppress_context__


@pytest.mark.parametrize(
    "path",
    [
        "",
        "key-literal",
        ".provider",
        "uuid.",
        "missing_secret.module.key",
        "uuid.missing_secret",
        "uuid.NAMESPACE_DNS",
        b"uuid.uuid4",
        42,
        lambda: "secret",
    ],
)
def test_sanitized_config_error_when_provider_path_invalid(path: str) -> None:
    # Given / When / Then
    with pytest.raises(APIConfigError) as error:
        HTTPClient(base_url=None, endpoint_path="/custom", timeout=2, api_key_provider=path)
    assert str(error.value) == "Invalid API configuration"
    assert error.value.__suppress_context__
    assert "secret" not in "".join(traceback.format_exception(error.value))


def test_sanitized_config_error_when_module_execution_fails(monkeypatch: pytest.MonkeyPatch) -> None:
    # Given
    def fail(name: str) -> None:
        raise RuntimeError("module-secret")

    monkeypatch.setattr("importlib.import_module", fail)
    # When / Then
    with pytest.raises(APIConfigError) as error:
        HTTPClient(base_url=None, endpoint_path="/custom", timeout=2, api_key_provider="credentials.provider")
    assert "module-secret" not in "".join(traceback.format_exception(error.value))


def test_token_preserved_when_provider_returns_surrounding_spaces(monkeypatch: pytest.MonkeyPatch) -> None:
    # Given
    monkeypatch.setattr("uuid.uuid4", lambda: " secret ")
    requests: list[httpx.Request] = []
    monkeypatch.setattr(
        httpx.HTTPTransport,
        "handle_request",
        lambda self, request: requests.append(request) or httpx.Response(200, content=b"{}"),
    )
    http = HTTPClient(
        base_url="https://assessment.test", endpoint_path="/v1/decisions", timeout=2, api_key_provider="uuid.uuid4"
    )
    # When
    http.request("{}")
    # Then
    assert requests[0].headers["Authorization"] == "Bearer  secret "


@pytest.mark.parametrize("key", ["secret\r\nInjected: value", "secret\n", "secret\r"])
def test_sanitized_error_when_http_rejects_credential_newlines(key: str, monkeypatch: pytest.MonkeyPatch) -> None:
    # Given: prevent network access if credential validation regresses.
    monkeypatch.setattr("uuid.uuid4", lambda: key)
    monkeypatch.setattr(
        "httpcore._sync.connection_pool.ConnectionPool.handle_request", lambda *args: pytest.fail("must not send")
    )
    http = HTTPClient(
        base_url="https://assessment.test", endpoint_path="/v1/decisions", timeout=2, api_key_provider="uuid.uuid4"
    )
    # When / Then
    with pytest.raises(APIError) as error:
        http.request("{}")
    assert "secret" not in "".join(traceback.format_exception(error.value))


@pytest.mark.parametrize(
    "constructor", [HTTPClient, DecisionsClient, SystemOneClient, DecisionsScanner, SystemOneScanner]
)
def test_yaml_auth_surface_when_inspecting_constructor(constructor: Callable[..., object]) -> None:
    # Given / When
    parameters = inspect.signature(constructor).parameters
    # Then
    assert parameters["api_key_provider"].default is None
    assert not {"transport", "headers_resolver", "headers", "api_key"} & parameters.keys()


@pytest.mark.parametrize("constructor", [DecisionsClient, SystemOneClient])
def test_type_error_when_public_constructor_receives_endpoint_path(constructor: Callable[..., object]) -> None:
    # Given
    arguments = {"model": "m", "base_url": "https://assessment.test", "endpoint_path": "/custom/evaluate"}
    # When / Then: Python rejects the obsolete keyword before constructor validation.
    with pytest.raises(TypeError, match="unexpected keyword argument 'endpoint_path'"):
        constructor(**arguments)


@pytest.mark.parametrize("path", ["https://evil.test", "//evil.test", "/v1/x?key=secret", "/v1/x#secret", "", "x"])
def test_config_error_when_endpoint_path_unsafe(path: str) -> None:
    # Given / When / Then
    with pytest.raises(APIConfigError):
        HTTPClient(base_url="https://assessment.test", endpoint_path=path, timeout=2)


@pytest.mark.parametrize("timeout", [0, -1, float("nan"), float("inf")])
def test_config_error_when_timeout_invalid(timeout: float) -> None:
    # Given / When / Then
    with pytest.raises(APIConfigError):
        HTTPClient(base_url=None, endpoint_path="/custom", timeout=timeout)


def test_error_when_endpoint_is_not_configured() -> None:
    # Given
    http = HTTPClient(base_url=None, endpoint_path="/v1/decisions", timeout=2)
    # When / Then
    with pytest.raises(APIError):
        http.request("{}")


def test_no_fallback_when_rotating_provider_later_fails(
    monkeypatch: pytest.MonkeyPatch, caplog: pytest.LogCaptureFixture
) -> None:
    # Given
    keys = iter(["credential-secret", None])
    monkeypatch.setattr("uuid.uuid4", lambda: next(keys))
    requests: list[httpx.Request] = []
    monkeypatch.setattr(
        httpx.HTTPTransport,
        "handle_request",
        lambda self, request: requests.append(request) or httpx.Response(200, content=b"{}"),
    )
    http = HTTPClient(
        base_url="https://assessment.test", endpoint_path="/v1/decisions", timeout=2, api_key_provider="uuid.uuid4"
    )
    http.request("{}")
    # When / Then
    with pytest.raises(APIError):
        http.request("{}")
    assert len(requests) == 1
    assert "credential-secret" not in caplog.text
