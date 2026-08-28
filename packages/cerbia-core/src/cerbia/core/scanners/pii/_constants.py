import re

_OCTET = r"(?:25[0-5]|2[0-4]\d|[01]?\d\d?)"

_AT_BLOCK = r"\s*[(\[]\s*(?:at|arroba)\s*[)\]]\s*"
_DOT_BLOCK = r"\s*[(\[]\s*(?:dot|punto)\s*[)\]]\s*"

PII_PATTERNS: list[tuple[str, re.Pattern[str], float]] = [
    ("Email", re.compile(r"[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}"), 0.90),
    ("Email (obfuscated)", re.compile(rf"(?i)[a-z0-9._%+-]+{_AT_BLOCK}[a-z0-9.-]+{_DOT_BLOCK}[a-z]{{2,}}"), 0.85),
    ("Phone (International)", re.compile(r"\+\d{1,3}[\s.-]?\d{2,4}[\s.-]?\d{3,4}[\s.-]?\d{3,4}"), 0.80),
    (
        "Phone (North American)",
        re.compile(r"(?<!\d)(?:\+1[\s.-]?)?\(?[2-9]\d{2}\)?[\s.-]?[2-9]\d{2}[\s.-]?\d{4}(?!\d)"),
        0.85,
    ),
    ("Phone (Spanish)", re.compile(r"(?<!\d)(?:\+34[\s.-]?)?[6-9]\d{2}[\s.-]?\d{3}[\s.-]?\d{3}(?!\d)"), 0.85),
    (
        "Phone (Chinese)",
        re.compile(r"(?<!\d)(?:\+86[\s.-]?)?(?:13\d|14[5-9]|15[0-35-9]|166|17[0-8]|18\d|19[89])\d{8}(?!\d)"),
        0.85,
    ),
    ("DNI (Spain)", re.compile(r"(?<!\w)\d{8}[A-HJ-NP-TV-Z](?!\w)"), 0.90),
    ("NIE (Spain)", re.compile(r"(?<!\w)[XYZ]\d{7}[A-Z](?!\w)"), 0.90),
    ("IBAN", re.compile(r"(?i)(?<![a-z0-9])[a-z]{2}\d{2}(?:[ -]?[a-z0-9]){11,30}(?![a-z0-9])"), 0.92),
    ("Credit Card (Visa)", re.compile(r"(?<!\d)4\d{3}[\s-]?\d{4}[\s-]?\d{4}[\s-]?\d{4}(?!\d)"), 0.80),
    (
        "Credit Card (Mastercard)",
        re.compile(
            r"(?<!\d)(?:5[1-5]\d{2}|2(?:2[2-9]\d|[3-6]\d{2}|7(?:[01]\d|20)))[\s-]?\d{4}[\s-]?\d{4}[\s-]?\d{4}(?!\d)"
        ),
        0.80,
    ),
    ("Credit Card (Amex)", re.compile(r"(?<!\d)3[47]\d{2}[\s-]?\d{6}[\s-]?\d{5}(?!\d)"), 0.80),
    ("Credit Card (Discover)", re.compile(r"(?<!\d)6(?:011|5\d{2})[\s-]?\d{4}[\s-]?\d{4}[\s-]?\d{4}(?!\d)"), 0.80),
    (
        "Credit Card (JCB)",
        re.compile(r"(?<!\d)(?:2131|1800)\d{11}(?!\d)|(?<!\d)35\d{2}[\s-]?\d{4}[\s-]?\d{4}[\s-]?\d{4}(?!\d)"),
        0.80,
    ),
    (
        "Credit Card (Diners Club)",
        re.compile(r"(?<!\d)3(?:0[0-5]|[68]\d)\d[\s-]?\d{4}[\s-]?\d{4}[\s-]?\d{2}(?!\d)"),
        0.80,
    ),
    ("Credit Card (UnionPay)", re.compile(r"(?<!\d)62\d{2}[\s-]?\d{4}[\s-]?\d{4}[\s-]?\d{4,7}(?!\d)"), 0.80),
    ("IPv4", re.compile(rf"(?<!\d){_OCTET}(?:\.{_OCTET}){{3}}(?!\d)"), 0.70),
    (
        "IPv6",
        re.compile(
            r"(?i)(?<![\w:])(?:(?:[0-9a-f]{1,4}:){1,7}[0-9a-f]{1,4}|(?:[0-9a-f]{1,4}:){1,6}:|"
            r"(?:[0-9a-f]{1,4}:){1,5}(?::[0-9a-f]{1,4}){1,2}|(?:[0-9a-f]{1,4}:){1,4}(?::[0-9a-f]{1,4}){1,3}|"
            r"(?:[0-9a-f]{1,4}:){1,3}(?::[0-9a-f]{1,4}){1,4}|(?:[0-9a-f]{1,4}:){1,2}(?::[0-9a-f]{1,4}){1,5}|"
            r"[0-9a-f]{1,4}:(?:(?::[0-9a-f]{1,4}){1,6})|:(?:(?::[0-9a-f]{1,4}){1,7}|:))(?![\w:])"
        ),
        0.70,
    ),
    ("SSN (US)", re.compile(r"(?<!\d)\d{3}-\d{2}-\d{4}(?!\d)"), 0.90),
    ("EIN (US)", re.compile(r"(?<!\d)\d{2}-\d{7}(?!\d)"), 0.90),
    ("ITIN (US)", re.compile(r"(?<!\d)9\d{2}-[7-9]\d-\d{4}(?!\d)"), 0.90),
    ("SIN (Canada)", re.compile(r"(?<!\d)\d{3}[ -]\d{3}[ -]\d{3}(?!\d)"), 0.90),
    (
        "National Insurance Number (UK)",
        re.compile(r"(?i)(?<!\w)(?!(?:BG|GB|KN|NK|NT|TN|ZZ))[A-CEGHJ-PR-TW-Z]{2}\d{6}[A-D](?!\w)"),
        0.90,
    ),
    ("CPF (Brazil)", re.compile(r"(?<!\d)\d{3}\.?\d{3}\.?\d{3}-?\d{2}(?!\d)"), 0.90),
    (
        "CURP (Mexico)",
        re.compile(r"(?i)(?<!\w)[A-Z][AEIOUX][A-Z]{2}\d{6}[HM][A-Z]{5}[A-Z0-9]\d(?!\w)"),
        0.90,
    ),
    (
        "Aadhaar (India)",
        re.compile(r"(?i)(?<!\w)aadhaar\s*(?:no\.?|number)?\s*[:#]?\s*\d{4}\s?\d{4}\s?\d{4}(?!\d)"),
        0.90,
    ),
    ("IMEI", re.compile(r"(?i)(?<!\w)imei\s*[:#]?\s*\d{15}(?!\d)"), 0.85),
    ("IMSI", re.compile(r"(?i)(?<!\w)imsi\s*[:#]?\s*\d{14,15}(?!\d)"), 0.85),
    ("MAC Address", re.compile(r"(?i)(?<![\w:])(?:[0-9a-f]{2}:){5}[0-9a-f]{2}(?![\w:])"), 0.75),
    ("UUID", re.compile(r"(?i)(?<!\w)[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}(?!\w)"), 0.75),
    ("Bitcoin Address", re.compile(r"(?<!\w)[13][a-km-zA-HJ-NP-Z0-9]{25,34}(?!\w)"), 0.80),
    ("Bitcoin Address (Bech32)", re.compile(r"(?i)(?<!\w)bc1[ac-hj-np-z02-9]{11,71}(?!\w)"), 0.80),
    ("Ethereum Address", re.compile(r"(?i)(?<!\w)0x[0-9a-f]{40}(?!\w)"), 0.80),
]
