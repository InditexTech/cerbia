import inspect

import pytest
from cerbia.core import preprocessors
from cerbia.core.preprocessors.speculative_decoding import (
    SpeculativeDecodingPreprocessor as PackageSpeculativeDecodingPreprocessor,
)

pytestmark = pytest.mark.unit


def test_speculative_decoding_preprocessor_is_exported_from_supported_packages() -> None:
    assert preprocessors.speculative_decoding.__all__ == ["SpeculativeDecodingPreprocessor"]
    assert preprocessors.SpeculativeDecodingPreprocessor is PackageSpeculativeDecodingPreprocessor


def test_speculative_decoding_preprocessor_documentation_describes_configuration_contract() -> None:
    documentation = inspect.getdoc(PackageSpeculativeDecodingPreprocessor)

    assert documentation is not None
    assert "decode" in documentation.lower()
    assert "Args:" in documentation
    assert "intensive_mode" in documentation
    assert "Raises:" in documentation
    assert "ValueError" in documentation
