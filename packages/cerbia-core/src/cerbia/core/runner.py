import logging

from .config import CerbIAConfig
from .exceptions import CerbIAConfigError
from .factories import LoaderFactory, PreprocessorFactory, ScannerFactory, ScoreAggregatorFactory
from .loaders.base import Loader
from .models.entries import Entry
from .models.results import EntryResult, ScanResult
from .preprocessors.base import Preprocessor
from .registries.url import UrlRegistry
from .scanners.base import Scanner
from .security_gate import SecurityGate

__all__ = ["Runner"]

logger = logging.getLogger(__name__)


class Runner:
    """Orchestrates the security scanning pipeline for a single gate.

    Builds loaders, preprocessors, and one security gate from configuration. During a scan, entries are loaded
    from all loaders, preprocessed (producing derived entries), then all entries are run through the gate.

    Args:
        config (CerbIAConfig): Flat configuration defining loaders, preprocessors, scanners, score aggregator, and
            fail-fast behavior.

    Attributes:
        loaders (list[Loader]): List of configured loaders.
        preprocessors (list[Preprocessor]): List of configured preprocessors.
        scanners (list[Scanner]): List of configured scanners.
        score_aggregator (ScoreAggregator): The configured score aggregator for the gate.
        gate (SecurityGate): The security gate that runs all configured scanners.
    """

    def __init__(self, config: CerbIAConfig) -> None:
        self._build_loaders(config)
        self._build_preprocessors(config)
        self._build_scanners(config)
        self._build_score_aggregator(config)

        self.gate: SecurityGate = SecurityGate(
            name=config.name,
            scanners=self.scanners,
            fail_fast=config.fail_fast,
            score_aggregator=self.score_aggregator,
            threshold=config.threshold,
            on_scanner_error=config.on_scanner_error,
        )

    def _build_loaders(self, config: CerbIAConfig) -> None:
        if not config.loaders:
            raise CerbIAConfigError("No loaders configured: set at least one loader")

        self.loaders: list[Loader] = [LoaderFactory.build(lc) for lc in config.loaders]

    def _build_preprocessors(self, config: CerbIAConfig) -> None:
        self.preprocessors: list[Preprocessor] = [PreprocessorFactory.build(pc) for pc in config.preprocessors]

    def _build_scanners(self, config: CerbIAConfig) -> None:
        if not config.scanners:
            raise CerbIAConfigError("No scanners configured: set at least one scanner")

        scanners: list[Scanner] = []
        url_registry = UrlRegistry()
        for sc in config.scanners:
            scanner = ScannerFactory.build(sc, url_registry=url_registry)
            scanners.append(scanner)

        self.scanners = scanners

    def _build_score_aggregator(self, config: CerbIAConfig) -> None:
        self.score_aggregator = ScoreAggregatorFactory.build(config.score_aggregator)

    def _preprocess(self, entries: list[Entry]) -> list[Entry]:
        for preprocessor in self.preprocessors:
            entries = preprocessor.process(entries)

        return entries

    def scan(self) -> ScanResult:
        """Load entries from all configured loaders, preprocess them, and run the security gate.

        Returns:
            ScanResult: Aggregated results for all entries from all loaders.
        """
        logger.debug(
            "Runner scan started",
            extra={
                "operation": "scan",
                "stage": "execution",
                "component_kind": "runner",
                "outcome": "started",
            },
        )
        entries: list[Entry] = []
        for loader in self.loaders:
            entries.extend(loader.load())

        entries = self._preprocess(entries)

        entry_results: list[EntryResult] = []
        for entry in entries:
            gate_result = self.gate.scan(entry.text, content_type=entry.content_type)
            entry_results.append(
                EntryResult(
                    entry=entry,
                    is_safe=gate_result.is_safe,
                    aggregated_score=gate_result.score,
                    rationale=gate_result.rationale,
                    findings=gate_result.findings,
                    skipped_scanners=gate_result.skipped_scanners,
                )
            )

        result_count = len(entry_results)
        logger.debug(
            "%s Scan results collected",
            result_count,
            extra={
                "operation": "scan",
                "stage": "execution",
                "component_kind": "runner",
                "outcome": "completed",
                "result_count": result_count,
            },
        )
        return ScanResult(entry_results=entry_results)
