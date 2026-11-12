from logging import getLogger
from re import Match
from urllib.parse import parse_qs, urlparse

from ..._utils.url import extract_urls, format_url_finding
from ...models.scans import MatchSpan, ScanOutcome
from ...registries.url import UrlRegistry
from ...types import Action, ContentType, Severity
from ._constants import (
    DATA_URI_PATTERN,
    PERCENT_ENCODING_RE,
    PERCENT_ENCODING_THRESHOLD,
    PUNYCODE_PATTERN,
    REDIRECT_PARAMS,
)
from ._defaults import DEFAULT_POPULAR_DOMAINS, DEFAULT_SHORTENER_DOMAINS, DEFAULT_SUSPICIOUS_TLDS
from ._validations import check_typosquatting, is_ip_url

logger = getLogger(__name__)


def _data_uri_display_ranges(text: str) -> list[tuple[int, int]]:
    ranges: list[tuple[int, int]] = []
    for header in DATA_URI_PATTERN.finditer(text):
        end = header.end()
        while end < len(text) and not text[end].isspace() and text[end] not in "\"'<>":
            end += 1

        ranges.append((header.start(), end))

    return ranges


class MaliciousUrlScanner:
    """Detects potentially malicious URLs via heuristic analysis.

    Checks URLs against: suspicious TLDs, IP-based hosts, shorteners, redirect parameters, punycode/IDN, excessive
    subdomains, data URIs, percent-encoding obfuscation, and typosquatting.

    Args:
        severity (Severity): Severity level for produced findings.
        action (Action): Action to take when malicious URLs are detected.
        suspicious_tlds (list[str] | None): TLDs to flag as suspicious. Defaults to a built-in set.
        shortener_domains (list[str] | None): URL shortener domains to flag. Defaults to a built-in set.
        popular_domains (list[str] | None): Domains to check for typosquatting against. Defaults to a built-in set.
        url_registry (UrlRegistry | None): Optional registry of allowed URLs to skip scanning. Defaults to None.
        redact (bool): Remove URL credentials, query, and fragment from rationale and hide data URI payloads.
            Defaults to True. False preserves raw legacy diagnostic snippets. Hosts, paths, ports, and detection
            reasons remain visible; redirect parameter names use canonical lowercase spelling when redacted.

    Attributes:
        scanner_id (str): Unique identifier for the scanner.
        scanner_name (str): Human-readable name for the scanner.
        severity (Severity): Severity level for produced findings.
        action (Action): Action to take when malicious URLs are detected.
        content_types (tuple[ContentType, ...]): Content types to scan for malicious URLs.
    """

    def __init__(
        self,
        severity: Severity = Severity.HIGH,
        action: Action = Action.BLOCK,
        suspicious_tlds: list[str] | None = None,
        shortener_domains: list[str] | None = None,
        popular_domains: list[str] | None = None,
        url_registry: UrlRegistry | None = None,
        content_types: tuple[ContentType, ...] | list[str] | None = (
            ContentType.TEXT,
            ContentType.URL,
            ContentType.CODE,
        ),
        redact: bool = True,
    ) -> None:
        self.scanner_id = "url_malicious"
        self.scanner_name = "Malicious URL"
        self.severity = severity
        self.action = action
        self.content_types = tuple(content_types) if content_types is not None else None
        self._suspicious_tlds = frozenset(suspicious_tlds) if suspicious_tlds is not None else DEFAULT_SUSPICIOUS_TLDS
        self._shortener_domains = (
            frozenset(shortener_domains) if shortener_domains is not None else DEFAULT_SHORTENER_DOMAINS
        )
        self._popular_domains = frozenset(popular_domains) if popular_domains is not None else DEFAULT_POPULAR_DOMAINS
        self._url_registry = url_registry
        self._redact = redact

    def scan(self, text: str) -> ScanOutcome:
        """Scan text for malicious URL indicators.

        Args:
            text (str): Input text to analyse.

        Returns:
            ScanOutcome: Verdict containing safety flag, risk score, rationale, and optional match spans.
        """
        data_uri_match = DATA_URI_PATTERN.search(text)
        data_uri_detected = data_uri_match is not None
        urls = extract_urls(text)
        if not urls and not data_uri_detected:
            logger.debug(
                "No URLs found",
                extra={
                    "operation": "scan",
                    "stage": "scanning",
                    "component_kind": "scanner",
                    "outcome": "completed",
                    "candidate_count": 0,
                    "match_count": 0,
                },
            )
            return ScanOutcome(risk_score=0.0, rationale="No URLs found")

        if self._url_registry:
            candidate_count = len(urls)
            urls = [u for u in urls if not self._url_registry.is_allowed(u.group())]
            if not urls and not data_uri_detected:
                logger.debug(
                    "All URLs found are registered as allowed",
                    extra={
                        "operation": "scan",
                        "stage": "scanning",
                        "component_kind": "scanner",
                        "outcome": "completed",
                        "candidate_count": candidate_count,
                        "match_count": 0,
                    },
                )
                return ScanOutcome(risk_score=0.0, rationale="All URLs on allowlist")

        candidate_count = len(urls)
        flags: list[tuple[str, str, float]] = []
        matches: list[MatchSpan] = []

        if data_uri_match is not None:
            data_uri_snippet = (
                "[REDACTED]" if self._redact else text[data_uri_match.start() : data_uri_match.start() + 60]
            )
            flags.append(("Data URI", data_uri_snippet, 0.9))
            matches.append(MatchSpan(start=data_uri_match.start(), end=data_uri_match.end()))

        display_ranges = _data_uri_display_ranges(text) if self._redact else []
        for url in urls:
            url_flags = self._check_url_match(url, display_ranges)
            flags.extend(url_flags)
            if url_flags:
                matches.append(MatchSpan(start=url.start(), end=url.end()))

        if not flags:
            logger.debug(
                "%s URLs evaluated and found safe",
                candidate_count,
                extra={
                    "operation": "scan",
                    "stage": "scanning",
                    "component_kind": "scanner",
                    "outcome": "completed",
                    "candidate_count": candidate_count,
                    "match_count": 0,
                },
            )
            return ScanOutcome(risk_score=0.0, rationale=f"All {len(urls)} URL(s) appear safe")

        max_risk_score = max(f[2] for f in flags)
        detail = "; ".join(f"{reason} ({url_snip})" for reason, url_snip, _ in flags[:5])
        rationale = f"Suspicious URL(s) ({len(flags)} flag(s)): {detail}"
        match_count = len(flags)
        logger.debug(
            "%s matches found",
            match_count,
            extra={
                "operation": "scan",
                "stage": "scanning",
                "component_kind": "scanner",
                "outcome": "completed",
                "candidate_count": candidate_count,
                "match_count": match_count,
            },
        )
        return ScanOutcome(risk_score=max_risk_score, rationale=rationale, matches=matches)

    def _check_url_match(self, url: Match[str], display_ranges: list[tuple[int, int]]) -> list[tuple[str, str, float]]:
        flags = self._check_url(url.group())
        if any(url.start() < end and start < url.end() for start, end in display_ranges):
            return [(reason, "[REDACTED]", score) for reason, _, score in flags]

        return flags

    def _check_url(self, url: str) -> list[tuple[str, str, float]]:
        flags: list[tuple[str, str, float]] = []
        snip = format_url_finding(url) if self._redact else url[:60]

        try:
            parsed = urlparse(url)
        except Exception:
            flags.append(("Unparseable URL", snip, 0.7))
            return flags

        hostname = (parsed.hostname or "").lower()

        if is_ip_url(hostname):
            flags.append(("IP-based URL", snip, 0.8))

        tld = hostname.rsplit(".", 1)[-1] if "." in hostname else ""
        if tld in self._suspicious_tlds:
            flags.append((f"Suspicious TLD (.{tld})", snip, 0.75))

        if hostname in self._shortener_domains or any(hostname.endswith("." + d) for d in self._shortener_domains):
            flags.append(("URL shortener", snip, 0.7))

        flags.extend(self._check_redirect_query(parsed.query, snip))

        if PUNYCODE_PATTERN.search(hostname):
            flags.append(("Punycode/IDN domain", snip, 0.85))

        if hostname.count(".") > 3:
            flags.append(("Excessive subdomains", snip, 0.65))

        if len(PERCENT_ENCODING_RE.findall(url)) > PERCENT_ENCODING_THRESHOLD:
            flags.append(("URL-encoding obfuscation", snip, 0.75))

        typosquat_target = check_typosquatting(hostname, self._popular_domains)
        if typosquat_target:
            flags.append((f"Possible typosquatting of {typosquat_target}", snip, 0.85))

        return flags

    def _check_redirect_query(self, query: str, snip: str) -> list[tuple[str, str, float]]:
        for param_name in parse_qs(query):
            if param_name.lower() in REDIRECT_PARAMS:
                display_param = param_name.lower() if self._redact else param_name
                return [(f"Redirect param '{display_param}'", snip, 0.8)]

        return []
