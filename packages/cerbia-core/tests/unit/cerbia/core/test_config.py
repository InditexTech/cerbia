import pytest
from cerbia.core.config import ComponentConfig, LoaderConfig, PreprocessorConfig, ScannerConfig, ScoreAggregatorConfig

pytestmark = pytest.mark.unit


@pytest.mark.parametrize(
    ("config", "expected_component"),
    [
        (LoaderConfig(loader="cerbia.loaders.FileLoader"), "cerbia.loaders.FileLoader"),
        (PreprocessorConfig(preprocessor="cerbia.preprocessors.Normalize"), "cerbia.preprocessors.Normalize"),
        (ScannerConfig(scanner="cerbia.scanners.PromptInjection"), "cerbia.scanners.PromptInjection"),
        (
            ScoreAggregatorConfig(score_aggregator="cerbia.score_aggregators.Maximum"),
            "cerbia.score_aggregators.Maximum",
        ),
    ],
    ids=["loader", "preprocessor", "scanner", "score_aggregator"],
)
def test_component_config_returns_configured_component_path(config: ComponentConfig, expected_component: str) -> None:
    result = config.component

    assert result == expected_component
