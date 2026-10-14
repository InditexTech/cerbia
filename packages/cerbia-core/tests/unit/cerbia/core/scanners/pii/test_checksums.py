import pytest
from cerbia.core.scanners.pii import PiiScanner
from cerbia.core.scanners.pii._checksums import (
    validate_cpf_checksum,
    validate_dni_checksum,
    validate_iban_checksum,
    validate_imei_checksum,
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
        ("¹²³⁴⁵⁶⁷⁸Z", False),
        ("12345678¹", False),
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
        ("X¹²³⁴⁵⁶⁷L", False),
        ("X1234567¹", False),
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
        ("⁴¹¹¹ 1111 1111 1111", False),
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
        ("ES⁹¹ 2100 0418 4502 0005", False),
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
        ("⁵²⁹⁹⁸²²⁴⁷²⁵", False),
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


def test_pii_scanner_iban_with_following_text() -> None:
    scanner = PiiScanner(validate_checksums=True)

    # Compact IBAN followed by text: match span must end exactly at the IBAN
    text_compact = "ES9121000418450200051332 hello"
    res_compact = scanner.scan(text_compact)
    assert res_compact.risk_score == 0.92
    assert len(res_compact.matches) == 1
    assert res_compact.matches[0].start == 0
    assert res_compact.matches[0].end == 24
    assert text_compact[res_compact.matches[0].start : res_compact.matches[0].end] == "ES9121000418450200051332"

    # Spaced IBAN followed by text: match span must end exactly at the IBAN
    text_spaced = "ES91 2100 0418 4502 0005 1332 hello"
    res_spaced = scanner.scan(text_spaced)
    assert res_spaced.risk_score == 0.92
    assert len(res_spaced.matches) == 1
    assert res_spaced.matches[0].start == 0
    assert res_spaced.matches[0].end == 29
    assert text_spaced[res_spaced.matches[0].start : res_spaced.matches[0].end] == "ES91 2100 0418 4502 0005 1332"


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


@pytest.mark.parametrize(
    ("imei", "expected"),
    [
        ("IMEI: 490154203237518", True),
        ("imei 490154203237518", True),
        ("IMEI#490154203237518", True),
        ("490154203237518", True),
        ("49-015420-323751-8", True),
        ("IMEI: 490154203237519", False),
        ("IMEI: 49015420323751", False),
        ("IMEI: 4901542032375188", False),
        ("IMEI: 49015420323751A", False),
        ("IMEI: ⁴⁹⁰¹⁵⁴²⁰³²³⁷⁵¹⁸", False),
        ("", False),
    ],
)
def test_validate_imei_checksum(imei: str, expected: bool) -> None:
    assert validate_imei_checksum(imei) is expected


def test_pii_scanner_imei_labeled_checksum() -> None:
    scanner = PiiScanner(validate_checksums=True)

    # Valid labeled IMEI must be detected with checksum enabled
    text_valid = "Device IMEI: 490154203237518 registered"
    res_valid = scanner.scan(text_valid)
    assert res_valid.risk_score == 0.85
    assert "IMEI" in res_valid.rationale
    assert len(res_valid.matches) == 1
    assert text_valid[res_valid.matches[0].start : res_valid.matches[0].end] == "IMEI: 490154203237518"

    # Invalid checksum labeled IMEI must be discarded when validate_checksums=True
    text_invalid = "Device IMEI: 490154203237519 registered"
    res_invalid = scanner.scan(text_invalid)
    assert res_invalid.risk_score == 0.0
    assert res_invalid.matches == []


@pytest.mark.parametrize(
    "iban",
    [
        "ES9121000418450200051332",
        "ES91 21000418450200051332",
        "ES91 2100 0418 4502 0005 1332",
        "ES91-2100-0418-4502-0005-1332",
        "DE89370400440532013000",
        "DE89 3704 0044 0532 0130 00",
        "GB29NWBK60161331926819",
        "GB29 NWBK 6016 1331 9268 19",
        "IQ90BAPI000000000000123",
        "IQ90 BAPI 0000 0000 0000 123",
    ],
)
def test_pii_scanner_iban_formats_and_spacing_followed_by_text(iban: str) -> None:
    scanner = PiiScanner(validate_checksums=True)
    text = f"{iban} hello"
    res = scanner.scan(text)
    assert res.risk_score == 0.92
    assert len(res.matches) == 1
    assert "IBAN" in res.rationale
    assert text[res.matches[0].start : res.matches[0].end] == iban
