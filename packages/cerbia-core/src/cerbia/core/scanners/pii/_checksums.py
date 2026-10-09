import re
from collections.abc import Callable

DNI_CONTROL_LETTERS = "TRWAGMYFPDXBNJZSQVHLCKE"
NIE_PREFIX_MAP = {"X": "0", "Y": "1", "Z": "2"}


def validate_dni_checksum(value: str) -> bool:
    """Validate a Spanish DNI (Documento Nacional de Identidad) using modulo 23.

    Args:
        value (str): The DNI string to validate (e.g. ``'12345678Z'`` or ``'12345678-Z'``).

    Returns:
        bool: True if the control letter matches the modulo 23 calculation, False otherwise.
    """
    cleaned = re.sub(r"[\s-]", "", value).upper()
    if len(cleaned) != 9:
        return False

    digits_part = cleaned[:8]
    letter_part = cleaned[8]

    if not digits_part.isdigit() or not letter_part.isalpha():
        return False

    number = int(digits_part)
    expected_letter = DNI_CONTROL_LETTERS[number % 23]
    return letter_part == expected_letter


def validate_nie_checksum(value: str) -> bool:
    """Validate a Spanish NIE (Número de Identidad de Extranjero) using modulo 23.

    Args:
        value (str): The NIE string to validate (e.g. ``'X1234567L'`` or ``'Y1234567X'``).

    Returns:
        bool: True if the control letter matches the modulo 23 calculation, False otherwise.
    """
    cleaned = re.sub(r"[\s-]", "", value).upper()
    if len(cleaned) != 9:
        return False

    prefix = cleaned[0]
    if prefix not in NIE_PREFIX_MAP:
        return False

    digits_part = cleaned[1:8]
    letter_part = cleaned[8]

    if not digits_part.isdigit() or not letter_part.isalpha():
        return False

    number = int(NIE_PREFIX_MAP[prefix] + digits_part)
    expected_letter = DNI_CONTROL_LETTERS[number % 23]
    return letter_part == expected_letter


def validate_luhn_checksum(value: str) -> bool:
    """Validate a numeric sequence using the Luhn algorithm (modulo 10 / ISO/IEC 7812-1).

    Args:
        value (str): Number string (spaces and hyphens will be ignored).

    Returns:
        bool: True if the sequence satisfies the Luhn checksum, False otherwise.
    """
    digits = [int(c) for c in value if c.isdigit()]
    if len(digits) < 2:
        return False

    checksum = 0
    for index, digit in enumerate(reversed(digits)):
        if index % 2 == 1:
            doubled = digit * 2
            checksum += doubled - 9 if doubled > 9 else doubled
        else:
            checksum += digit

    return checksum % 10 == 0


def validate_iban_checksum(value: str) -> bool:
    """Validate an International Bank Account Number (IBAN) using ISO 7064 MOD 97-10.

    Args:
        value (str): IBAN string (spaces and hyphens will be ignored).

    Returns:
        bool: True if the IBAN satisfies the modulo 97 check, False otherwise.
    """
    cleaned = re.sub(r"[\s-]", "", value).upper()
    if len(cleaned) < 15 or len(cleaned) > 34:
        return False

    if not (cleaned[:2].isalpha() and cleaned[2:4].isdigit() and cleaned.isalnum()):
        return False

    rearranged = cleaned[4:] + cleaned[:4]
    numeric_str = "".join(str(ord(c) - 55) if c.isalpha() else c for c in rearranged)
    return int(numeric_str) % 97 == 1


def validate_cpf_checksum(value: str) -> bool:
    """Validate a Brazilian CPF using modulo 11.

    Args:
        value (str): CPF string (dots and hyphens will be ignored).

    Returns:
        bool: True if the CPF satisfies the two check digits, False otherwise.
    """
    digits = [int(c) for c in value if c.isdigit()]
    if len(digits) != 11 or len(set(digits)) == 1:
        return False

    sum1 = sum(d * (10 - i) for i, d in enumerate(digits[:9]))
    rem1 = (sum1 * 10) % 11
    d9 = 0 if rem1 >= 10 else rem1
    if digits[9] != d9:
        return False

    sum2 = sum(d * (11 - i) for i, d in enumerate(digits[:10]))
    rem2 = (sum2 * 10) % 11
    d10 = 0 if rem2 >= 10 else rem2
    return digits[10] == d10


CHECKSUM_VALIDATORS: dict[str, Callable[[str], bool]] = {
    "DNI (Spain)": validate_dni_checksum,
    "NIE (Spain)": validate_nie_checksum,
    "IBAN": validate_iban_checksum,
    "Credit Card (Visa)": validate_luhn_checksum,
    "Credit Card (Mastercard)": validate_luhn_checksum,
    "Credit Card (Amex)": validate_luhn_checksum,
    "Credit Card (Discover)": validate_luhn_checksum,
    "Credit Card (JCB)": validate_luhn_checksum,
    "Credit Card (Diners Club)": validate_luhn_checksum,
    "Credit Card (UnionPay)": validate_luhn_checksum,
    "CPF (Brazil)": validate_cpf_checksum,
    "IMEI": validate_luhn_checksum,
}
