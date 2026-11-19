import re

import pytest
from cerbia.core.scanners.secret import SecretScanner

pytestmark = pytest.mark.unit


@pytest.mark.parametrize("key", ["secret", "password", "passwd", "pwd", "PASSWORD"])
@pytest.mark.parametrize("reference", ["${oc.env:DB_PASSWORD}", "${oc.env:_PASS2}", "${settings.password}"])
@pytest.mark.parametrize("quote", ["", "'", '"'])
def test_suppresses_assignment_when_entire_value_is_supported_reference(key: str, reference: str, quote: str) -> None:
    # Given
    text = f"{key} = {quote}{reference}{quote}"
    # When
    result = SecretScanner().scan(text)
    # Then
    assert result.matches == []
    assert result.risk_score == 0


@pytest.mark.parametrize(
    "value",
    [
        "${oc.env:PASS,default}",
        "${oc.env:PASS:-default}",
        "${oc.env:9PASS}",
        "${OC.env:PASS}",
        "${env:PASS}",
        "${PASSWORD}",
        "${settings}",
        "${settings..password}",
        "${settings.password",
        "${settings.${password}}",
        r"\${settings.password}",
        "prefix${settings.password}",
        "${settings.password}literal",
        "${settings.password}${settings.other}",
        "'${settings.password}literal'",
        '"${settings.password} literal"',
        "'${settings.password}",
        "'${settings.password}\"",
        "'${settings.password}'literal",
        "'${settings.password}'+literal",
        "'${settings.password}' + 'literal'",
        "${settings.password} + literal",
        "${settings.password}'literal'",
        '"${settings.password}\\"literal"',
        "${settings.password} literal",
        "'${settings.password}' literal",
        "${settings.password} ${settings.other}",
    ],
)
def test_retains_assignment_when_value_is_not_whole_supported_reference(value: str) -> None:
    # Given
    text = f"password={value}"
    expected = re.search(r"(?i)(secret|password|passwd|pwd)\s*[=:]\s*['\"]?[^\s'\"]{8,}", text)
    assert expected is not None
    # When
    result = SecretScanner().scan(text)
    # Then
    assert result.risk_score == 0.75
    assert [(span.start, span.end) for span in result.matches] == [expected.span()]


@pytest.mark.parametrize("extra", [False, True])
@pytest.mark.parametrize(
    ("name", "regex", "score", "text"),
    [
        (
            "Generic Secret",
            r"(?i)(secret|password|passwd|pwd)\s*[=:]\s*['\"]?[^\s'\"]{8,}",
            0.75,
            "password=${settings.password}",
        ),
        (
            "Connection String",
            r"(?i)(mongodb|postgres|mysql|redis)://[^\s]{10,}",
            0.85,
            "postgres://database.internal/app",
        ),
    ],
)
def test_suppresses_custom_rule_when_tuple_matches_builtin(
    extra: bool, name: str, regex: str, score: float, text: str
) -> None:
    # Given
    patterns = [(name, regex, score)]
    scanner = SecretScanner(extra_patterns=patterns) if extra else SecretScanner(patterns=patterns)
    # When
    result = scanner.scan(text)
    # Then
    assert result.matches == []
    assert result.risk_score == 0


@pytest.mark.parametrize("extra", [False, True])
@pytest.mark.parametrize(
    "case",
    [
        (
            "Generic Secret",
            r"(?i)(secret|password|passwd|pwd)\s*[=:]\s*['\"]?[^\s'\"]{8,}",
            "password=${settings.password}",
        ),
        ("Connection String", r"(?i)(mongodb|postgres|mysql|redis)://[^\s]{10,}", "postgres://database.internal/app"),
        ("Generic Secret", r"password=.+", "password=${settings.password}"),
    ],
)
def test_preserves_custom_rules_when_name_or_regex_matches_builtin(extra: bool, case: tuple[str, str, str]) -> None:
    # Given
    name, regex, text = case
    patterns = [(name, regex, 0.61)]
    scanner = SecretScanner(extra_patterns=patterns) if extra else SecretScanner(patterns=patterns)
    # When
    result = scanner.scan(text)
    # Then
    assert result.risk_score == 0.61
    assert [(span.start, span.end) for span in result.matches] == [(0, len(text))]
    assert result.rationale == f"Secret(s) detected (1): {name}"


def test_preserves_counts_scores_and_offsets_when_references_and_literals_are_mixed() -> None:
    # Given
    text = "password=${oc.env:PASS}\nsecret=literal123\npwd='${settings.password}'\npassword=another123"
    # When
    result = SecretScanner().scan(text)
    # Then
    assert [(span.start, span.end) for span in result.matches] == [
        (text.index("secret="), text.index("\npwd=")),
        (text.rindex("password="), len(text)),
    ]
    assert result.risk_score == 0.75
    assert result.rationale == "Secret(s) detected (2): Generic Secret; Generic Secret"


def test_retains_ambiguous_reference_and_literal_when_assignments_share_line() -> None:
    # Given
    text = "password=${settings.password} secret=literal123 pwd=${oc.env:PASS}"
    # When
    result = SecretScanner().scan(text)
    # Then
    start = text.index("secret=")
    assert [(span.start, span.end) for span in result.matches] == [
        (0, len("password=${settings.password}")),
        (start, start + len("secret=literal123")),
    ]
    assert result.risk_score == 0.75
    assert result.rationale == "Secret(s) detected (2): Generic Secret; Generic Secret"


@pytest.mark.parametrize("suffix", ["suffix=supersecret", "suffix:supersecret"])
def test_retains_reference_when_yaml_plain_scalar_has_assignment_suffix(suffix: str) -> None:
    # Given
    text = f"password: ${{settings.password}} {suffix}"
    # When
    result = SecretScanner().scan(text)
    # Then
    assert result.risk_score == 0.75
    assert [(span.start, span.end) for span in result.matches] == [(0, len("password: ${settings.password}"))]


def test_keeps_entropy_independent_when_reference_assignment_is_suppressed() -> None:
    # Given
    text = "password=${oc.env:ABCDEFGHIJKLMNOPQRSTUVWXYZ}"
    # When
    result = SecretScanner(entropy_detection=True).scan(text)
    # Then
    assert result.risk_score == 0.70
    assert [(span.start, span.end) for span in result.matches] == [(18, 44)]


@pytest.mark.parametrize("text", ["password=1234567", "postgres://localhost", "redis://user@host"])
def test_preserves_regex_minimums_when_candidate_is_short(text: str) -> None:
    # Given / When
    result = SecretScanner().scan(text)
    # Then
    assert result.matches == []
