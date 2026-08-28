import pytest
from cerbia.core.registries.url import UrlRegistry

pytestmark = pytest.mark.unit


@pytest.mark.parametrize(
    ("entry", "url"),
    [
        ("https://example.com/docs/*", "https://example.com/docs/start"),
        ("https://*.example.com/*", "https://api.example.com/path"),
        ("https://example.com:8443/*", "https://example.com:8443/path"),
        ("https://xn--bcher-kva.example/*", "https://bücher.example/path"),
        ("https://[2001:db8::1]/*", "https://[2001:DB8::1]/path"),
    ],
    ids=["path_wildcard", "subdomain_wildcard", "explicit_port", "internationalized_host", "ipv6_host"],
)
def test_url_registry_allows_url_when_registered_pattern_matches(entry: str, url: str) -> None:
    registry = UrlRegistry([entry])

    result = registry.is_allowed(url)

    assert result


@pytest.mark.parametrize(
    "url",
    [
        "not a URL",
        "https:///missing-host",
        "https://example.com:70000/path",
    ],
    ids=["plain_text", "missing_host", "invalid_port"],
)
def test_url_registry_rejects_url_when_url_cannot_be_normalized(url: str) -> None:
    registry = UrlRegistry(["https://example.com/*"])

    result = registry.is_allowed(url)

    assert not result


def test_url_registry_uses_normalized_url_when_credentials_query_and_fragment_are_provided() -> None:
    registry = UrlRegistry(["https://example.com/docs/page"])

    result = registry.is_allowed("HTTPS://user:pass@EXAMPLE.COM/docs/section/../page?query=value#fragment")

    assert result


def test_url_registry_ignores_entry_when_existing_pattern_covers_it() -> None:
    registry = UrlRegistry(["https://example.com/*"])
    registry.register("https://example.com/docs/*")

    assert len(registry._patterns) == 1
    assert registry.is_allowed("https://example.com/docs/page")


def test_url_registry_removes_existing_pattern_when_new_pattern_covers_it() -> None:
    registry = UrlRegistry(["https://example.com/docs/*"])
    registry.register("https://example.com/*")

    assert len(registry._patterns) == 1
    assert registry.is_allowed("https://example.com/other/page")


def test_url_registry_rejects_url_when_no_registered_pattern_matches() -> None:
    registry = UrlRegistry(["https://example.com/docs/*"])

    result = registry.is_allowed("https://example.com/other")

    assert not result
