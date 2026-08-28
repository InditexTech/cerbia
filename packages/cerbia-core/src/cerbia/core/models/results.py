from pydantic import BaseModel, Field, computed_field

from .entries import Entry
from .scans import Finding, SkippedScanner

__all__ = ["EntryResult", "ScanResult"]


class EntryResult(BaseModel):
    """Scan results for a single :class:`Entry`.

    Attributes:
        entry (Entry): The input entry that was scanned.
        is_safe (bool): Whether the gate passed for this entry.
        aggregated_score (float): Aggregated risk score across blocked scanners, ``0.0`` to ``1.0``.
        rationale (str): Summary explanation of the gate verdict.
        findings (list[Finding]): Individual scanner results collected during the scan.
        skipped_scanners (list[SkippedScanner]): Scanners skipped due to content-type routing or the explicit
            ``"skip"`` on error policy.
    """

    entry: Entry
    is_safe: bool = True
    aggregated_score: float = Field(ge=0.0, le=1.0, default=0.0)
    rationale: str = ""
    findings: list[Finding] = Field(default_factory=list)
    skipped_scanners: list[SkippedScanner] = Field(default_factory=list)


class ScanResult(BaseModel):
    """Top-level aggregation across all entries.

    Attributes:
        entry_results (list[EntryResult]): Per-entry scan outcomes.
        is_safe (bool): Whether all entries passed all gates.
        total_findings (int): Total number of findings across all entry results.
        unsafe_entries (int): Number of entry results where is_safe is False.
    """

    entry_results: list[EntryResult] = Field(default_factory=list)

    @computed_field
    @property
    def is_safe(self) -> bool:
        """Whether all entries passed all gates.

        Returns:
            bool: True if all entry results are safe, False otherwise.
        """
        return all(er.is_safe for er in self.entry_results)

    @computed_field
    @property
    def total_findings(self) -> int:
        """Total number of findings across all entry results.

        Returns:
            int: Sum of findings across all entry results.
        """
        return sum(len(er.findings) for er in self.entry_results)

    @computed_field
    @property
    def unsafe_entries(self) -> int:
        """Number of entry results where is_safe is False.

        Returns:
            int: Count of unsafe entry results.
        """
        return sum(1 for er in self.entry_results if not er.is_safe)
