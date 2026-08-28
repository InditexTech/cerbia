import pytest
from cerbia.core.scanners.secret import SecretScanner
from cerbia.core.types import Action, ContentType, Severity

pytestmark = pytest.mark.unit


@pytest.mark.parametrize(
    ("secret", "expected_name", "expected_risk_score"),
    [
        ("AKIAAAAAAAAAAAAAAAAA", "AWS Access Key", 0.95),
        ("ghp_" + "a" * 36, "GitHub Personal Token", 0.95),
        ("-----BEGIN PRIVATE KEY-----", "Private Key", 0.99),
    ],
    ids=["aws_access_key", "github_personal_token", "private_key"],
)
def test_secret_scanner_detects_default_pattern_when_known_secret_is_provided(
    secret: str, expected_name: str, expected_risk_score: float
) -> None:
    scanner = SecretScanner()

    result = scanner.scan(f"Secret: {secret}")

    assert result.risk_score == expected_risk_score
    assert result.rationale.startswith("Secret(s) detected (2):")
    assert expected_name in result.rationale
    assert "Generic Secret" in result.rationale
    assert (8, 8 + len(secret)) in [(match.start, match.end) for match in result.matches]


def test_secret_scanner_returns_safe_outcome_when_secret_is_not_detected() -> None:
    scanner = SecretScanner()

    result = scanner.scan("The documentation contains no credentials.")

    assert result.risk_score == 0.0
    assert result.rationale == "No secrets detected"
    assert result.matches == []


def test_secret_scanner_replaces_default_patterns_when_custom_patterns_are_provided() -> None:
    scanner = SecretScanner(patterns=[("Internal Token", r"INT-\d{6}", 0.65)])

    result = scanner.scan("AKIAAAAAAAAAAAAAAAAA INT-123456")

    assert result.risk_score == 0.65
    assert result.rationale == "Secret(s) detected (1): Internal Token"
    assert [(match.start, match.end) for match in result.matches] == [(21, 31)]


def test_secret_scanner_appends_extra_patterns_when_extra_patterns_are_provided() -> None:
    scanner = SecretScanner(extra_patterns=[("Internal Token", r"INT-\d{6}", 0.65)])

    result = scanner.scan("INT-123456")

    assert result.risk_score == 0.65
    assert result.rationale == "Secret(s) detected (1): Internal Token"
    assert [(match.start, match.end) for match in result.matches] == [(0, 10)]


def test_secret_scanner_uses_highest_risk_and_limits_rationale_to_first_five_hits() -> None:
    patterns = [(f"Secret {index}", f"token-{index}", index / 10) for index in range(1, 7)]
    scanner = SecretScanner(patterns=patterns)

    result = scanner.scan("token-1 token-2 token-3 token-4 token-5 token-6")

    assert result.risk_score == 0.6
    assert result.rationale == "Secret(s) detected (6): Secret 1; Secret 2; Secret 3; Secret 4; Secret 5"
    assert [(match.start, match.end) for match in result.matches] == [
        (0, 7),
        (8, 15),
        (16, 23),
        (24, 31),
        (32, 39),
        (40, 47),
    ]


def test_secret_scanner_detects_high_entropy_hex_when_entropy_detection_is_enabled() -> None:
    scanner = SecretScanner(patterns=[], entropy_detection=True)

    result = scanner.scan("0123456789abcdef0123")

    assert result.risk_score == 0.7
    assert result.rationale == "Secret(s) detected (1): High Entropy (hex, 3.9)"
    assert [(match.start, match.end) for match in result.matches] == [(0, 20)]


def test_secret_scanner_detects_high_entropy_base64_when_entropy_detection_is_enabled() -> None:
    scanner = SecretScanner(patterns=[], entropy_detection=True)
    candidate = "ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789"

    result = scanner.scan(candidate)

    assert result.risk_score == 0.7
    assert result.rationale == "Secret(s) detected (1): High Entropy (base64, 6.0)"
    assert [(match.start, match.end) for match in result.matches] == [(0, len(candidate))]


@pytest.mark.parametrize(
    ("text", "patterns", "entropy_detection", "expected_risk_score", "expected_rationale", "expected_matches"),
    [
        ("0123456789abcdef0123", [], False, 0.0, "No secrets detected", []),
        ("aaaaaaaaaaaaaaaaaaaa", [], True, 0.0, "No secrets detected", []),
        (
            "ABCDEFGHIJKLMNOPQRSTUVWXYZabcdef",
            [("Known", r"ABCDEFGHIJKLMNOPQRSTUVWXYZabcdef", 0.9)],
            True,
            0.9,
            "Secret(s) detected (1): Known",
            [(0, 32)],
        ),
    ],
    ids=["entropy_detection_disabled", "low_entropy_candidate", "already_matched_pattern"],
)
def test_secret_scanner_skips_entropy_detection_when_candidate_is_not_eligible(
    text: str,
    patterns: list[tuple[str, str, float]],
    entropy_detection: bool,
    expected_risk_score: float,
    expected_rationale: str,
    expected_matches: list[tuple[int, int]],
) -> None:
    scanner = SecretScanner(patterns=patterns, entropy_detection=entropy_detection)

    result = scanner.scan(text)

    assert result.risk_score == expected_risk_score
    assert result.rationale == expected_rationale
    assert [(match.start, match.end) for match in result.matches] == expected_matches


def test_secret_scanner_preserves_configuration_when_custom_values_are_provided() -> None:
    scanner = SecretScanner(
        severity=Severity.HIGH,
        action=Action.WARN,
        content_types=[ContentType.TEXT, ContentType.CODE],
    )

    assert scanner.scanner_id == "secrets"
    assert scanner.scanner_name == "Secrets"
    assert scanner.severity is Severity.HIGH
    assert scanner.action is Action.WARN
    assert scanner.content_types == (ContentType.TEXT, ContentType.CODE)
