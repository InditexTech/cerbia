import pytest
from cerbia.core.scanners.pii import PiiScanner
from cerbia.core.types import Action, ContentType, Severity

pytestmark = pytest.mark.unit


@pytest.mark.parametrize(
    ("pii", "expected_names", "expected_risk_score"),
    [
        ("jane@example.com", ("Email",), 0.90),
        ("jane [at] example [dot] com", ("Email (obfuscated)",), 0.85),
        ("+44 20 1234 5678", ("Phone (International)",), 0.80),
        ("202-555-0123", ("Phone (North American)",), 0.85),
        ("612345678", ("Phone (Spanish)",), 0.85),
        ("13800138000", ("Phone (Chinese)", "CPF (Brazil)"), 0.90),
        ("12345678Z", ("DNI (Spain)",), 0.90),
        ("X1234567L", ("NIE (Spain)",), 0.90),
        ("ES9121000418450200051332", ("IBAN",), 0.92),
        ("4111 1111 1111 1111", ("Credit Card (Visa)",), 0.80),
        ("5555 5555 5555 4444", ("Credit Card (Mastercard)",), 0.80),
        ("3782 822463 10005", ("Credit Card (Amex)",), 0.80),
        ("6011 1111 1111 1117", ("Credit Card (Discover)",), 0.80),
        ("3530 1113 3330 0000", ("Credit Card (JCB)",), 0.80),
        ("3000 0000 0000 00", ("Credit Card (Diners Club)",), 0.80),
        ("6200 0000 0000 0005", ("Credit Card (UnionPay)",), 0.80),
        ("192.0.2.1", ("IPv4",), 0.70),
        ("2001:db8::1", ("IPv6",), 0.70),
        ("123-45-6789", ("SSN (US)",), 0.90),
        ("12-3456789", ("EIN (US)",), 0.90),
        ("912-70-1234", ("SSN (US)", "ITIN (US)"), 0.90),
        ("123 456 789", ("SIN (Canada)",), 0.90),
        ("AB123456C", ("National Insurance Number (UK)",), 0.90),
        ("123.456.789-01", ("CPF (Brazil)",), 0.90),
        ("GODE561231HDFRRN09", ("CURP (Mexico)",), 0.90),
        ("Aadhaar: 1234 5678 9012", ("Aadhaar (India)",), 0.90),
        ("IMEI: 490154203237518", ("IMEI",), 0.85),
        ("IMSI: 310150123456789", ("IMSI",), 0.85),
        ("00:1A:2B:3C:4D:5E", ("IPv6", "MAC Address"), 0.75),
        ("123e4567-e89b-12d3-a456-426614174000", ("UUID",), 0.75),
        ("1BoatSLRHtKNngkdXEeobR76b53LETtpyT", ("Bitcoin Address",), 0.80),
        ("bc1qw508d6qejxtdg4y5r3zarvary0c5xw7kygt080", ("Bitcoin Address (Bech32)",), 0.80),
        ("0xaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa", ("Ethereum Address",), 0.80),
    ],
    ids=[
        "email",
        "obfuscated_email",
        "international_phone",
        "north_american_phone",
        "spanish_phone",
        "chinese_phone",
        "spanish_dni",
        "spanish_nie",
        "iban",
        "visa",
        "mastercard",
        "amex",
        "discover",
        "jcb",
        "diners_club",
        "unionpay",
        "ipv4",
        "ipv6",
        "ssn",
        "ein",
        "itin",
        "canadian_sin",
        "uk_national_insurance",
        "brazilian_cpf",
        "mexican_curp",
        "indian_aadhaar",
        "imei",
        "imsi",
        "mac_address",
        "uuid",
        "bitcoin",
        "bitcoin_bech32",
        "ethereum",
    ],
)
def test_pii_scanner_detects_default_patterns_when_known_pii_is_provided(
    pii: str, expected_names: tuple[str, ...], expected_risk_score: float
) -> None:
    scanner = PiiScanner()

    result = scanner.scan(f"PII: {pii}")

    assert result.risk_score == expected_risk_score
    assert result.rationale == "PII detected ({} match(es)): {}".format(
        len(expected_names), ", ".join(f"{name} (1)" for name in expected_names)
    )
    assert [(match.start, match.end) for match in result.matches] == [(5, 5 + len(pii))] * len(expected_names)


def test_pii_scanner_returns_safe_outcome_when_pii_is_not_detected() -> None:
    scanner = PiiScanner()

    result = scanner.scan("The documentation contains no personal information.")

    assert result.risk_score == 0.0
    assert result.rationale == "No PII detected"
    assert result.matches == []


def test_pii_scanner_uses_highest_risk_and_limits_rationale_to_first_five_types() -> None:
    extra_patterns = [(f"Custom {index}", f"custom-{index}") for index in range(1, 6)]
    scanner = PiiScanner(extra_patterns=extra_patterns)
    text = "custom-1 custom-2 custom-3 custom-4 custom-5 jane@example.com"

    result = scanner.scan(text)

    assert result.risk_score == 0.90
    assert (
        result.rationale
        == "PII detected (6 match(es)): Email (1), Custom 1 (1), Custom 2 (1), Custom 3 (1), Custom 4 (1)"
    )
    assert [(match.start, match.end) for match in result.matches] == [
        (45, 61),
        (0, 8),
        (9, 17),
        (18, 26),
        (27, 35),
        (36, 44),
    ]


def test_pii_scanner_appends_extra_patterns_when_extra_patterns_are_provided() -> None:
    scanner = PiiScanner(extra_patterns=[("Internal Identifier", r"INT-\d{6}")])

    result = scanner.scan("INT-123456")

    assert result.risk_score == 0.80
    assert result.rationale == "PII detected (1 match(es)): Internal Identifier (1)"
    assert [(match.start, match.end) for match in result.matches] == [(0, 10)]


def test_pii_scanner_isolates_extra_patterns_between_instances() -> None:
    sentinel = r"SENTINEL-[A-Z]{4}"
    PiiScanner(extra_patterns=[("Sentinel", sentinel)])
    default_scanner = PiiScanner()
    second_custom_scanner = PiiScanner(extra_patterns=[("Other", r"OTHER-\d{4}")])

    default_result = default_scanner.scan("SENTINEL-ABCD")
    second_custom_result = second_custom_scanner.scan("SENTINEL-ABCD")

    assert default_result.risk_score == 0.0
    assert default_result.rationale == "No PII detected"
    assert default_result.matches == []
    assert second_custom_result.risk_score == 0.0
    assert second_custom_result.rationale == "No PII detected"
    assert second_custom_result.matches == []


def test_pii_scanner_preserves_configuration_when_custom_values_are_provided() -> None:
    scanner = PiiScanner(
        severity=Severity.CRITICAL,
        action=Action.BLOCK,
        content_types=[ContentType.TEXT, ContentType.CODE],
    )

    assert scanner.scanner_id == "pii"
    assert scanner.scanner_name == "PII"
    assert scanner.severity is Severity.CRITICAL
    assert scanner.action is Action.BLOCK
    assert scanner.content_types == (ContentType.TEXT, ContentType.CODE)
