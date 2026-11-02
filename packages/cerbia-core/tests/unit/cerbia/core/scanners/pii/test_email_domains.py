import pytest
from cerbia.core.config import ScannerConfig
from cerbia.core.exceptions import CerbIAConfigError
from cerbia.core.factories.scanner import ScannerFactory
from cerbia.core.scanners.pii import PiiScanner
from cerbia.core.types import Action, ContentType, Severity

pytestmark = pytest.mark.unit


@pytest.mark.parametrize(
    ("address", "expected"),
    [
        ("jane@example.com", True),
        ("JANE@EXAMPLE.ORG", True),
        ("jane@unrelated.com", False),
        ("jane@sub.example.com", False),
        ("jane@listed.example.com", True),
        ("jane@notexample.com", False),
        ("jane@example.com.evil", False),
        ("jane@example.comevil", False),
        ("jane@example.com-evil", False),
        ("jane@example.com_ignored", False),
        ("jane@example.com123", False),
        ("jane@example.comé", False),
        ("jane@example.com.", True),
    ],
)
def test_email_domains_match_exactly_when_filtering_is_enabled(address: str, expected: bool) -> None:
    scanner = PiiScanner(email_domains=["EXAMPLE.COM", "example.org", "listed.example.com"])

    result = scanner.scan(address)

    assert bool(result.matches) is expected
    assert result.risk_score == (0.90 if expected else 0.0)


@pytest.mark.parametrize(
    "address",
    [
        "jane [at] example [dot] com",
        "jane(at)example(dot)com",
        "jane [arroba] example [punto] com",
        "JANE ( AT ) EXAMPLE ( DOT ) COM",
        "jane [at] listed.example [dot] com",
    ],
)
def test_email_domains_preserve_spans_when_email_is_obfuscated(address: str) -> None:
    scanner = PiiScanner(email_domains=["example.com", "listed.example.com"])
    text = f"你好 🙂 {address}!"

    result = scanner.scan(text)

    assert [(span.start, span.end) for span in result.matches] == [(5, 5 + len(address))]
    assert result.risk_score == 0.85


@pytest.mark.parametrize(
    "address",
    [
        "jane [at] unrelated [dot] com",
        "jane [at] sub.example [dot] com",
        "jane [at] notexample [dot] com",
        "jane [at] example [dot] com [dot] evil",
        "jane [at] example [dot] com (punto) evil",
        "jane [at] example [dot] com.evil",
        "jane [at] example [dot] com-evil",
        "jane [at] example [dot] com123",
        "jane@example.com [dot] evil",
    ],
)
def test_email_domains_reject_unlisted_domains_and_continuations_when_filtering_is_enabled(address: str) -> None:
    scanner = PiiScanner(email_domains=["example.com"])

    result = scanner.scan(address)

    assert result.matches == []
    assert result.risk_score == 0.0


def test_email_domains_keep_original_spans_and_counts_when_multiple_addresses_are_present() -> None:
    scanner = PiiScanner(email_domains=["example.com", "EXAMPLE.COM", "example.org"])
    text = "🙂 jane@example.com bob@other.com jane@example.com sam [at] example [dot] org"

    result = scanner.scan(text)

    assert [text[span.start : span.end] for span in result.matches] == [
        "jane@example.com",
        "jane@example.com",
        "sam [at] example [dot] org",
    ]
    assert [(span.start, span.end) for span in result.matches[:2]] == [(2, 18), (33, 49)]
    assert result.rationale == "PII detected (3 match(es)): Email (2), Email (obfuscated) (1)"


@pytest.mark.parametrize("domains", [None, [], ["example.com"]])
def test_email_domains_preserve_extra_patterns_when_custom_labels_match_builtin_labels(
    domains: list[str] | None,
) -> None:
    scanner = PiiScanner(
        extra_patterns=[("Email", "CUSTOM-A"), ("Email (obfuscated)", "CUSTOM-B")], email_domains=domains
    )
    text = "CUSTOM-A CUSTOM-B"

    result = scanner.scan(text)

    assert [text[span.start : span.end] for span in result.matches] == ["CUSTOM-A", "CUSTOM-B"]
    assert result.risk_score == 0.80


@pytest.mark.parametrize("domains", [None, [], ["example.com"]])
@pytest.mark.parametrize("checksums", [False, True])
def test_email_domains_preserve_other_pii_when_checksum_validation_is_configured(
    domains: list[str] | None, checksums: bool
) -> None:
    scanner = PiiScanner(email_domains=domains, validate_checksums=checksums)
    text = "192.0.2.1 12345678Z 12345678A"

    result = scanner.scan(text)

    expected = ["12345678Z", "192.0.2.1"] if checksums else ["12345678Z", "12345678A", "192.0.2.1"]
    assert [text[span.start : span.end] for span in result.matches] == expected


