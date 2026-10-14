# SPDX-FileCopyrightText: 2026 INDUSTRIA DE DISEÑO TEXTIL S.A. (INDITEX S.A.)
#
# SPDX-License-Identifier: Apache-2.0

"""Technical tender and architectural data scanner implementation."""

from __future__ import annotations

import logging

from ...models.scans import MatchSpan, ScanOutcome
from ...types import Action, ContentType, Severity
from ._constants import (
    BC3_RECORD_PATTERN,
    COORDINATE_DECIMAL_PATTERN,
    COORDINATE_DMS_PATTERN,
    COORDINATE_UTM_PATTERN,
    SCORE_BC3,
    SCORE_BUDGET,
    SCORE_COORDINATES,
    SCORE_DOCKET,
    TENDER_BUDGET_PATTERN,
    TENDER_DOCKET_PATTERN,
)

logger = logging.getLogger(__name__)


class TenderDataScanner:
    """Detects confidential architectural tender figures, BC3 records, and high-precision coordinates.

    Scans for:
    1. FIEBDC-3 / BC3 standard bill of quantities and decomposed unit price records.
    2. Construction budgets (PEM - Presupuesto de Ejecución Material, PBL, contractor margins).
    3. Official procurement tender dockets and EU TED notices.
    4. High-precision spatial coordinates (decimal, sexagesimal DMS, UTM) identifying confidential sites.

    Args:
        detect_bc3 (bool): Whether to detect FIEBDC-3/BC3 line records (~V, ~K, ~C, ~D, ~M).
        detect_budgets (bool): Whether to detect PEM, PBL, and contractor margin percentages.
        detect_coordinates (bool): Whether to detect high-precision geographic coordinates.
        detect_dockets (bool): Whether to detect official tender expediente identifiers.
        severity (Severity): Severity level for produced findings.
        action (Action): Action to take when tender data is detected.
        content_types (tuple[ContentType, ...] | list[str] | None): Content types to scan.
    """

    def __init__(
        self,
        detect_bc3: bool = True,
        detect_budgets: bool = True,
        detect_coordinates: bool = True,
        detect_dockets: bool = True,
        severity: Severity = Severity.HIGH,
        action: Action = Action.BLOCK,
        content_types: tuple[ContentType, ...] | list[str] | None = (ContentType.TEXT,),
    ) -> None:
        self.scanner_id = "tender_data"
        self.scanner_name = "Tender Data"
        self.severity = severity
        self.action = action
        self.content_types = tuple(content_types) if content_types is not None else None
        self._detect_bc3 = detect_bc3
        self._detect_budgets = detect_budgets
        self._detect_coordinates = detect_coordinates
        self._detect_dockets = detect_dockets

    def scan(self, text: str) -> ScanOutcome:
        """Scan text for sensitive technical tender data and spatial coordinates.

        Args:
            text (str): Input text to analyse.

        Returns:
            ScanOutcome: Verdict containing safety score, rationale, and exact match spans.
        """
        if not text:
            return ScanOutcome(risk_score=0.0, rationale="No text provided", matches=[])

        matches: list[MatchSpan] = []
        categories: list[str] = []
        scores: list[float] = []

        # 1. Detect FIEBDC-3 / BC3 line records
        if self._detect_bc3:
            for match in BC3_RECORD_PATTERN.finditer(text):
                # Use span of group(1) containing the actual BC3 line
                start, end = match.span(1)
                matches.append(MatchSpan(start=start, end=end))
                categories.append("BC3 Record")
                scores.append(SCORE_BC3)

        # 2. Detect PEM, PBL, and contractor budget figures
        if self._detect_budgets:
            for match in TENDER_BUDGET_PATTERN.finditer(text):
                matches.append(MatchSpan(start=match.start(), end=match.end()))
                categories.append("Tender Budget")
                scores.append(SCORE_BUDGET)

        # 3. Detect high-precision geographic coordinates
        if self._detect_coordinates:
            for match in COORDINATE_DECIMAL_PATTERN.finditer(text):
                matches.append(MatchSpan(start=match.start(), end=match.end()))
                categories.append("Coordinates (Decimal)")
                scores.append(SCORE_COORDINATES)

            for match in COORDINATE_DMS_PATTERN.finditer(text):
                matches.append(MatchSpan(start=match.start(), end=match.end()))
                categories.append("Coordinates (DMS)")
                scores.append(SCORE_COORDINATES)

            for match in COORDINATE_UTM_PATTERN.finditer(text):
                matches.append(MatchSpan(start=match.start(), end=match.end()))
                categories.append("Coordinates (UTM)")
                scores.append(SCORE_COORDINATES)

        # 4. Detect official tender dockets
        if self._detect_dockets:
            for match in TENDER_DOCKET_PATTERN.finditer(text):
                matches.append(MatchSpan(start=match.start(), end=match.end()))
                categories.append("Tender Docket")
                scores.append(SCORE_DOCKET)

        if not matches:
            logger.debug(
                "No tender data or coordinates detected",
                extra={
                    "operation": "scan",
                    "stage": "scanning",
                    "component_kind": "scanner",
                    "scanner_id": self.scanner_id,
                    "matches_found": 0,
                },
            )
            return ScanOutcome(risk_score=0.0, rationale="No confidential tender data detected", matches=[])

        # Sort matches by start offset
        sorted_indices = sorted(range(len(matches)), key=lambda i: matches[i].start)
        sorted_matches = [matches[i] for i in sorted_indices]
        unique_categories = list(dict.fromkeys(categories[i] for i in sorted_indices))

        max_risk = max(scores)
        rationale = f"Confidential tender data detected ({len(matches)} match(es)): {', '.join(unique_categories)}"

        logger.info(
            "Tender data detected",
            extra={
                "operation": "scan",
                "stage": "scanning",
                "component_kind": "scanner",
                "scanner_id": self.scanner_id,
                "matches_found": len(matches),
                "categories": unique_categories,
            },
        )

        return ScanOutcome(risk_score=max_risk, rationale=rationale, matches=sorted_matches)
