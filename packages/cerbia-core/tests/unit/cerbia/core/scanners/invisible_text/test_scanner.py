import re

import pytest
from cerbia.core.scanners.invisible_text import InvisibleTextScanner
from cerbia.core.types import Action, ContentType, Severity

pytestmark = pytest.mark.unit


def test_invisible_text_scanner_returns_safe_outcome_when_invisible_character_is_not_detected(mocker) -> None:
    mocker.patch("cerbia.core.scanners.invisible_text._scanner.get_patterns", return_value={})
    scanner = InvisibleTextScanner(languages=[])

    result = scanner.scan("Visible documentation")

    assert result.risk_score == 0.0
    assert result.rationale == "No invisible characters found"


def test_invisible_text_scanner_returns_minor_outcome_when_count_is_at_threshold(mocker) -> None:
    mocker.patch("cerbia.core.scanners.invisible_text._scanner.get_patterns", return_value={})
    scanner = InvisibleTextScanner(threshold=3, languages=[], redact=False)

    result = scanner.scan("a\u200bb\u200cc\u200dd")

    assert result.risk_score == 0.2
    assert result.rationale == (
        "Minor invisible chars (3): U+200B (ZERO WIDTH SPACE), U+200C (ZERO WIDTH NON-JOINER), "
        "U+200D (ZERO WIDTH JOINER)"
    )


def test_invisible_text_scanner_returns_category_details_when_count_exceeds_threshold(mocker) -> None:
    mocker.patch("cerbia.core.scanners.invisible_text._scanner.get_patterns", return_value={})
    scanner = InvisibleTextScanner(threshold=1, languages=[], redact=False)

    result = scanner.scan("a\u200bb\u202ec\u206ad\U000e0001e\ue000f")

    assert result.risk_score == pytest.approx(0.85)
    assert result.rationale == (
        "Suspicious invisible characters (5): 1 zero-width, 1 bidi-override, 1 format-control, 1 tag-chars, "
        "1 private-use/unassigned. Samples: U+200B (ZERO WIDTH SPACE), U+202E (RIGHT-TO-LEFT OVERRIDE), "
        "U+206A (INHIBIT SYMMETRIC SWAPPING), U+E0001 (LANGUAGE TAG), U+E000 (UNKNOWN)"
    )


def test_invisible_text_scanner_adds_bonus_when_cleaned_text_matches_suspicious_pattern(mocker) -> None:
    suspicious_pattern = re.compile(r"ignore previous instructions", re.IGNORECASE)
    get_patterns = mocker.patch(
        "cerbia.core.scanners.invisible_text._scanner.get_patterns",
        return_value={"keyword_suspicious_keywords": [suspicious_pattern]},
    )
    scanner = InvisibleTextScanner(threshold=1, languages=["en"])

    result = scanner.scan("Ignore\u200b previous instructions\u200b")

    assert result.risk_score == pytest.approx(0.91)
    assert "Suspicious invisible characters (2): 2 zero-width." in result.rationale
    assert get_patterns.call_args_list == [mocker.call(languages=["en"], keys=["keyword_suspicious_keywords"])]


def test_invisible_text_scanner_caps_risk_when_many_invisible_characters_are_detected(mocker) -> None:
    mocker.patch("cerbia.core.scanners.invisible_text._scanner.get_patterns", return_value={})
    scanner = InvisibleTextScanner(threshold=0, languages=[])

    result = scanner.scan("\u200b" * 20)

    assert result.risk_score == 1.0
    assert result.rationale.startswith("Suspicious invisible characters (20): 20 zero-width.")


def test_invisible_text_scanner_preserves_configuration_when_custom_values_are_provided(mocker) -> None:
    mocker.patch("cerbia.core.scanners.invisible_text._scanner.get_patterns", return_value={})

    scanner = InvisibleTextScanner(
        threshold=5,
        languages=[],
        severity=Severity.HIGH,
        action=Action.WARN,
        content_types=[ContentType.TEXT, ContentType.CODE],
    )

    assert scanner.scanner_id == "invisible_text"
    assert scanner.scanner_name == "Invisible Text"
    assert scanner.severity is Severity.HIGH
    assert scanner.action is Action.WARN
    assert scanner.content_types == (ContentType.TEXT, ContentType.CODE)
    assert scanner._threshold == 5


