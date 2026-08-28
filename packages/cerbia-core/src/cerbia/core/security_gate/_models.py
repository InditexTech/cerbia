from pydantic import BaseModel

from ..models.scans import Finding, SkippedScanner


class GateVerdict(BaseModel):
    """Lightweight result from SecurityGate's scan.

    Attributes:
        is_safe (bool): Whether the gate passed or failed.
        score (float): The aggregated score from blocked findings.
        rationale (str): Human-readable explanation of the verdict.
        findings (list[Finding]): List of findings from all scanners.
        skipped_scanners (list[SkippedScanner]): List of scanners that were skipped due to incompatible content types or
            errors.
    """

    is_safe: bool
    score: float
    rationale: str
    findings: list[Finding]
    skipped_scanners: list[SkippedScanner]
