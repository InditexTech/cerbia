import pytest
from cerbia.core.exceptions import CerbIAError

pytestmark = pytest.mark.unit


def test_cerbia_error_preserves_message() -> None:
    error = CerbIAError("scan failed")

    assert str(error) == "scan failed"
    assert isinstance(error, Exception)