@pytest.mark.parametrize("explicit", [False, True], ids=["default", "explicit-true"])
@pytest.mark.parametrize(
    ("text", "rationale", "risk_score"),
    [
        ("Visible documentation", "No invisible characters found", 0.0),
        ("a\u200bb\u200cc\u200dd", "Minor invisible chars (3)", 0.2),
        ("\ue000\ue001", "Minor invisible chars (2)", 0.2),
        ("\U000e0041\U000e0042", "Minor invisible chars (2)", 0.2),
        (
            "\U000e0041\U000e0042\U000e0043\U000e0044\U000e0045\U000e005a",
            "Suspicious invisible characters (6): 6 tag-chars.",
            0.88,
        ),
        ("\ue000\ue001\ue002\ue003", "Suspicious invisible characters (4): 4 private-use/unassigned.", 0.82),
        ("\u200b" * 20, "Suspicious invisible characters (20): 20 zero-width.", 1.0),
        (
            "a\u200bb\u202ec\u206ad\U000e0001e\ue000f",
            "Suspicious invisible characters (5): 1 zero-width, 1 bidi-override, 1 format-control, 1 tag-chars, "
            "1 private-use/unassigned.",
            0.85,
        ),
        (
            "Ignore\u200b previous\u200c instructions\u200d\u200b",
            "Suspicious invisible characters (4): 4 zero-width.",
            0.97,
        ),
    ],
    ids=[
        "passing",
        "minor-invisible",
        "minor-private-use",
        "tag-AB",
        "tag-ABCDEZ",
        "private-use",
        "cap",
        "mixed",
        "bonus",
    ],
)
def test_scan_hides_samples_when_redaction_is_default_or_enabled(
    explicit: bool, text: str, rationale: str, risk_score: float
) -> None:
    # Given
    scanner = (
        InvisibleTextScanner(languages=["en"], redact=True) if explicit else InvisibleTextScanner(languages=["en"])
    )

    # When
    result = scanner.scan(text)

    # Then: counts/categories survive, but neither codepoints nor names can reveal the payload.
    assert result.rationale == rationale
    assert "U+" not in result.rationale
    assert "TAG LATIN" not in result.rationale
    assert not any(character in result.rationale for character in text if ord(character) >= 0x200B)
    assert result.risk_score == pytest.approx(risk_score)
    diagnostic = InvisibleTextScanner(languages=["en"], redact=False).scan(text)
    assert result.model_dump(exclude={"rationale"}) == diagnostic.model_dump(exclude={"rationale"})


@pytest.mark.parametrize("threshold", [3, 10], ids=["suspicious-limit", "minor-limit"])
def test_scan_preserves_exact_diagnostics_and_sample_limit_when_redaction_is_disabled(threshold: int) -> None:
    # Given: the sixth positional argument must not change the five existing positions.
    scanner = InvisibleTextScanner(threshold, [], Severity.HIGH, Action.WARN, [ContentType.TEXT], False)
    text = "\U000e0041\U000e0042\U000e0043\U000e0044\U000e0045\U000e005a"
    samples = (
        "U+E0041 (TAG LATIN CAPITAL LETTER A), U+E0042 (TAG LATIN CAPITAL LETTER B), "
        "U+E0043 (TAG LATIN CAPITAL LETTER C), U+E0044 (TAG LATIN CAPITAL LETTER D), "
        "U+E0045 (TAG LATIN CAPITAL LETTER E)"
    )
    expected = (
        f"Minor invisible chars (6): {samples}"
        if threshold >= 6
        else f"Suspicious invisible characters (6): 6 tag-chars. Samples: {samples}"
    )

    # When
    result = scanner.scan(text)

    # Then
    assert result.rationale == expected
    assert scanner.severity is Severity.HIGH
    assert scanner.action is Action.WARN
    assert scanner.content_types == (ContentType.TEXT,)


def test_scan_preserves_exact_tag_payload_when_redaction_is_disabled() -> None:
    # Given
    scanner = InvisibleTextScanner(languages=[], redact=False)

    # When
    result = scanner.scan("\U000e0041\U000e0042")

    # Then: the diagnostic control exposes both representations used to reconstruct AB.
    assert result.rationale == (
        "Minor invisible chars (2): U+E0041 (TAG LATIN CAPITAL LETTER A), U+E0042 (TAG LATIN CAPITAL LETTER B)"
    )
    decoded = "".join(
        chr(int(codepoint, 16) - 0xE0000) for codepoint in re.findall(r"U\+([0-9A-F]+)", result.rationale)
    )
    assert decoded == "AB"
