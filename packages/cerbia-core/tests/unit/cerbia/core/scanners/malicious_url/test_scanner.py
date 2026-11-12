import pytest
from cerbia.core.models.scans import MatchSpan
from cerbia.core.registries.url import UrlRegistry
from cerbia.core.scanners.malicious_url import MaliciousUrlScanner
from cerbia.core.score_aggregators import MeanScoreAggregator
from cerbia.core.security_gate import SimpleGate
from cerbia.core.types import Action, ContentType, Severity

pytestmark = pytest.mark.unit


def test_malicious_url_scanner_returns_safe_outcome_when_text_contains_no_urls() -> None:
    scanner = MaliciousUrlScanner()

    result = scanner.scan("No links are present.")

    assert result.risk_score == 0.0
    assert result.rationale == "No URLs found"
    assert result.matches == []


def test_malicious_url_scanner_returns_safe_outcome_when_url_has_no_indicators() -> None:
    scanner = MaliciousUrlScanner(
        suspicious_tlds=[],
        shortener_domains=[],
        popular_domains=[],
    )

    result = scanner.scan("https://example.com/docs")

    assert result.risk_score == 0.0
    assert result.rationale == "All 1 URL(s) appear safe"
    assert result.matches == []


def test_malicious_url_scanner_returns_safe_outcome_when_all_urls_are_allowlisted() -> None:
    registry = UrlRegistry(["https://example.com/*"])
    scanner = MaliciousUrlScanner(url_registry=registry)

    result = scanner.scan("https://example.com/docs")

    assert result.risk_score == 0.0
    assert result.rationale == "All URLs on allowlist"
    assert result.matches == []


def test_malicious_url_scanner_evaluates_unallowlisted_url_when_text_contains_mixed_urls() -> None:
    registry = UrlRegistry(["https://example.com/*"])
    scanner = MaliciousUrlScanner(suspicious_tlds=["xyz"], url_registry=registry)

    result = scanner.scan("https://example.com/docs https://evil.xyz/path")

    assert result.risk_score == 0.75
    assert result.rationale == "Suspicious URL(s) (1 flag(s)): Suspicious TLD (.xyz) (https://evil.xyz/path)"
    assert result.matches == [MatchSpan(start=25, end=46)]


def test_malicious_url_scanner_detects_data_uri_when_data_uri_is_present() -> None:
    scanner = MaliciousUrlScanner(redact=False)

    result = scanner.scan("data:text/html,<script>alert(1)</script>")

    assert result.risk_score == 0.9
    assert result.rationale == "Suspicious URL(s) (1 flag(s)): Data URI (data:text/html,<script>alert(1)</script>)"
    assert result.matches == [MatchSpan(start=0, end=14)]


@pytest.mark.parametrize(
    ("url", "scanner", "expected_reason", "expected_score"),
    [
        ("https://192.0.2.1/path", MaliciousUrlScanner(), "IP-based URL", 0.8),
        ("https://evil.xyz/path", MaliciousUrlScanner(suspicious_tlds=["xyz"]), "Suspicious TLD (.xyz)", 0.75),
        (
            "https://go.short.example/path",
            MaliciousUrlScanner(shortener_domains=["short.example"]),
            "URL shortener",
            0.7,
        ),
        (
            "https://example.com/?ReDiReCt=https://evil.example",
            MaliciousUrlScanner(redact=False),
            "Redirect param 'ReDiReCt'",
            0.8,
        ),
        ("https://xn--paypa-4ve.com/path", MaliciousUrlScanner(), "Punycode/IDN domain", 0.85),
        ("https://a.b.c.d.example.com/path", MaliciousUrlScanner(), "Excessive subdomains", 0.65),
        ("https://example.com/%00%01%02%03%04%05", MaliciousUrlScanner(), "URL-encoding obfuscation", 0.75),
        (
            "https://gooogle.com/path",
            MaliciousUrlScanner(popular_domains=["google.com"]),
            "Possible typosquatting of google.com",
            0.85,
        ),
    ],
    ids=[
        "ip_host",
        "suspicious_tld",
        "shortener_subdomain",
        "redirect_parameter",
        "punycode",
        "excessive_subdomains",
        "percent_encoding",
        "typosquatting",
    ],
)
def test_malicious_url_scanner_returns_finding_when_url_has_malicious_indicator(
    url: str, scanner: MaliciousUrlScanner, expected_reason: str, expected_score: float
) -> None:
    result = scanner.scan(url)

    assert result.risk_score == expected_score
    assert result.rationale == f"Suspicious URL(s) (1 flag(s)): {expected_reason} ({url})"
    assert result.matches == [MatchSpan(start=0, end=len(url))]


