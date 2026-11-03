import importlib
from collections.abc import Callable
from math import isfinite
from urllib.parse import urlsplit

import httpx

from .exceptions import APIConfigError, APIError


class HTTPClient:
    """Send bounded JSON POST requests without retries, redirects, environment credentials, or logs.

    Args:
        base_url (str | None): HTTP or HTTPS base URL to append the endpoint path to. If ``None``, construction
            succeeds but requests fail with APIError until a URL is configured through a new client.
        endpoint_path (str): Absolute endpoint path without a scheme, host, query, fragment, or backslash.
        timeout (float): Finite, positive timeout in seconds for HTTP operations.
        api_key_provider (str | None): Dotted import path to a zero-argument callable returning an API key. The
            callable is imported during construction and invoked for every request. Defaults to ``None``, which
            sends no Authorization header.

    Raises:
        APIConfigError: If the timeout, endpoint path, base URL, provider import, or provider callability is invalid.
            External failure details are redacted.
    """

    def __init__(
        self,
        *,
        base_url: str | None,
        endpoint_path: str,
        timeout: float,
        api_key_provider: str | None = None,
    ) -> None:
        try:
            if not isfinite(timeout) or timeout <= 0:
                raise ValueError("Invalid timeout")

            path = urlsplit(endpoint_path)
            if (
                not endpoint_path.startswith("/")
                or endpoint_path.startswith("//")
                or path.scheme
                or path.netloc
                or path.query
                or path.fragment
                or "?" in endpoint_path
                or "#" in endpoint_path
                or "\\" in endpoint_path
            ):
                raise ValueError("Invalid endpoint path")

            self._url: str | None = None
            if base_url is not None:
                url = httpx.URL(base_url)
                if (
                    url.scheme not in {"http", "https"}
                    or not url.host
                    or url.userinfo
                    or url.query
                    or url.fragment
                    or "?" in base_url
                    or "#" in base_url
                    or "\\" in base_url
                ):
                    raise ValueError("Invalid base URL")

                self._url = str(url).rstrip("/") + endpoint_path

        except (ValueError, TypeError, httpx.InvalidURL):
            raise APIConfigError() from None

        self._timeout = timeout
        self._api_key_provider: Callable[[], str] | None = None

        if api_key_provider is not None:
            try:
                module_path, _, name = api_key_provider.rpartition(".")
                if not module_path or not name:
                    raise APIConfigError()

                provider: Callable[[], str] = getattr(importlib.import_module(module_path), name)
                if not callable(provider):
                    raise APIConfigError()

                self._api_key_provider = provider

            except Exception:
                raise APIConfigError() from None

    def request(self, body: str) -> bytes:
        """Send one JSON POST request and redact external callback and HTTP failure details.

        Args:
            body (str): Serialized JSON request body to send without further serialization.

        Returns:
            bytes: Response body from a successful HTTP request.

        Raises:
            APIError: If no base URL is configured, credential resolution fails or returns an invalid key, header
                preparation fails, the network request fails, or the response has an unsuccessful HTTP status.
                External failure details are redacted.
        """
        if self._url is None:
            raise APIError() from None

        headers = {"Content-Type": "application/json"}

        try:
            if self._api_key_provider is not None:
                key = self._api_key_provider()
                if not isinstance(key, str) or not key.strip():
                    raise APIError()

                headers["Authorization"] = f"Bearer {key}"

        except Exception:
            raise APIError() from None

        try:
            if any("\r" in value or "\n" in value for value in headers.values()):
                raise httpx.LocalProtocolError("Invalid header value")

            response = httpx.post(self._url, content=body, headers=headers, timeout=self._timeout)
            response.raise_for_status()

            return response.content

        except (httpx.HTTPError, httpx.InvalidURL, ValueError, TypeError, OSError):
            raise APIError() from None
