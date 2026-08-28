from importlib import import_module
from types import ModuleType

import pytest

pytestmark = pytest.mark.unit


@pytest.mark.unit
def test_cerbia_core_package_is_importable() -> None:
    module: ModuleType = import_module("cerbia.core")

    assert module.__name__ == "cerbia.core"
