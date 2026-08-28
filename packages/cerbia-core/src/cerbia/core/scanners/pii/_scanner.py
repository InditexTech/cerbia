import logging
import re

from ...models.scans import MatchSpan, ScanOutcome
from ...types import Action, ContentType, Severity
from ._constants import PII_PATTERNS

logger = logging.getLogger(__name__)


class PiiScanner:
    """Detects personally identifiable information (PII) in text.

    Args:
        extra_patterns (list[tuple[str, str]] | None): Additional ``(name, regex_string)`` pairs.
        severity (Severity): Severity level for produced findings.
        action (Action): Action to take when PII is detected.

    Attributes:
        scanner_id (str): Unique identifier for the scanner.
        scanner_name (str): Human-readable name for the scanner.
        severity (Severity): Severity level for produced findings.
        action (Action): Action to take when PII is detected.
    """

    def __init__(
        self,
        extra_patterns: list[tuple[str, str]] | None = None,
        severity: Severity = Severity.HIGH,
        action: Action = Action.WARN,
        content_types: tuple[ContentType, ...] | list[str] | None = (ContentType.TEXT,),
    ) -> None:
        self.scanner_id = "pii"
        self.scanner_name = "PII"
        self.severity = severity
        self.action = action
        self.content_types = tuple(content_types) if content_types is not None else None

        self._patterns = PII_PATTERNS.copy()
        if extra_patterns:
            for name, regex in extra_patterns:
                self._patterns.append((name, re.compile(regex), 0.80))

    def scan(self, text: str) -> ScanOutcome:
        """Scan text for personally identifiable information.

        Args:
            text (str): Input text to analyse.

        Returns:
            ScanOutcome: Verdict with match spans for detected PII.
        """
        hits: list[tuple[str, float]] = []
        matches: list[MatchSpan] = []

        for name, pattern, risk_score in self._patterns:
            for match in pattern.finditer(text):
                hits.append((name, risk_score))
                matches.append(MatchSpan(start=match.start(), end=match.end()))

        if not hits:
            outcome = ScanOutcome(risk_score=0.0, rationale="No PII detected")
            logger.debug(
                "No matches found",
                extra={
                    "operation": "scan",
                    "stage": "detection",
                    "component_kind": "scanner",
                    "outcome": "completed",
                    "match_count": len(hits),
                },
            )
            return outcome

        max_risk = max(h[1] for h in hits)
        type_counts: dict[str, int] = {}
        for name, _ in hits:
            type_counts[name] = type_counts.get(name, 0) + 1

        summary = ", ".join(f"{name} ({count})" for name, count in list(type_counts.items())[:5])
        outcome = ScanOutcome(
            risk_score=max_risk,
            rationale=f"PII detected ({len(hits)} match(es)): {summary}",
            matches=matches,
        )

        match_count = len(hits)
        logger.debug(
            "%s matches found",
            match_count,
            extra={
                "operation": "scan",
                "stage": "detection",
                "component_kind": "scanner",
                "outcome": "completed",
                "match_count": match_count,
            },
        )
        return outcome
