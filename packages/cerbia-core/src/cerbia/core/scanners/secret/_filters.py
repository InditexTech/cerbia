import re
from ipaddress import IPv6Address
from typing import Final
from urllib.parse import unquote_plus

from ._defaults import CONNECTION_STRING_RULE, DEFAULT_SECRET_PATTERNS, GENERIC_SECRET_RULE

_REFERENCE: Final = re.compile(
    r"\$\{(?:oc\.env:[A-Za-z_][A-Za-z0-9_]*|[A-Za-z_][A-Za-z0-9_]*(?:\.[A-Za-z_][A-Za-z0-9_]*)+)\}"
)
_CREDENTIAL_KEY: Final = re.compile(
    r"(?:user(?:name)?|password|passwd|pwd|secret|token|apikey|accesskey|credentials?)[0-9]*$"
)
_HOST: Final = re.compile(r"(?:[A-Za-z0-9](?:[A-Za-z0-9-]*[A-Za-z0-9])?\.)*[A-Za-z0-9](?:[A-Za-z0-9-]*[A-Za-z0-9])?\.?")
_INVALID_ESCAPE: Final = re.compile(r"%(?![0-9A-Fa-f]{2})")
_ENCODED_STRUCTURE: Final = re.compile(r"%(?:2[134-9bcf]|3[abdf]|40|5[bcd]|7[bd])", re.IGNORECASE)
_CREDENTIAL_ASSIGNMENT: Final = re.compile(
    r"(?i)(?:user(?:name)?|password|passwd|pwd|secret|token|api[_-]?key|access[_-]?token)\s*[:=]"
)


def _ends_value(text: str, end: int) -> bool:
    tail = text[end:]
    return not tail or re.match(r"[ \t]*(?:\r?\n|$)", tail) is not None


def _whole_reference(match: re.Match[str]) -> bool:
    value_start = re.search(r"[=:]\s*", match.group())
    if value_start is None:
        return False

    start = match.start() + value_start.end()
    end = match.end()
    text = match.string

    quote = text[start] if text[start] in "'\"" else ""
    if quote:
        start += 1
        if text[end : end + 1] != quote:
            return False

        end += 1

    return _REFERENCE.fullmatch(text[start : match.end()]) is not None and _ends_value(text, end)


def _valid_host(entry: str) -> bool:
    host, separator, port = entry.partition(":")
    if entry.startswith("["):
        host, closing, suffix = entry[1:].partition("]")
        if not closing or "%" in host or (suffix and not suffix.startswith(":")):
            return False

        try:
            IPv6Address(host)
        except ValueError:
            return False

        separator, port = suffix[:1], suffix[1:]

    elif _HOST.fullmatch(host) is None:
        return False

    return not separator or (port.isascii() and port.isdecimal() and len(port) <= 5 and 0 < int(port) <= 65535)


def _ordinary_query(query: str) -> bool:
    return all(_ordinary_query_pair(pair) for pair in query.split("&"))


def _ordinary_query_pair(pair: str) -> bool:
    key, separator, value = pair.partition("=")
    if not key or not separator or _INVALID_ESCAPE.search(pair) or _ENCODED_STRUCTURE.search(value):
        return False

    try:
        decoded_key = unquote_plus(key, errors="strict")
        decoded_value = unquote_plus(value, errors="strict")
    except UnicodeDecodeError:
        return False

    if not re.fullmatch(r"[A-Za-z_][A-Za-z0-9_.-]*", decoded_key):
        return False

    normalized_key = re.sub(r"[_.-]", "", decoded_key).lower()
    if _CREDENTIAL_KEY.search(normalized_key):
        return False

    if re.fullmatch(r"[A-Za-z0-9._~:/,+ -]*", decoded_value) is None or "://" in decoded_value:
        return False

    if _CREDENTIAL_ASSIGNMENT.search(decoded_value):
        return False

    return not any(
        pattern.search(part) for _, pattern, _ in DEFAULT_SECRET_PATTERNS for part in (decoded_key, decoded_value)
    )


def _credential_free_url(match: re.Match[str]) -> bool:
    candidate = match.group()
    text = match.string
    if match.start() and text[match.start() - 1] in "'\"":
        quote = text[match.start() - 1]
        if not candidate.endswith(quote) or not _ends_value(text, match.end()):
            return False

        candidate = candidate[:-1]

    if re.search(r"[^A-Za-z0-9._~:/?&=,%+\[\]-]", candidate) or _INVALID_ESCAPE.search(candidate):
        return False

    address = candidate.split("://", 1)[1]
    location, query_separator, query = address.partition("?")
    authority, _, path = location.partition("/")
    if "," in authority and match.group(1).lower() not in {"mongodb", "postgres", "mysql"}:
        return False

    if not all(_valid_host(entry) for entry in authority.split(",")):
        return False

    try:
        decoded_path = unquote_plus(path, errors="strict")
    except UnicodeDecodeError:
        return False

    if _ENCODED_STRUCTURE.search(path) or re.fullmatch(r"[A-Za-z0-9._~/-]*", decoded_path) is None:
        return False

    return not query_separator or _ordinary_query(query)


def suppress_builtin_match(rule: tuple[str, re.Pattern[str], float], match: re.Match[str]) -> bool:
    """Filter built-in rules and custom rules with identical tuple contents.

    Args:
        rule (tuple[str, re.Pattern[str], float]): The rule tuple containing the name, pattern, and risk score.
        match (re.Match[str]): The regex match object to be evaluated against the rule.

    Returns:
        bool: True if the match should be suppressed based on the rule, False otherwise.
    """
    return (rule == GENERIC_SECRET_RULE and _whole_reference(match)) or (
        rule == CONNECTION_STRING_RULE and _credential_free_url(match)
    )