def test_malicious_url_scanner_emits_one_span_per_flagged_occurrence_when_multiple_heuristics_match() -> None:
    # Given
    scanner = MaliciousUrlScanner(suspicious_tlds=["xyz"], shortener_domains=["evil.xyz"])
    url = "HTTPS://EVIL.xyz/é"
    text = f"前🙂 ({url}), https://safe.example/docs; {url}!"
    # When
    result = scanner.scan(text)
    # Then
    assert result.risk_score == 0.75
    assert result.rationale.startswith("Suspicious URL(s) (4 flag(s)):")
    assert result.matches == [
        MatchSpan(start=text.index(url), end=text.index(url) + len(url)),
        MatchSpan(start=text.rindex(url), end=text.rindex(url) + len(url)),
    ]


def test_malicious_url_scanner_preserves_denied_url_span_when_matching_allow_rule_exists() -> None:
    # Given
    registry = UrlRegistry(["https://*.xyz/*"])
    registry.register("https://blocked.xyz/*", denied=True)
    scanner = MaliciousUrlScanner(suspicious_tlds=["xyz"], url_registry=registry)
    text = "https://allowed.xyz/doc (https://blocked.xyz/doc)."
    # When
    result = scanner.scan(text)
    # Then
    start = text.index("https://blocked")
    assert result.matches == [MatchSpan(start=start, end=start + len("https://blocked.xyz/doc"))]
    assert result.risk_score == 0.75


def test_malicious_url_scanner_uses_data_uri_match_span_when_payload_and_allowed_url_follow() -> None:
    # Given
    scanner = MaliciousUrlScanner(url_registry=UrlRegistry(["*"]))
    text = "前🙂 data: text/html,<svg>payload</svg> https://safe.example/"
    # When
    result = scanner.scan(text)
    # Then
    assert result.risk_score == 0.9
    assert result.matches == [MatchSpan(start=3, end=18)]


def test_malicious_url_scanner_keeps_data_uri_and_url_spans_when_both_are_detected() -> None:
    # Given
    scanner = MaliciousUrlScanner(suspicious_tlds=["xyz"])
    text = "data:text/html,payload https://evil.xyz/doc"
    # When
    result = scanner.scan(text)
    # Then
    assert result.risk_score == 0.9
    assert result.matches == [MatchSpan(start=0, end=14), MatchSpan(start=23, end=43)]


def test_malicious_url_scanner_uses_highest_score_and_limits_rationale_to_first_five_flags() -> None:
    scanner = MaliciousUrlScanner(suspicious_tlds=["xyz"], shortener_domains=["evil.xyz"])

    result = scanner.scan("https://192.0.2.1/?redirect=https://evil.xyz https://evil.xyz/%00%01%02%03%04%05")

    assert result.risk_score == 0.8
    assert result.rationale.startswith("Suspicious URL(s) (5 flag(s)):")
    assert "IP-based URL" in result.rationale
    assert "Redirect param 'redirect'" in result.rationale


