import pytest
from cerbia.core.types import Action, ContentType, Severity

pytestmark = pytest.mark.unit


@pytest.mark.parametrize(
    ("severity", "expected_weight"),
    [
        (Severity.CRITICAL, 1.0),
        (Severity.HIGH, 0.75),
        (Severity.MEDIUM, 0.5),
        (Severity.LOW, 0.25),
    ],
    ids=["critical", "high", "medium", "low"],
)
def test_severity_type_computes_weight_correctly(severity: Severity, expected_weight: float) -> None:
    result = severity.weight

    assert result == expected_weight


@pytest.mark.parametrize(
    ("action", "expected_value"),
    [(Action.BLOCK, "block"), (Action.WARN, "warn"), (Action.PASS, "pass")],
    ids=["block", "warn", "pass"],
)
def test_action_type_serializes_to_lowercase_value(action: Action, expected_value: str) -> None:
    result = action.value

    assert result == expected_value


@pytest.mark.parametrize(
    ("content_type", "expected_value"),
    [
        (ContentType.TEXT, "text"),
        (ContentType.URL, "url"),
        (ContentType.CODE, "code"),
        (ContentType.UNKNOWN, "unknown"),
    ],
    ids=["text", "url", "code", "unknown"],
)
def test_content_type_serializes_to_lowercase_value(content_type: ContentType, expected_value: str) -> None:
    result = content_type.value

    assert result == expected_value
