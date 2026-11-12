from pathlib import Path

import pytest
from cerbia.core.models.scans import MatchSpan
from cerbia.core.registries.url import UrlRegistry
from cerbia.core.scanners.url_allow_list import UrlAllowListScanner
from cerbia.core.types import Action, ContentType, Severity

pytestmark = pytest.mark.unit


def test_url_allowlist_scanner_returns_safe_outcome_when_text_contains_no_urls() -> None:
    scanner = UrlAllowListScanner(["https://example.com/*"])

    result = scanner.scan("This text has no links.")

    assert result.risk_score == 0.0
    assert result.rationale == "No URLs found"
    assert result.matches == []


def test_url_allowlist_scanner_returns_safe_outcome_when_all_urls_are_allowed() -> None:
    scanner = UrlAllowListScanner(["https://example.com/*", "https://trusted.example/*"])

    result = scanner.scan("See https://example.com/docs and https://trusted.example/help.")

    assert result.risk_score == 0.0
    assert result.rationale == "All 2 URL(s) on allowlist"
    assert result.matches == []


def test_url_allowlist_scanner_returns_finding_when_url_is_not_allowed() -> None:
    scanner = UrlAllowListScanner(["https://example.com/*"])

    result = scanner.scan("See HTTPS://EVIL.EXAMPLE/path/../docs?query=value#fragment")

    assert result.risk_score == 0.95
    assert result.rationale == "URL(s) not on allowlist (1): https://evil.example/docs"
    assert result.matches == [MatchSpan(start=4, end=58)]


def test_url_allowlist_scanner_returns_only_unallowed_urls_when_text_contains_mixed_urls() -> None:
    scanner = UrlAllowListScanner(["https://example.com/*"])

    result = scanner.scan("https://example.com/docs https://evil.example/path")

    assert result.risk_score == 0.95
    assert result.rationale == "URL(s) not on allowlist (1): https://evil.example/path"


def test_url_allowlist_scanner_limits_finding_details_when_more_than_five_urls_are_unallowed() -> None:
    scanner = UrlAllowListScanner([])
    urls = " ".join(f"https://evil.example/{index}" for index in range(1, 7))

    result = scanner.scan(urls)

    assert result.risk_score == 0.95
    assert result.rationale == (
        "URL(s) not on allowlist (6): https://evil.example/1; https://evil.example/2; "
        "https://evil.example/3; https://evil.example/4; https://evil.example/5"
    )


def test_url_allowlist_scanner_registers_allowed_domains_with_shared_registry() -> None:
    registry = UrlRegistry()
    scanner = UrlAllowListScanner(["https://example.com/*"], url_registry=registry)

    result = scanner.scan("https://example.com/docs")

    assert scanner._url_registry is registry
    assert registry.is_allowed("https://example.com/docs")
    assert result.risk_score == 0.0


def test_url_allowlist_scanner_preserves_configuration_when_custom_values_are_provided() -> None:
    scanner = UrlAllowListScanner(
        ["https://example.com/*"],
        severity=Severity.CRITICAL,
        action=Action.WARN,
        content_types=[ContentType.URL],
    )

    assert scanner.scanner_id == "url_allowlist"
    assert scanner.scanner_name == "URL Allowlist"
    assert scanner.severity is Severity.CRITICAL
    assert scanner.action is Action.WARN
    assert scanner.content_types == (ContentType.URL,)


@pytest.mark.parametrize("source", ["inline", "string", "path"])
def test_allowlist_routes_supported_rule_sources(source: str, tmp_path: Path) -> None:
    path = tmp_path / "rules.txt"
    path.write_text("https://file.example/*\n", encoding="utf-8")

    if source == "inline":
        rules = ["https://file.example/*"]
    elif source == "string":
        rules = str(path)
    else:
        rules = path

    scanner = UrlAllowListScanner(rules)

    assert scanner.scan("https://file.example/doc").risk_score == 0.0
    assert scanner.scan("https://other.example/doc").risk_score == 0.95


def test_allowlist_preserves_original_spans_for_normalized_repeated_unicode_urls() -> None:
    scanner = UrlAllowListScanner(["https://safe.example/*"])
    url = "HTTPS://user:pass@BÜCHER.example/a/../docs?q=é#frag"
    text = f"前🙂 ({url}), https://safe.example/; {url}!"

    result = scanner.scan(text)

    assert [text[span.start : span.end] for span in result.matches] == [url, url]
    assert "https://xn--bcher-kva.example/docs" in result.rationale


@pytest.mark.parametrize("redact", [None, True, False], ids=["omitted", "enabled", "disabled"])
def test_allowlist_formats_invalid_url_when_redaction_is_configured(redact: bool | None) -> None:
    # Given
    url = "https://user:password@bad_host/path?token=secret#fragment"
    scanner = UrlAllowListScanner([]) if redact is None else UrlAllowListScanner([], redact=redact)

    # When
    result = scanner.scan(f"See {url}")

    # Then
    expected = url if redact is False else "[REDACTED URL]"
    assert result.rationale == f"URL(s) not on allowlist (1): {expected}"
    assert result.risk_score == 0.95
    assert result.matches == [MatchSpan(start=4, end=4 + len(url))]


@pytest.mark.parametrize("redact", [None, True, False], ids=["omitted", "enabled", "disabled"])
def test_allowlist_preserves_normalized_diagnostics_when_redaction_is_configured(redact: bool | None) -> None:
    # Given
    url = "HTTPS://user:password@EXAMPLE.COM:8443/path/../docs?token=secret#fragment"
    scanner = UrlAllowListScanner([]) if redact is None else UrlAllowListScanner([], redact=redact)

    # When
    result = scanner.scan(url)

    # Then
    assert result.rationale == "URL(s) not on allowlist (1): https://example.com:8443/docs"
    assert result.risk_score == 0.95
    assert result.matches == [MatchSpan(start=0, end=len(url))]
