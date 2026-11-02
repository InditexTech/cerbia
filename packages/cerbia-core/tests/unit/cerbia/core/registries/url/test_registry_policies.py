from pathlib import Path

import pytest
from cerbia.core.exceptions import CerbIAConfigError
from cerbia.core.registries.url import UrlRegistry
from cerbia.core.scanners import MaliciousUrlScanner, UrlAllowListScanner, UrlDenyListScanner

pytestmark = pytest.mark.unit


@pytest.mark.parametrize("denied", [False, True], ids=["allow", "deny"])
def test_registry_rejects_invalid_rule_when_existing_pattern_covers_it(denied: bool) -> None:
    # Given
    registry = UrlRegistry()
    registry.register("*", denied=denied)
    previous_rules = (registry._patterns.copy(), registry._denied_patterns.copy())
    # When / Then
    with pytest.raises(ValueError):
        registry.register("https://[invalid]/", denied=denied)
    assert (registry._patterns, registry._denied_patterns) == previous_rules


@pytest.mark.parametrize("denied", [False, True], ids=["allow", "deny"])
@pytest.mark.parametrize("preexisting", [False, True], ids=["earlier_line", "preexisting"])
def test_registry_rejects_invalid_file_rule_when_existing_pattern_covers_it(
    tmp_path: Path, denied: bool, preexisting: bool
) -> None:
    # Given
    path = tmp_path / "policy.txt"
    path.write_text("# policy\n*\nhttps://[invalid]/\n", encoding="utf-8")
    registry = UrlRegistry()
    if preexisting:
        registry.register("*", denied=denied)
    # When / Then
    with pytest.raises(CerbIAConfigError) as exc_info:
        registry.register_file(path, denied=denied)
    assert f"{path}:3:" in str(exc_info.value)
    assert isinstance(exc_info.value.__cause__, ValueError)
    assert [rule for rule, _ in registry._patterns] == ([] if denied else ["*"])
    assert [rule for rule, _ in registry._denied_patterns] == (["*"] if denied else [])
    assert registry.is_denied("https://example.com/") == denied
    assert registry.is_allowed("https://example.com/") == (not denied)


@pytest.mark.parametrize("denied", [False, True], ids=["allow", "deny"])
def test_registry_preserves_rules_when_invalid_pattern_would_cover_them(denied: bool) -> None:
    # Given
    registry = UrlRegistry()
    registry.register("https://[2001:db8::1]/*", denied=denied)
    previous_rules = (registry._patterns.copy(), registry._denied_patterns.copy())
    # When / Then
    with pytest.raises(ValueError):
        registry.register("https://[2001:db8::*]/*", denied=denied)
    assert (registry._patterns, registry._denied_patterns) == previous_rules
    assert registry.is_denied("https://[2001:db8::1]/doc") == denied
    assert registry.is_allowed("https://[2001:db8::1]/doc") == (not denied)


@pytest.mark.parametrize("deny_first", [False, True])
def test_registry_denies_overlap_when_rules_are_registered_in_either_order(deny_first: bool) -> None:
    # Given
    registry = UrlRegistry()
    # When
    for denied in [True, False] if deny_first else [False, True]:
        registry.register("https://example.com/private/*" if denied else "https://example.com/*", denied=denied)
    # Then
    assert registry.is_denied("HTTPS://user@EXAMPLE.COM/a/../private/doc?q=1#frag")
    assert not registry.is_allowed("https://example.com/private/doc")
    assert registry.is_allowed("https://example.com/public/doc")
    assert not registry.is_denied("https://example.com/public/doc")
    assert not registry.is_allowed("https://other.example/")


def test_registry_adds_only_denied_rules_when_file_targets_denied_store(tmp_path: Path) -> None:
    # Given
    path = tmp_path / "deny.txt"
    path.write_text("# comment\nhttps://blocked.example/*\n", encoding="utf-8")
    registry = UrlRegistry(["https://allowed.example/*"])
    # When
    registry.register_file(path, denied=True)
    # Then
    assert registry.is_denied("https://blocked.example/doc")
    assert not registry.is_allowed("https://blocked.example/doc")
    assert registry.is_allowed("https://allowed.example/doc")
    assert not registry.is_denied("https://allowed.example/doc")
    assert not registry.is_denied("https://[broken")


def test_scanners_share_policy_when_registry_is_injected() -> None:
    # Given
    registry = UrlRegistry()
    allow = UrlAllowListScanner(["https://*.xyz/*"], url_registry=registry)
    deny = UrlDenyListScanner(["https://blocked.xyz/*"], url_registry=registry)
    malicious = MaliciousUrlScanner(suspicious_tlds=["xyz"], url_registry=registry)
    # When
    outcomes = [scanner.scan("https://blocked.xyz/doc") for scanner in (allow, deny, malicious)]
    # Then
    assert allow._url_registry is deny._url_registry is malicious._url_registry is registry
    assert all(outcome.risk_score > 0 for outcome in outcomes)
    assert deny.scan("https://allowed.xyz/doc").risk_score == 0.0
    assert malicious.scan("https://allowed.xyz/doc").risk_score == 0.0


def test_scanners_create_private_registries_when_registry_is_omitted() -> None:
    # Given
    allow = UrlAllowListScanner(["*"])
    deny = UrlDenyListScanner(["*"])
    # When
    allowed = allow.scan("https://example.com/")
    denied = deny.scan("https://example.com/")
    # Then
    assert allow._url_registry is not deny._url_registry
    assert allowed.risk_score == 0.0
    assert denied.risk_score == 0.95
