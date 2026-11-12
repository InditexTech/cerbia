import re

import pytest
from cerbia.core.scanners.keyword import KeywordScanner
from cerbia.core.scanners.keyword._types import MatchStrategy
from cerbia.core.types import Action, ContentType, Severity

pytestmark = pytest.mark.unit


@pytest.mark.parametrize(
    ("text", "expected_name", "expected_snippet"),
    [
        ("Please exec(command)", "Code Execution", "exec"),
        ("Run import os to inspect the environment", "OS Command", "import os"),
    ],
    ids=["code_execution", "os_command"],
)
def test_keyword_scanner_detects_default_code_pattern_when_suspicious_code_is_provided(
    text: str, expected_name: str, expected_snippet: str
) -> None:
    scanner = KeywordScanner(languages=[], redact=False)

    result = scanner.scan(text)

    assert result.risk_score == pytest.approx(0.85)
    assert result.rationale == f"Suspicious keyword(s) (1): {expected_name} ('{expected_snippet}')"


def test_keyword_scanner_returns_safe_outcome_when_keyword_is_not_detected() -> None:
    scanner = KeywordScanner(languages=[])

    result = scanner.scan("The documentation contains no executable instructions.")

    assert result.risk_score == 0.0
    assert result.rationale == "No suspicious keywords found"


def test_keyword_scanner_loads_i18n_patterns_when_configured_language_patterns_are_available(mocker) -> None:
    instruction_pattern = re.compile(r"ignore previous instructions", re.IGNORECASE)
    get_patterns = mocker.patch("cerbia.core.scanners.keyword._scanner.get_patterns")
    get_patterns.side_effect = [
        {"keyword_instruction_override": [instruction_pattern]},
        {"defensive_context": []},
    ]

    scanner = KeywordScanner(languages=["en"], redact=False)
    result = scanner.scan("Ignore previous instructions")

    assert result.risk_score == pytest.approx(0.85)
    assert result.rationale == "Suspicious keyword(s) (1): Instruction Override ('Ignore previous instructions')"
    assert get_patterns.call_args_list == [
        mocker.call(languages=["en"], keys=KeywordScanner.i18n_keys),
        mocker.call(languages=["en"], keys=["defensive_context"]),
    ]


@pytest.mark.parametrize(
    ("match_strategy", "text", "expected_rationale"),
    [
        (MatchStrategy.SEARCH, "token token", "Suspicious keyword(s) (1): Internal Token ('token')"),
        (
            MatchStrategy.ALL,
            "token token",
            "Suspicious keyword(s) (2): Internal Token ('token'); Internal Token ('token')",
        ),
        (MatchStrategy.FULL_MATCH, "token", "Suspicious keyword(s) (1): Internal Token ('token')"),
        (MatchStrategy.FULL_MATCH, "prefix token", "No suspicious keywords found"),
    ],
    ids=["search_first_match", "all_matches", "full_match", "incomplete_full_match"],
)
def test_keyword_scanner_applies_configured_match_strategy_when_extra_pattern_is_provided(
    match_strategy: MatchStrategy, text: str, expected_rationale: str
) -> None:
    scanner = KeywordScanner(
        languages=[], extra_patterns=[("Internal Token", r"token")], match_strategy=match_strategy, redact=False
    )

    result = scanner.scan(text)

    assert result.rationale == expected_rationale


def test_keyword_scanner_skips_match_when_defensive_context_is_detected(mocker) -> None:
    is_in_defensive_context = mocker.patch(
        "cerbia.core.scanners.keyword._scanner.is_in_defensive_context", return_value=True
    )
    scanner = KeywordScanner(languages=[], extra_patterns=[("Internal Token", r"token")])

    result = scanner.scan("token")

    assert result.risk_score == 0.0
    assert result.rationale == "No suspicious keywords found"
    is_in_defensive_context.assert_called_once()


def test_keyword_scanner_redacts_matching_snippet_when_redaction_is_enabled() -> None:
    scanner = KeywordScanner(languages=[], extra_patterns=[("Internal Token", r"token")], redact=True)

    result = scanner.scan("token")

    assert result.risk_score == pytest.approx(0.85)
    assert result.rationale == "Suspicious keyword(s) (1): Internal Token ('[REDACTED]')"


