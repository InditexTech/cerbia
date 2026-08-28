from abc import ABC, abstractmethod
from typing import Any

from pydantic import BaseModel, ConfigDict, Field

from .types import ScannerErrorPolicy

__all__ = [
    "PreprocessorConfig",
    "ScannerConfig",
    "ScoreAggregatorConfig",
    "LoaderConfig",
    "CerbIAConfig",
]


class ComponentConfig(BaseModel, ABC):
    """Configuration for an individual component.

    Attributes:
        init_args (dict[str, Any]): Keyword arguments forwarded to the component constructor.
    """

    init_args: dict[str, Any] = Field(default_factory=dict)

    @property
    @abstractmethod
    def component(self) -> str:
        """Return the fully qualified import path to the component class.

        Returns:
            str: Fully qualified import path to the component class.
        """


class PreprocessorConfig(ComponentConfig):
    """Configuration for an individual preprocessor.

    Attributes:
        preprocessor (str): Fully qualified import path to the preprocessor class.
        init_args (dict[str, Any]): Keyword arguments forwarded to the preprocessor constructor.
    """

    preprocessor: str
    init_args: dict[str, Any] = Field(default_factory=dict)

    @property
    def component(self) -> str:
        """Return the fully qualified import path to the preprocessor class.

        Returns:
            str: Fully qualified import path to the preprocessor class.
        """
        return self.preprocessor


class ScannerConfig(ComponentConfig):
    """Configuration for an individual scanner.

    Attributes:
        scanner (str): Fully qualified import path to the scanner class..
        init_args (dict[str, Any]): Keyword arguments forwarded to the scanner constructor.
    """

    scanner: str
    init_args: dict[str, Any] = Field(default_factory=dict)

    @property
    def component(self) -> str:
        """Return the fully qualified import path to the scanner class.

        Returns:
            str: Fully qualified import path to the scanner class.
        """
        return self.scanner


class ScoreAggregatorConfig(ComponentConfig):
    """Configuration for an individual score aggregator.

    Attributes:
        score_aggregator (str): Fully qualified import path to the aggregator class.
        init_args (dict[str, Any]): Keyword arguments forwarded to the aggregator constructor.
    """

    score_aggregator: str
    init_args: dict[str, Any] = Field(default_factory=dict)

    @property
    def component(self) -> str:
        """Return the fully qualified import path to the score aggregator class.

        Returns:
            str: Fully qualified import path to the score aggregator class.
        """
        return self.score_aggregator


class LoaderConfig(ComponentConfig):
    """Configuration for the input loader.

    Attributes:
        loader (str): Fully qualified import path to the loader class.
        init_args (dict[str, Any]): Keyword arguments forwarded to the loader constructor.
    """

    loader: str
    init_args: dict[str, Any] = Field(default_factory=dict)

    @property
    def component(self) -> str:
        """Return the fully qualified import path to the loader class.

        Returns:
            str: Fully qualified import path to the loader class.
        """
        return self.loader


class CerbIAConfig(BaseModel):
    """Root configuration model.

    Each config defines a single security gate with its own loaders, preprocessors, scanners, and score aggregation
    strategy.

    Attributes:
        name (str): Gate identifier (e.g. ``"prompt-scan"``).
        loaders (list[LoaderConfig]): Loaders that produce entries to scan.
        preprocessors (list[PreprocessorConfig]): Preprocessor pipeline.
        fail_fast (bool): Stop scanning after the first blocking failure.
        threshold (float): Minimum aggregated score to trigger a block verdict. ``0.0`` means any BLOCK finding fails
            the gate. Range ``[0.0, 1.0]``.
        on_scanner_error (ScannerErrorPolicy): How scanner execution errors affect the verdict.
        scanners (list[ScannerConfig]): Ordered list of scanners.
        score_aggregator (ScoreAggregatorConfig): Score aggregation strategy.
    """

    model_config = ConfigDict(extra="forbid")

    name: str
    loaders: list[LoaderConfig] = Field(default_factory=list)
    preprocessors: list[PreprocessorConfig] = Field(default_factory=list)
    fail_fast: bool = True
    threshold: float = Field(default=0.0, ge=0.0, le=1.0)
    on_scanner_error: ScannerErrorPolicy = ScannerErrorPolicy.BLOCK
    scanners: list[ScannerConfig] = Field(default_factory=list)
    score_aggregator: ScoreAggregatorConfig
