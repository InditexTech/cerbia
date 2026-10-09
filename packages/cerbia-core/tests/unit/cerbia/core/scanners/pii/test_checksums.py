import pytest
from cerbia.core.scanners.pii import (
    PiiScanner,
    validate_cpf_checksum,
    validate_dni_checksum,
    validate_iban_checksum,
    validate_luhn_checksum,
    validate_nie_checksum,
)

pytestmark = pytest.mark.unit


@pytest.mark.parametrize(
    ("dni", "expected"),
    [
        ("12345678Z", True),
        ("12345678-Z", True),
        ("12345678z", True),
        ("00000000T", True),
        ("00000001R", True),
        ("12345678A", False),
        ("123", False),
        ("1234567890", False),
        ("1234567AZ", False),
        ("123456789", False),
        ("", False),
    ],
)
def test_validate_dni_checksum(dni: str, expected: bool) -> None:
    assert validate_dni_checksum(dni) is expected


@pytest.mark.parametrize(
    ("nie", "expected"),
    [
        ("X1234567L", True),
        ("X-1234567-L", True),
        ("Y1234567X", True),
        ("Z1234567R", True),
        ("X1234567A", False),
        ("W1234567L", False),
        ("X123", False),
        ("X123456AL", False),
        ("X12345671", False),
        ("", False),
    ],
)
def test_validate_nie_checksum(nie: str, expected: bool) -> None:
    assert validate_nie_checksum(nie) is expected


@pytest.mark.parametrize(
    ("card_number", "expected"),
    [
        ("4111 1111 1111 1111", True),
        ("5555 5555 5555 4444", True),
        ("3782 822463 10005", True),
        ("6011 1111 1111 1117", True),
        ("49927398716", True),
        ("490154203237518", True),  # IMEI test vector
        ("4111 1111 1111 1112", False),
        ("49927398717", False),
        ("4", False),
        ("", False),
        ("abc-def", False),
    ],
)
def test_validate_luhn_checksum(card_number: str, expected: bool) -> None:
    assert validate_luhn_checksum(card_number) is expected


@pytest.mark.parametrize(
    ("iban", "expected"),
    [
        ("ES9121000418450200051332", True),
        ("ES91 2100 0418 4502 0005 1332", True),
        ("ES9121000418450200051333", False),
        ("ES12", False),
        ("ES" + "1" * 40, False),
        ("1234567890123456", False),
        ("ES91 2100 0418 4502 @@@@", False),
    ],
)
def test_validate_iban_checksum(iban: str, expected: bool) -> None:
    assert validate_iban_checksum(iban) is expected


@pytest.mark.parametrize(
    ("cpf", "expected"),
    [
        ("52998224725", True),
        ("529.982.247-25", True),
        ("123.456.789-01", False),
        ("111.111.111-11", False),
        ("123", False),
        ("52998224726", False),
        ("52998224735", False),
    ],
)
def test_validate_cpf_checksum(cpf: str, expected: bool) -> None:
    assert validate_cpf_checksum(cpf) is expected


def test_pii_scanner_with_validate_checksums_filters_false_positives() -> None:
    scanner = PiiScanner(validate_checksums=True)

    # 12345678A is an invalid DNI (checksum fails)
    # 4111 1111 1111 1112 is an invalid Visa (Luhn fails)
    # X1234567A is an invalid NIE (checksum fails)
    text = "Order 12345678A, ref 4111 1111 1111 1112, client X1234567A"
    result = scanner.scan(text)

    assert result.risk_score == 0.0
    assert result.rationale == "No PII detected"
    assert result.matches == []


def test_pii_scanner_with_validate_checksums_preserves_valid_pii() -> None:
    scanner = PiiScanner(validate_checksums=True)

    text = "DNI: 12345678Z, Visa: 4111 1111 1111 1111, Email: user@example.com"
    result = scanner.scan(text)

    assert result.risk_score == 0.90
    assert "DNI (Spain)" in result.rationale
    assert "Credit Card (Visa)" in result.rationale
    assert "Email" in result.rationale
    assert len(result.matches) == 3


def test_pii_scanner_with_custom_validators() -> None:
    custom_validators = {
        "Custom ID": lambda val: val.endswith("99"),
    }
    scanner = PiiScanner(
        extra_patterns=[("Custom ID", r"CID-\d{4}")],
        validate_checksums=True,
        custom_validators=custom_validators,
    )

    # CID-1234 should be rejected by custom validator
    result_invalid = scanner.scan("CID-1234")
    assert result_invalid.risk_score == 0.0
    assert result_invalid.matches == []

    # CID-1299 ends with 99 and should pass
    result_valid = scanner.scan("CID-1299")
    assert result_valid.risk_score == 0.80
    assert len(result_valid.matches) == 1
    assert "Custom ID" in result_valid.rationale


def test_pii_scanner_initialization_attributes() -> None:
    scanner = PiiScanner(validate_checksums=True)
    assert scanner.validate_checksums is True
