import pytest
from cerbia.core.scanners.secret._math import charset_entropy

pytestmark = pytest.mark.unit


def test_secret_math_returns_zero_when_data_is_empty() -> None:
    result = charset_entropy("", frozenset("ab"))

    assert result == 0.0


@pytest.mark.parametrize(
    ("data", "charset", "expected_entropy"),
    [
        ("aaaa", frozenset("a"), 0.0),
        ("aabb", frozenset("ab"), 1.0),
        ("aa!!bb", frozenset("ab"), 1.0),
    ],
    ids=["uniform_characters", "balanced_characters", "out_of_charset_characters"],
)
def test_secret_math_returns_entropy_for_characters_in_configured_charset(
    data: str, charset: frozenset[str], expected_entropy: float
) -> None:
    result = charset_entropy(data, charset)

    assert result == pytest.approx(expected_entropy)
