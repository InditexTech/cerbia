from collections.abc import Callable

import httpx
import pytest


@pytest.fixture
def mock_http(monkeypatch: pytest.MonkeyPatch) -> Callable[[Callable[[httpx.Request], httpx.Response]], None]:
    def install(handler: Callable[[httpx.Request], httpx.Response]) -> None:
        monkeypatch.setattr(httpx.HTTPTransport, "handle_request", lambda self, request: handler(request))

    return install
