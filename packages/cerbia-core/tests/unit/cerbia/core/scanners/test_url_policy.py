from pathlib import Path

import pytest
from cerbia.core.config import ScannerConfig
from cerbia.core.factories import ScannerFactory
from cerbia.core.models.scans import MatchSpan
from cerbia.core.registries.url import UrlRegistry
from cerbia.core.scanners import UrlAllowListScanner
from cerbia.core.types import Action, ContentType, Severity

pytestmark = pytest.mark.unit


@pytest.mark.parametrize("kind", ["allowlist", "denylist"])
@pytest.mark.parametrize("source", ["inline", "string", "path"])
def test_policy_matches_rules_when_single_source_is_configured(kind: str, source: str, tmp_path: Path) -> None:
    # Given
    path = tmp_path / "rules.txt"
    path.write_text("https://file.example/*\n", encoding="utf-8")
    key = "allowed_domains" if kind == "allowlist" else "blocked_domains"
    policy = ["https://inline.example/*"] if source == "inline" else str(path) if source == "string" else path
    scanner = ScannerFactory.build(
        ScannerConfig(
            scanner=f"cerbia.core.scanners.Url{kind.removesuffix('list').title()}ListScanner",
            init_args={key: policy},
        )
    )

    # When
    outcomes = [scanner.scan(f"https://{host}.example/docs") for host in ("inline", "file", "other")]

    # Then
    matches_policy = [source == "inline", source != "inline", False]
    assert [outcome.risk_score > 0 for outcome in outcomes] == [
        matched != (kind == "allowlist") for matched in matches_policy
    ]


@pytest.mark.parametrize("kind", ["allowlist", "denylist"])
def test_policy_requires_explicit_source_when_policy_is_omitted(kind: str) -> None:
    # Given
    config = ScannerConfig(scanner=f"cerbia.core.scanners.Url{kind.removesuffix('list').title()}ListScanner")
    # When / Then
    with pytest.raises(TypeError, match="required positional argument"):
        ScannerFactory.build(config)


@pytest.mark.parametrize("kind", ["allowlist", "denylist"])
@pytest.mark.parametrize("file_only", [False, True])
def test_policy_has_zero_rules_when_source_is_explicitly_empty(kind: str, file_only: bool, tmp_path: Path) -> None:
    # Given
    path = tmp_path / "empty.txt"
    path.write_text("\n # comment\n", encoding="utf-8")
    key = "allowed_domains" if kind == "allowlist" else "blocked_domains"
    args = {key: path if file_only else []}
    scanner = ScannerFactory.build(
        ScannerConfig(scanner=f"cerbia.core.scanners.Url{kind.removesuffix('list').title()}ListScanner", init_args=args)
    )
    # When
    outcome = scanner.scan("https://example.com/")
    # Then
    assert outcome.risk_score == (0.95 if kind == "allowlist" else 0.0)
    assert scanner.scan("no links").matches == []


@pytest.mark.parametrize("kind", ["allowlist", "denylist"])
def test_policy_preserves_original_spans_when_urls_repeat_with_unicode_and_punctuation(kind: str) -> None:
    # Given
    key = "allowed_domains" if kind == "allowlist" else "blocked_domains"
    rules = ["https://safe.example/*"] if kind == "allowlist" else ["https://xn--bcher-kva.example/docs"]
    scanner = ScannerFactory.build(
        ScannerConfig(
            scanner=f"cerbia.core.scanners.Url{kind.removesuffix('list').title()}ListScanner",
            init_args={key: rules},
        )
    )
    url = "HTTPS://user:pass@BÜCHER.example/a/../docs?q=é#frag"
    text = f"前🙂 ({url}), https://safe.example/; {url}!"
    first = text.index(url)
    last = text.rindex(url)
    # When
    outcome = scanner.scan(text)
    # Then
    assert outcome.risk_score == 0.95
    assert outcome.matches == [MatchSpan(start=first, end=first + len(url)), MatchSpan(start=last, end=last + len(url))]
    assert [text[span.start : span.end] for span in outcome.matches] == [url, url]
    assert "https://xn--bcher-kva.example/docs" in outcome.rationale
    if kind == "denylist":
        assert "allowlist" not in outcome.rationale