def test_malicious_url_scanner_preserves_configuration_when_custom_values_are_provided() -> None:
    registry = UrlRegistry()
    scanner = MaliciousUrlScanner(
        severity=Severity.CRITICAL,
        action=Action.WARN,
        suspicious_tlds=["custom"],
        shortener_domains=["short.example"],
        popular_domains=["popular.example"],
        url_registry=registry,
        content_types=[ContentType.URL],
    )

    assert scanner.scanner_id == "url_malicious"
    assert scanner.scanner_name == "Malicious URL"
    assert scanner.severity is Severity.CRITICAL
    assert scanner.action is Action.WARN
    assert scanner.content_types == (ContentType.URL,)
    assert scanner._suspicious_tlds == frozenset(["custom"])
    assert scanner._shortener_domains == frozenset(["short.example"])
    assert scanner._popular_domains == frozenset(["popular.example"])
    assert scanner._url_registry is registry


@pytest.mark.parametrize("redact", [None, True, False], ids=["default", "enabled", "legacy"])
@pytest.mark.parametrize("credentials", ["user:password", "user:" + "secret" * 15])
def test_formats_full_url_before_truncating_when_credentials_are_present(redact: bool | None, credentials: str) -> None:
    # Given
    scanner = MaliciousUrlScanner() if redact is None else MaliciousUrlScanner(redact=redact)
    url = f"https://{credentials}@evil.xyz:8443/retained/path?token=query-secret#fragment-secret"
    display = url[:60] if redact is False else "https://evil.xyz:8443/retained/path"
    # When
    result = scanner.scan(url)
    # Then
    assert result.rationale == f"Suspicious URL(s) (1 flag(s)): Suspicious TLD (.xyz) ({display})"


@pytest.mark.parametrize("redact", [None, True, False], ids=["default", "enabled", "legacy"])
@pytest.mark.parametrize("payload", ["payload adjacent-secret", "x" * 80 + " adjacent-secret"])
def test_hides_payload_and_adjacent_text_when_data_uri_is_detected(redact: bool | None, payload: str) -> None:
    # Given
    scanner = MaliciousUrlScanner() if redact is None else MaliciousUrlScanner(redact=redact)
    text = f"prefix data:text/html,{payload}"
    display = text[7:67] if redact is False else "[REDACTED]"
    # When
    result = scanner.scan(text)
    # Then
    assert result.rationale == f"Suspicious URL(s) (1 flag(s)): Data URI ({display})"


@pytest.mark.parametrize("redact", [True, False])
@pytest.mark.parametrize(
    ("url", "reason"),
    [
        ("https://user:password@[broken/path?token=secret#fragment", "Unparseable URL"),
        ("https://user:password@evil.xyz:bad/path?token=secret#fragment", "Suspicious TLD (.xyz)"),
        ("https://user:password@evil.xyz:99999/path?token=secret#fragment", "Suspicious TLD (.xyz)"),
    ],
)
def test_uses_placeholder_when_flagged_url_is_invalid(redact: bool, url: str, reason: str) -> None:
    # Given
    scanner = MaliciousUrlScanner(redact=redact)
    display = "[REDACTED URL]" if redact else url[:60]
    # When
    result = scanner.scan(url)
    # Then
    assert result.rationale == f"Suspicious URL(s) (1 flag(s)): {reason} ({display})"


@pytest.mark.parametrize(
    ("port", "safe_display"),
    [
        pytest.param("9" * 5000, "[REDACTED URL]", id="5000-digit-port"),
        pytest.param("65535", "https://evil.xyz:65535/path", id="maximum-valid-port"),
        pytest.param("65536", "[REDACTED URL]", id="first-invalid-port"),
    ],
)
def test_preserves_detection_when_port_formatting_changes(port: str, safe_display: str) -> None:
    # Given
    url = f"https://user:password@evil.xyz:{port}/path?token=secret#fragment"
    safe_scanner = MaliciousUrlScanner(redact=True)
    legacy_scanner = MaliciousUrlScanner(redact=False)
    # When
    safe = safe_scanner.scan(url)
    legacy = legacy_scanner.scan(url)
    # Then
    assert safe.rationale == f"Suspicious URL(s) (1 flag(s)): Suspicious TLD (.xyz) ({safe_display})"
    assert legacy.rationale == f"Suspicious URL(s) (1 flag(s)): Suspicious TLD (.xyz) ({url[:60]})"
    assert safe.risk_score == legacy.risk_score == 0.75
    assert safe.matches == legacy.matches == [MatchSpan(start=0, end=len(url))]