def test_keyword_scanner_caps_risk_and_limits_rationale_to_first_five_hits() -> None:
    extra_patterns = [
        ("Pattern One", "patternone"),
        ("Pattern Two", "patterntwo"),
        ("Pattern Three", "patternthree"),
        ("Pattern Four", "patternfour"),
        ("Pattern Five", "patternfive"),
        ("Pattern Six", "patternsix"),
    ]
    scanner = KeywordScanner(
        languages=[], extra_patterns=extra_patterns, match_strategy=MatchStrategy.ALL, redact=False
    )

    result = scanner.scan("patternone patterntwo patternthree patternfour patternfive patternsix")

    assert result.risk_score == 1.0
    assert result.rationale == (
        "Suspicious keyword(s) (6): Pattern One ('patternone'); Pattern Two ('patterntwo'); "
        "Pattern Three ('patternthree'); Pattern Four ('patternfour'); Pattern Five ('patternfive')"
    )


def test_keyword_scanner_preserves_configuration_when_custom_values_are_provided() -> None:
    scanner = KeywordScanner(
        languages=[],
        match_strategy=MatchStrategy.ALL,
        redact=True,
        severity=Severity.CRITICAL,
        action=Action.WARN,
        content_types=[ContentType.TEXT, ContentType.CODE],
    )

    assert scanner.scanner_id == "keyword"
    assert scanner.scanner_name == "Keyword"
    assert scanner.severity is Severity.CRITICAL
    assert scanner.action is Action.WARN
    assert scanner.content_types == (ContentType.TEXT, ContentType.CODE)
    assert scanner._match_strategy is MatchStrategy.ALL
    assert scanner._redact


@pytest.mark.parametrize("redact", [None, True], ids=["default", "explicit"])
@pytest.mark.parametrize("text", ["privatepayload", "ｐｒｉｖａｔｅｐａｙｌｏａｄ", "pr1v4t3p4yl04d"])
def test_keyword_omits_normalized_excerpt_when_redaction_is_enabled(redact: bool | None, text: str) -> None:
    # Given
    patterns = [("Trusted Label", "privatepayload")]
    scanner = (
        KeywordScanner(languages=[], extra_patterns=patterns)
        if redact is None
        else KeywordScanner(languages=[], extra_patterns=patterns, redact=redact)
    )

    # When
    result = scanner.scan(text)

    # Then
    assert result.risk_score == pytest.approx(0.85)
    for rendered in (str(result.model_dump()), result.model_dump_json(), repr(result)):
        assert "privatepayload" not in rendered
        assert text not in rendered
        assert "Trusted Label ('[REDACTED]')" in rendered


@pytest.mark.parametrize("redact", [None, True, False], ids=["default", "explicit", "legacy"])
def test_keyword_preserves_detection_and_limits_across_redaction_modes(redact: bool | None) -> None:
    # Given
    snippet = "privatepayload" + "z" * 50
    patterns = [(f"Label {letter}", snippet) for letter in "abcdef"]
    legacy = KeywordScanner(languages=[], extra_patterns=patterns, redact=False).scan(snippet)
    scanner = (
        KeywordScanner(languages=[], extra_patterns=patterns)
        if redact is None
        else KeywordScanner(languages=[], extra_patterns=patterns, redact=redact)
    )

    # When
    result = scanner.scan(snippet)

    # Then
    assert result.model_dump(exclude={"rationale"}) == legacy.model_dump(exclude={"rationale"})
    excerpt = snippet[:40] if redact is False else "[REDACTED]"
    details = "; ".join(f"Label {letter} ('{excerpt}')" for letter in "abcde")
    assert result.rationale == f"Suspicious keyword(s) (6): {details}"


def test_keyword_preserves_trusted_custom_label_when_redacting_excerpt() -> None:
    # Given
    scanner = KeywordScanner(languages=[], extra_patterns=[("privatepayload", "privatepayload")])

    # When
    result = scanner.scan("privatepayload")

    # Then
    assert result.rationale == "Suspicious keyword(s) (1): privatepayload ('[REDACTED]')"


def test_keyword_preserves_normalized_excerpt_when_redaction_is_disabled() -> None:
    # Given
    scanner = KeywordScanner(
        languages=[],
        extra_patterns=[("Trusted Label", "privatepayload")],
        match_strategy=MatchStrategy.ALL,
        redact=False,
    )

    # When
    result = scanner.scan("ｐｒｉｖａｔｅｐａｙｌｏａｄ pr1v4t3p4yl04d")

    # Then
    assert result.rationale == (
        "Suspicious keyword(s) (2): Trusted Label ('privatepayload'); Trusted Label ('privatepayload')"
    )
