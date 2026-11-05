import pytest
from cerbia.core.models.scans import MatchSpan
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


def test_secret_scanner_keeps_default_patterns_when_another_scanner_adds_extra_patterns() -> None:
    existing_scanner = SecretScanner()
    SecretScanner(extra_patterns=[("Deploy Token", r"DEPLOY-\d{6}", 0.65)])

    results = [existing_scanner.scan("DEPLOY-123456"), SecretScanner().scan("DEPLOY-123456")]

    assert [result.rationale for result in results] == ["No secrets detected", "No secrets detected"]


def test_secret_scanner_reports_extra_pattern_once_when_several_scanners_add_it() -> None:
    SecretScanner(extra_patterns=[("Build Token", r"BUILD-\d{6}", 0.65)])
    scanner = SecretScanner(extra_patterns=[("Build Token", r"BUILD-\d{6}", 0.65)])

    result = scanner.scan("BUILD-123456")

    assert result.rationale == "Secret(s) detected (1): Build Token"
    assert [(match.start, match.end) for match in result.matches] == [(0, 12)]


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


def test_secret_scanner_reports_api_key_once_when_entropy_is_enabled() -> None:
    # Given
    scanner = SecretScanner(entropy_detection=True)
    text = "api_key=ABCDEFGHIJKLMNOPQRSTUVWXYZabcdef"

    # When
    result = scanner.scan(text)

    # Then
    assert [(match.start, match.end) for match in result.matches] == [(0, 40)]
    assert result.risk_score == 0.8
    assert result.rationale == "Secret(s) detected (1): Generic API Key"


@pytest.mark.parametrize(
    ("text", "pattern", "expected_spans"),
    [
        (
            "note: ABCDEFGHIJKLMNOPQRSTUVWXYZabcdef",
            r"(?<=note: )ABCDEFGHIJKLMNOPQRSTUVWXYZabcdef",
            [(6, 38)],
        ),
        (
            "note: [ABCDEFGHIJKLMNOPQRSTUVWXYZabcdef]",
            r"\[ABCDEFGHIJKLMNOPQRSTUVWXYZabcdef\]",
            [(6, 40)],
        ),
    ],
    ids=["exact_containment", "strict_containment"],
)
def test_secret_scanner_skips_entropy_when_candidate_is_contained_in_regex_span(
    text: str, pattern: str, expected_spans: list[tuple[int, int]]
) -> None:
    # Given
    scanner = SecretScanner(patterns=[("Known", pattern, 0.6)], entropy_detection=True)

    # When
    result = scanner.scan(text)

    # Then
    assert [(match.start, match.end) for match in result.matches] == expected_spans
    assert result.risk_score == 0.6
    assert result.rationale == "Secret(s) detected (1): Known"


@pytest.mark.parametrize(
    ("text", "pattern", "expected_spans"),
    [
        (
            "prefix: ABCDEFGHIJKLMNOPQRSTUVWXYZabcdef",
            r"prefix: ABCDEFGHIJ",
            [(0, 18), (8, 40)],
        ),
        (
            "ABCDEFGHIJKLMNOPQRSTUVWXYZabcdef:suffix",
            r"QRSTUVWXYZabcdef:suffix",
            [(16, 39), (0, 32)],
        ),
        (
            "ABCDEFGHIJKLMNOPQRSTUVWXYZabcdef",
            r"KLMNOPQRST",
            [(10, 20), (0, 32)],
        ),
        (
            "ABCDEFGHIJKLMNOPQRSTUVWXYZabcdef ABCDEFGHIJKLMNOPQRSTUVWXYZabcdef",
            r"^ABCDEFGHIJKLMNOPQRSTUVWXYZabcdef",
            [(0, 32), (33, 65)],
        ),
    ],
    ids=["partial_overlap_left", "partial_overlap_right", "enclosing_candidate", "separate_candidate"],
)
def test_secret_scanner_keeps_entropy_when_candidate_is_not_contained_in_regex_span(
    text: str, pattern: str, expected_spans: list[tuple[int, int]]
) -> None:
    # Given
    scanner = SecretScanner(patterns=[("Known", pattern, 0.6)], entropy_detection=True)

    # When
    result = scanner.scan(text)

    # Then
    assert [(match.start, match.end) for match in result.matches] == expected_spans
    assert result.risk_score == 0.7
    assert result.rationale.startswith("Secret(s) detected (2): Known; High Entropy (base64,")


