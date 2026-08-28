import pytest
from cerbia.core.registries.url import UrlRegistry
from cerbia.core.scanners.malicious_url import MaliciousUrlScanner
from cerbia.core.scanners.url_allowlist import UrlAllowlistScanner
from cerbia.core.types import Action, ContentType, Severity

pytestmark = pytest.mark.unit


def test_url_allowlist_scanner_returns_safe_outcome_when_text_contains_no_urls() -> None:
    scanner = UrlAllowlistScanner(["https://example.com/*"])

    result = scanner.scan("This text has no links.")

    assert result.risk_score == 0.0
    assert result.rationale == "No URLs found"
    assert result.matches == []


def test_url_allowlist_scanner_returns_safe_outcome_when_all_urls_are_allowed() -> None:
    scanner = UrlAllowlistScanner(["https://example.com/*", "https://trusted.example/*"])

    result = scanner.scan("See https://example.com/docs and https://trusted.example/help.")

    assert result.risk_score == 0.0
    assert result.rationale == "All 2 URL(s) on allowlist"
    assert result.matches == []


def test_url_allowlist_scanner_returns_finding_when_url_is_not_allowed() -> None:
    scanner = UrlAllowlistScanner(["https://example.com/*"])

    result = scanner.scan("See HTTPS://EVIL.EXAMPLE/path/../docs?query=value#fragment")

    assert result.risk_score == 0.95
    assert result.rationale == "URL(s) not on allowlist (1): https://evil.example/docs"
    assert result.matches == []


def test_url_allowlist_scanner_returns_only_unallowed_urls_when_text_contains_mixed_urls() -> None:
    scanner = UrlAllowlistScanner(["https://example.com/*"])

    result = scanner.scan("https://example.com/docs https://evil.example/path")

    assert result.risk_score == 0.95
    assert result.rationale == "URL(s) not on allowlist (1): https://evil.example/path"


def test_url_allowlist_scanner_limits_finding_details_when_more_than_five_urls_are_unallowed() -> None:
    scanner = UrlAllowlistScanner([])
    urls = " ".join(f"https://evil.example/{index}" for index in range(1, 7))

    result = scanner.scan(urls)

    assert result.risk_score == 0.95
    assert result.rationale == (
        "URL(s) not on allowlist (6): https://evil.example/1; https://evil.example/2; "
        "https://evil.example/3; https://evil.example/4; https://evil.example/5"
    )


def test_url_allowlist_scanner_registers_allowed_domains_with_shared_registry() -> None:
    registry = UrlRegistry()
    scanner = UrlAllowlistScanner(["https://example.com/*"], url_registry=registry)

    result = scanner.scan("https://example.com/docs")

    assert scanner._url_registry is registry
    assert registry.is_allowed("https://example.com/docs")
    assert result.risk_score == 0.0


def test_url_allowlist_scanner_shares_registered_urls_with_malicious_scanner() -> None:
    registry = UrlRegistry()
    allowlist_scanner = UrlAllowlistScanner(["https://trusted.xyz/*"], url_registry=registry)
    malicious_scanner = MaliciousUrlScanner(suspicious_tlds=["xyz"], url_registry=registry)
    scanner_with_distinct_registry = MaliciousUrlScanner(suspicious_tlds=["xyz"], url_registry=UrlRegistry())

    allowlist_scanner.scan("https://trusted.xyz/docs")
    shared_result = malicious_scanner.scan("https://trusted.xyz/docs")
    distinct_registry_result = scanner_with_distinct_registry.scan("https://trusted.xyz/docs")

    assert shared_result.risk_score == 0.0
    assert shared_result.rationale == "All URLs on allowlist"
    assert distinct_registry_result.risk_score == 0.75
    assert distinct_registry_result.rationale == (
        "Suspicious URL(s) (1 flag(s)): Suspicious TLD (.xyz) (https://trusted.xyz/docs)"
    )


def test_url_allowlist_scanner_preserves_configuration_when_custom_values_are_provided() -> None:
    scanner = UrlAllowlistScanner(
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