@pytest.mark.parametrize(
    ("domains", "expected"),
    [
        (None, ["jane@example.com", "bob@other.com", "jane [at] example [dot] com"]),
        ([], []),
        (["example.com"], ["jane@example.com", "jane [at] example [dot] com"]),
    ],
)
def test_email_domains_are_forwarded_when_scanner_is_built_from_config(
    domains: list[str] | None, expected: list[str]
) -> None:
    config = ScannerConfig(scanner="cerbia.core.scanners.PiiScanner", init_args={"email_domains": domains})
    scanner = ScannerFactory.build(config)
    text = "jane@example.com bob@other.com jane [at] example [dot] com"

    result = scanner.scan(text)

    assert [text[span.start : span.end] for span in result.matches] == expected


@pytest.mark.parametrize(
    "domains",
    [
        [""],
        [" example.com"],
        ["example.com "],
        ["example.com\n"],
        ["exam ple.com"],
        ["@example.com"],
        ["https://example.com"],
        ["*.example.com"],
        ["example.com/path"],
        ["example.com:443"],
        ["example"],
        [".example.com"],
        ["example.com."],
        ["example..com"],
        ["-example.com"],
        ["example-.com"],
        ["exam_ple.com"],
        ["éxample.com"],
        ["a" * 64 + ".com"],
        [".".join(["a" * 63] * 4)],
        ["example.com", "bad domain"],
    ],
)
def test_email_domains_raise_config_error_when_configuration_is_invalid(domains: list[str]) -> None:
    with pytest.raises(CerbIAConfigError, match="email_domains"):
        PiiScanner(email_domains=domains)


def test_email_domains_preserve_legacy_matches_when_none_is_explicit() -> None:
    scanner = PiiScanner(email_domains=None)
    text = "jane@other.com jane [at] example [dot] com [dot] evil"

    result = scanner.scan(text)

    assert result == PiiScanner().scan(text)
    assert len(result.matches) == 2


def test_email_domains_preserve_positional_arguments_when_appended_after_custom_validators() -> None:
    scanner = PiiScanner(None, Severity.LOW, Action.BLOCK, (ContentType.TEXT,), True, {"Email": lambda _: False}, None)

    result = scanner.scan("jane@example.com")

    assert result.matches == []


def test_email_domains_are_copied_when_configuration_list_changes() -> None:
    domains = ["example.com"]
    scanner = PiiScanner(email_domains=domains)
    domains.append("other.com")

    result = scanner.scan("jane@other.com")

    assert result.matches == []


@pytest.mark.parametrize(
    "address",
    [
        "jane [at] sub [dot] example.com",
        "jane [at] sub [dot] example [dot] com",
        "jane [arroba] sub [punto] example [punto] com",
        "JANE (ARROBA) SUB (PUNTO) EXAMPLE.COM",
    ],
)
@pytest.mark.parametrize("suffix", ["", ".evil", " [dot] evil", " (punto) evil"])
def test_email_domains_resolve_full_subdomain_when_earlier_separators_are_obfuscated(address: str, suffix: str) -> None:
    scanner = PiiScanner(email_domains=["sub.example.com"])
    text = f"你好 🙂 {address}{suffix}!"

    result = scanner.scan(text)

    assert [(span.start, span.end) for span in result.matches] == ([] if suffix else [(5, 5 + len(address))])
    assert result.risk_score == (0.0 if suffix else 0.85)


@pytest.mark.parametrize("domains", [None, [], ["example.com"]])
@pytest.mark.parametrize("checksums", [False, True])
@pytest.mark.parametrize(
    ("pii", "valid"),
    [
        ("4111 1111 1111 1111", True),
        ("4111 1111 1111 1112", False),
        ("ES9121000418450200051332", True),
        ("ES9021000418450200051332", False),
    ],
)
def test_email_domains_preserve_payments_when_checksum_validation_is_configured(
    domains: list[str] | None, checksums: bool, pii: str, valid: bool
) -> None:
    scanner = PiiScanner(email_domains=domains, validate_checksums=checksums)

    result = scanner.scan(pii)

    assert [(span.start, span.end) for span in result.matches] == ([(0, len(pii))] if valid or not checksums else [])


@pytest.mark.parametrize(
    ("address", "legacy_match"),
    [
        ("jane [at] sub [dot] example.com", "jane [at] sub [dot] example"),
        ("jane [at] sub [dot] example [dot] com", "jane [at] sub [dot] example"),
        ("jane [arroba] sub [punto] example [punto] com", "jane [arroba] sub [punto] example"),
    ],
)
def test_email_domains_preserve_truncated_legacy_spans_when_filter_is_omitted(address: str, legacy_match: str) -> None:
    scanner = PiiScanner()

    result = scanner.scan(address)

    assert [(span.start, span.end) for span in result.matches] == [(0, len(legacy_match))]