@pytest.mark.parametrize("use_default", [True, False], ids=["default", "explicit_opt_out"])
def test_secret_scanner_skips_unmatched_entropy_when_detection_is_disabled(use_default: bool) -> None:
    # Given
    patterns = [("Known", r"KNOWN", 0.6)]
    scanner = (
        SecretScanner(patterns=patterns) if use_default else SecretScanner(patterns=patterns, entropy_detection=False)
    )

    # When
    result = scanner.scan("KNOWN ABCDEFGHIJKLMNOPQRSTUVWXYZabcdef")

    # Then
    assert [(match.start, match.end) for match in result.matches] == [(0, 5)]
    assert result.risk_score == 0.6
    assert result.rationale == "Secret(s) detected (1): Known"


def test_secret_scanner_preserves_order_when_regex_spans_are_unsorted_and_nested() -> None:
    # Given
    token = "ABCDEFGHIJKLMNOPQRSTUVWXYZabcdef"
    scanner = SecretScanner(
        patterns=[
            ("Later", rf"(?<=\] ){token}", 0.5),
            ("Outer", r"\[[^]]+\]", 0.6),
            ("Nested", r"(?<=\[AB)CDEFGHIJ", 0.4),
        ],
        entropy_detection=True,
    )

    # When
    result = scanner.scan(f"[{token} {token}] {token} {token}")

    # Then
    assert [(match.start, match.end) for match in result.matches] == [(68, 100), (0, 67), (3, 11), (101, 133)]
    assert result.risk_score == 0.7
    assert result.rationale == "Secret(s) detected (4): Later; Outer; Nested; High Entropy (base64, 5.0)"


def test_secret_scanner_keeps_entropy_when_only_union_of_regex_spans_covers_candidate() -> None:
    # Given
    scanner = SecretScanner(
        patterns=[("Left", r"ABCDEFGHIJKLMNOPQRST", 0.5), ("Right", r"MNOPQRSTUVWXYZabcdef", 0.6)],
        entropy_detection=True,
    )

    # When
    result = scanner.scan("ABCDEFGHIJKLMNOPQRSTUVWXYZabcdef")

    # Then
    assert [(match.start, match.end) for match in result.matches] == [(0, 20), (12, 32), (0, 32)]
    assert result.risk_score == 0.7
    assert result.rationale == "Secret(s) detected (3): Left; Right; High Entropy (base64, 5.0)"


@pytest.mark.parametrize("count", [128, 256, 2000])
def test_secret_scanner_bounds_span_reads_when_many_candidates_are_already_matched(
    count: int, monkeypatch: pytest.MonkeyPatch
) -> None:
    # Given
    scanner = SecretScanner(entropy_detection=True)
    token = "AKIA" + "A" * 16
    text = " ".join([token] * count)
    spans = [MatchSpan(start=index * 21, end=index * 21 + 20) for index in range(count)]
    starts = {id(span): span.start for span in spans}
    reads: list[None] = []

    def read_start(span: MatchSpan) -> int:
        reads.append(None)
        return starts[id(span)]

    monkeypatch.setattr(MatchSpan, "start", property(read_start), raising=False)

    # When
    matches, hits = scanner._scan_entropy(text, spans)

    # Then
    assert matches == []
    assert hits == []
    assert len(reads) <= 8 * count


@pytest.mark.parametrize(
    "header",
    [
        "-----BEGIN ENCRYPTED PRIVATE KEY-----",
        "-----BEGIN PRIVATE KEY-----",
        "-----BEGIN RSA PRIVATE KEY-----",
        "-----BEGIN EC PRIVATE KEY-----",
        "-----BEGIN DSA PRIVATE KEY-----",
        "-----BEGIN OPENSSH PRIVATE KEY-----",
    ],
    ids=["encrypted", "bare", "rsa", "ec", "dsa", "openssh"],
)
@pytest.mark.parametrize("entropy_detection", [False, True], ids=["entropy_disabled", "entropy_enabled"])
@pytest.mark.parametrize("surrounding_text", ["", "Notes\n"], ids=["standalone", "surrounding_text"])
def test_secret_scanner_detects_private_key_when_header_is_provided(
    header: str, entropy_detection: bool, surrounding_text: str
) -> None:
    # Given
    scanner = SecretScanner(entropy_detection=entropy_detection)
    text = f"{surrounding_text}{header}{surrounding_text}"

    # When
    result = scanner.scan(text)

    # Then
    assert result.risk_score == 0.99
    assert result.rationale == "Secret(s) detected (1): Private Key"
    assert [(match.start, match.end) for match in result.matches] == [
        (len(surrounding_text), len(surrounding_text) + len(header))
    ]
