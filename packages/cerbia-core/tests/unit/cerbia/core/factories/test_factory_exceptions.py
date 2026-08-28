import pytest
from cerbia.core.exceptions import CerbIAError
from cerbia.core.factories.exceptions import FactoryError

pytestmark = pytest.mark.unit


def test_factory_error_is_subclass_of_cerbia_error_and_preserves_message() -> None:
    error = FactoryError("creation failed")

    assert isinstance(error, CerbIAError)
    assert str(error) == "creation failed"