@pytest.mark.parametrize("redact", [True, False])
def test_canonicalizes_redirect_reason_only_when_redaction_is_enabled(redact: bool) -> None:
    # Given: mixed-case query spelling must not be echoed back in safe mode.
    scanner = MaliciousUrlScanner(redact=redact)
    url = "https://example.com/path?ReDiReCt=query-secret#fragment-secret"
    reason = "redirect" if redact else "ReDiReCt"
    display = "https://example.com/path" if redact else url[:60]
    # When
    result = scanner.scan(url)
    # Then
    assert result.rationale == f"Suspicious URL(s) (1 flag(s)): Redirect param '{reason}' ({display})"


def test_preserves_detection_and_first_five_flags_when_redaction_changes() -> None:
    # Given
    text = (
        "data:text/html,payload https://user:password@192.0.2.1:8443/path?ReDiReCt=secret#fragment "
        "https://evil.xyz/%00%01%02%03%04%05 https://gooogle.com/path"
    )
    safe_scanner = MaliciousUrlScanner(shortener_domains=["evil.xyz"])
    legacy_scanner = MaliciousUrlScanner(shortener_domains=["evil.xyz"], redact=False)
    legacy = legacy_scanner.scan(text)
    # When
    result = safe_scanner.scan(text)
    # Then
    assert result.model_dump(exclude={"rationale"}) == legacy.model_dump(exclude={"rationale"})
    assert result.risk_score == 0.9
    assert len(result.matches) == 4
    assert result.rationale == (
        "Suspicious URL(s) (7 flag(s)): Data URI ([REDACTED]); "
        "IP-based URL (https://192.0.2.1:8443/path); "
        "Redirect param 'redirect' (https://192.0.2.1:8443/path); "
        "Suspicious TLD (.xyz) (https://evil.xyz/%00%01%02%03%04%05); "
        "URL shortener (https://evil.xyz/%00%01%02%03%04%05)"
    )


def test_retains_typosquat_reason_when_sensitive_url_components_are_removed() -> None:
    # Given
    scanner = MaliciousUrlScanner(popular_domains=["google.com"])
    # When
    result = scanner.scan("https://user:password@gooogle.com/path?token=secret#fragment")
    # Then
    assert result.rationale == (
        "Suspicious URL(s) (1 flag(s)): Possible typosquatting of google.com (https://gooogle.com/path)"
    )


def test_preserves_positional_arguments_when_redact_is_appended() -> None:
    # Given
    scanner = MaliciousUrlScanner(Severity.LOW, Action.WARN, ["xyz"], [], [], None, [ContentType.URL], False)
    url = "https://user:password@evil.xyz/path?token=secret#fragment"
    # When
    result = scanner.scan(url)
    # Then
    assert scanner.severity is Severity.LOW
    assert scanner.action is Action.WARN
    assert scanner.content_types == (ContentType.URL,)
    assert result.rationale == f"Suspicious URL(s) (1 flag(s)): Suspicious TLD (.xyz) ({url[:60]})"


