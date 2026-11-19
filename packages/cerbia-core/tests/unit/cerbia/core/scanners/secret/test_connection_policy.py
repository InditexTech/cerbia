import pytest
from cerbia.core.scanners.secret import SecretScanner

pytestmark = pytest.mark.unit


@pytest.mark.parametrize("key", ["password1", "pass%77ord2", "user1", "api_key2", "clientSecret3"])
def test_retains_connection_when_query_key_is_numbered_credential(key: str) -> None:
    # Given
    text = f"mysql://db.example.test/app?{key}=supersecret"
    # When
    result = SecretScanner().scan(text)
    # Then
    assert result.risk_score == 0.85
    assert [(span.start, span.end) for span in result.matches] == [(0, len(text))]


@pytest.mark.parametrize("scheme", ["redis", "REDIS"])
def test_retains_connection_when_redis_has_multiple_hosts(scheme: str) -> None:
    # Given
    text = f"{scheme}://cache.example.test,other.example.test/0"
    # When
    result = SecretScanner().scan(text)
    # Then
    assert result.risk_score == 0.85
    assert [(span.start, span.end) for span in result.matches] == [(0, len(text))]


@pytest.mark.parametrize("scheme", ["mongodb", "postgres", "mysql", "redis"])
@pytest.mark.parametrize(
    "address",
    [
        "database.internal:1234/app",
        "database.internal",
        "[2001:db8::1]:1234/app",
        "database.internal/app?ssl=true&applicationName=my%20app",
        "database.internal/app?unknown_option=ordinary-value&retryWrites=true",
        "database.internal/app?%73slmode=require&timeout=3000",
    ],
)
def test_suppresses_connection_when_credentials_are_absent(scheme: str, address: str) -> None:
    # Given
    scanner = SecretScanner()
    # When
    result = scanner.scan(f"{scheme}://{address}")
    # Then
    assert result.risk_score == 0
    assert result.matches == []


@pytest.mark.parametrize("scheme", ["mongodb", "postgres", "mysql"])
def test_suppresses_connection_when_all_hosts_are_valid(scheme: str) -> None:
    # Given
    text = f"{scheme}://node-a:1234,[2001:db8::2]:4321,node-b/app?replicaSet=rs0"
    # When
    result = SecretScanner().scan(text)
    # Then
    assert result.matches == []


@pytest.mark.parametrize("quote", ["'", '"'])
def test_suppresses_connection_when_whole_url_is_quoted(quote: str) -> None:
    # Given
    text = f"DB={quote}postgres://database.internal:5432/app?sslmode=require{quote}"
    # When
    result = SecretScanner().scan(text)
    # Then
    assert result.matches == []


@pytest.mark.parametrize("scheme", ["mongodb", "postgres", "mysql", "redis"])
@pytest.mark.parametrize("userinfo", ["alice@", "alice:password123@", "%61lice@", ":@", "alice%3Apass@"])
def test_retains_connection_when_any_userinfo_exists(scheme: str, userinfo: str) -> None:
    # Given
    text = f"{scheme}://{userinfo}database.internal/app"
    # When
    result = SecretScanner().scan(text)
    # Then
    assert result.risk_score == 0.85
    assert [(span.start, span.end) for span in result.matches] == [(0, len(text))]


@pytest.mark.parametrize(
    "query",
    [
        "user=alice",
        "username=alice",
        "password=x",
        "passwd=x",
        "pwd=x",
        "secret=x",
        "token=x",
        "api_key=x",
        "access_token=x",
        "clientSecret=x",
        "db-password=x",
        "%75ser=alice",
        "pass%77ord=x",
        "api%5Fkey=x",
        "option=password%3Dx",
        "option=user:pass@host",
        "option=https%3A%2F%2Falice%3Apass%40host",
        "option=AKIAAAAAAAAAAAAAAAAA",
        "option=ghp_" + "a" * 36,
        "option=Bearer%20abc123",
        "option=%2570assword%253Dx",
        "option=%FF",
        "option=%ZZ",
        "option=x%26password%3Dx",
        "option=x;y=z",
        "flag",
        "=value",
        "option=pwd%3Ax",
        "option=password%3Ashort",
        "option=user%3Dalice",
        "option=x%3Fy",
        "option=one%2Ftwo",
        "option=%2526token",
        "option=x%23fragment",
        "option=%3Cunsafe%3E",
        "AKIAAAAAAAAAAAAAAAAA=ordinary",
        "option=%60unsafe%60",
    ],
)
def test_retains_connection_when_query_contains_credentials_or_ambiguity(query: str) -> None:
    # Given
    text = f"postgres://database.internal/app?{query}"
    # When
    result = SecretScanner().scan(text)
    # Then
    assert result.risk_score >= 0.85
    assert (0, len(text)) in [(span.start, span.end) for span in result.matches]


@pytest.mark.parametrize(
    "address",
    [
        "database.internal:bad/app",
        "database.internal:99999/app",
        "database.internal:/app",
        "database.internal,,other/app",
        "database.internal,evil:bad/app",
        "database.internal,/app",
        "database.internal,[not-ipv6]/app",
        "[2001:db8::1/app",
        "[2001:db8::1]junk/app",
        "2001:db8::1/app",
        "database.internal/app#fragment",
        "database.internal/app%ZZ",
        "database.internal/app%252fpassword",
        "database.internal/app%40alice",
        "database.internal/app;password=x",
        "database.internal/app\\suffix",
        'database.internal/app"suffix',
        "database.internal/app?ssl=true#token",
        "database.internal/app?ssl=true&",
        "database.internal/app?option=%0Asecret",
        "database.internal/app%2Fpassword",
        "database.internal/app%3Fpassword=x",
        "database.internal:0/app",
        "database.internal:12:34/app",
        "-database.internal/app",
        "database..internal/app",
        "database.internal,[2001:db8::1]:bad/app",
        "[fe80::1%25eth0]/app",
    ],
)
def test_retains_connection_when_url_is_malformed_or_ambiguous(address: str) -> None:
    # Given
    text = f"mongodb://{address}"
    # When
    result = SecretScanner().scan(text)
    # Then
    assert result.risk_score >= 0.85
    assert (0, len(text)) in [(span.start, span.end) for span in result.matches]


def test_preserves_surviving_connection_spans_when_safe_and_real_urls_are_mixed() -> None:
    # Given
    real = 'postgres://alice@database.internal/app"'
    text = f'mongodb://database.internal/app\nDB="{real}\nredis://cache.internal:6379/0'
    # When
    result = SecretScanner().scan(text)
    # Then
    start = text.index("postgres://")
    assert [(span.start, span.end) for span in result.matches] == [(start, start + len(real))]
    assert result.risk_score == 0.85
    assert result.rationale == "Secret(s) detected (1): Connection String"