@pytest.mark.parametrize("kind", ["allowlist", "denylist"])
@pytest.mark.parametrize(
    ("rule", "url", "matched"),
    [
        ("*://*.example.com/*", "sftp://sub.example.com/file", True),
        ("https://example.com/docs", "HTTPS://u:p@EXAMPLE.COM/a/../docs?q=1#frag", True),
        ("https://example.com/docs", "https://example.com/docs/child", False),
        ("https://example.com/docs", "http://example.com/docs", False),
        ("https://example.com:8443/*", "https://example.com:8443/docs", True),
        ("https://example.com/*", "https://example.com.evil/docs", False),
        ("not a URL [literal]", "https://example.com/", False),
        ("https://example.com/*", "https://[broken", False),
    ],
)
def test_policy_uses_existing_grammar_when_matching(kind: str, rule: str, url: str, matched: bool) -> None:
    # Given
    key = "allowed_domains" if kind == "allowlist" else "blocked_domains"
    scanner = ScannerFactory.build(
        ScannerConfig(
            scanner=f"cerbia.core.scanners.Url{kind.removesuffix('list').title()}ListScanner",
            init_args={key: [rule]},
        )
    )
    # When
    outcome = scanner.scan(url)
    # Then
    assert (outcome.risk_score > 0) == (matched != (kind == "allowlist"))


@pytest.mark.parametrize("file_policy", [False, True])
def test_allowlist_preserves_five_positional_slots_when_policy_is_configured(tmp_path: Path, file_policy: bool) -> None:
    # Given
    path = tmp_path / "rules.txt"
    path.write_text("https://file.example/*", encoding="utf-8")
    registry = UrlRegistry(["https://legacy.example/*"])
    # When
    scanner = UrlAllowListScanner(
        path if file_policy else ["https://file.example/*"], Severity.LOW, Action.WARN, registry, None
    )
    # Then
    assert (scanner.severity, scanner.action, scanner.content_types) == (Severity.LOW, Action.WARN, None)
    assert scanner._url_registry is registry
    assert scanner.scan("https://legacy.example/docs https://file.example/docs").risk_score == 0.0
    assert registry.is_allowed("https://file.example/docs")


def test_denylist_preserves_configuration_when_built_by_factory() -> None:
    # Given
    config = ScannerConfig(
        scanner="cerbia.core.scanners.url_deny_list.UrlDenyListScanner",
        init_args={"blocked_domains": [], "severity": Severity.LOW, "action": Action.WARN, "content_types": ["url"]},
    )
    # When
    scanner = ScannerFactory.build(config)
    # Then
    assert (scanner.scanner_id, scanner.scanner_name) == ("url_denylist", "URL Denylist")
    assert (scanner.severity, scanner.action, scanner.content_types) == (Severity.LOW, Action.WARN, (ContentType.URL,))


def test_denylist_keeps_all_spans_when_finding_details_are_limited() -> None:
    # Given
    scanner = ScannerFactory.build(
        ScannerConfig(
            scanner="cerbia.core.scanners.UrlDenyListScanner",
            init_args={"blocked_domains": ["https://blocked.example/*"]},
        )
    )
    urls = [f"https://blocked.example/{index}" for index in range(6)]
    text = " ".join(urls)
    # When
    outcome = scanner.scan(text)
    # Then
    assert [text[span.start : span.end] for span in outcome.matches] == urls
    assert urls[-1] not in outcome.rationale
    assert (scanner.severity, scanner.action) == (Severity.HIGH, Action.BLOCK)
    assert scanner.content_types == (ContentType.TEXT, ContentType.URL, ContentType.CODE)


def test_denylist_returns_safe_outcome_when_text_has_no_urls() -> None:
    # Given
    scanner = ScannerFactory.build(
        ScannerConfig(scanner="cerbia.core.scanners.UrlDenyListScanner", init_args={"blocked_domains": ["*"]})
    )
    # When
    outcome = scanner.scan("no links")
    # Then
    assert outcome.risk_score == 0.0
    assert outcome.matches == []