@pytest.mark.parametrize("redact", [None, True, False], ids=["default", "enabled", "legacy"])
@pytest.mark.parametrize(
    ("text", "candidates"),
    [
        ("data:text/html,https://evil.xyz/privatepayload", [("https://evil.xyz/privatepayload", True)]),
        (
            "data:text/html,first data:image/svg+xml,https://evil.xyz/privatepayload",
            [("https://evil.xyz/privatepayload", True)],
        ),
        (
            "data:text/html,https://evil.xyz/first data:text/html,https://evil.xyz/second",
            [("https://evil.xyz/first", True), ("https://evil.xyz/second", True)],
        ),
        (
            "data:text/html,https://evil.xyz/privatepayload https://evil.xyz/public",
            [("https://evil.xyz/privatepayload", True), ("https://evil.xyz/public", False)],
        ),
        *[
            (
                f"<a href={quote}data:text/html,https://evil.xyz/privatepayload{quote}>https://evil.xyz/public</a>",
                [("https://evil.xyz/privatepayload", True), ("https://evil.xyz/public", False)],
            )
            for quote in ["'", '"']
        ],
        *[
            (
                f"data: text/html,payload{boundary}https://evil.xyz/public",
                [("https://evil.xyz/public", False)],
            )
            for boundary in [" ", "\t", "\n", "<", ">"]
        ],
        (
            "https://evil.xyz/data:text/html,privatepayload",
            [("https://evil.xyz/data:text/html,privatepayload", True)],
        ),
        (
            "data:text/html,data:image/svg+xml,https://evil.xyz/privatepayload",
            [("https://evil.xyz/privatepayload", True)],
        ),
        (
            " ".join(f"data:text/html,https://evil.xyz/private{i}" for i in range(6)),
            [(f"https://evil.xyz/private{i}", True) for i in range(6)],
        ),
    ],
)
def test_masks_intersecting_url_displays_when_data_uri_contains_urls(
    redact: bool | None, text: str, candidates: list[tuple[str, bool]]
) -> None:
    # Given
    scanner = MaliciousUrlScanner() if redact is None else MaliciousUrlScanner(redact=redact)
    legacy = MaliciousUrlScanner(redact=False).scan(text)
    start = text.index("data:")
    displays = ["[REDACTED]" if hidden and redact is not False else url[:60] for url, hidden in candidates]
    data_display = text[start : start + 60] if redact is False else "[REDACTED]"
    details = [f"Data URI ({data_display})", *[f"Suspicious TLD (.xyz) ({display})" for display in displays]]
    # When
    result = scanner.scan(text)
    # Then
    assert result.rationale == f"Suspicious URL(s) ({len(details)} flag(s)): " + "; ".join(details[:5])
    assert result.model_dump(exclude={"rationale"}) == legacy.model_dump(exclude={"rationale"})
    assert legacy.rationale == (
        f"Suspicious URL(s) ({len(details)} flag(s)): Data URI ({text[start : start + 60]}); "
        + "; ".join(f"Suspicious TLD (.xyz) ({url[:60]})" for url, _ in candidates[:4])
    )


@pytest.mark.parametrize("redact", [None, True, False], ids=["default", "enabled", "legacy"])
def test_promotes_private_data_uri_display_to_public_finding_and_summary(redact: bool | None) -> None:
    # Given
    scanner = MaliciousUrlScanner() if redact is None else MaliciousUrlScanner(redact=redact)
    text = "data:text/html,https://evil.xyz/privatepayload https://evil.xyz/public"
    gate = SimpleGate("privacy", [scanner], MeanScoreAggregator())
    display = "https://evil.xyz/privatepayload" if redact is False else "[REDACTED]"
    data_display = text[:60] if redact is False else "[REDACTED]"
    expected = (
        f"Suspicious URL(s) (3 flag(s)): Data URI ({data_display}); "
        f"Suspicious TLD (.xyz) ({display}); Suspicious TLD (.xyz) (https://evil.xyz/public)"
    )
    # When
    verdict = gate.scan(text)
    # Then
    assert not verdict.is_safe
    assert len(verdict.findings) == 1
    assert verdict.findings[0].rationale == expected
    assert verdict.rationale == f"Malicious URL: {expected}"
    assert verdict.findings[0].matches == [
        MatchSpan(start=0, end=14),
        MatchSpan(start=15, end=46),
        MatchSpan(start=47, end=len(text)),
    ]
