import pytest
from cerbia.core.scanners.secret._defaults import CONNECTION_STRING_RULE, GENERIC_SECRET_RULE
from cerbia.core.scanners.secret._filters import suppress_builtin_match

pytestmark = pytest.mark.unit


@pytest.mark.parametrize("key", ["password1", "pass%77ord2", "user1", "api_key2", "clientSecret3"])
def test_retains_connection_when_query_key_is_numbered_credential(key: str) -> None:
    # Given
    text = f"mysql://db.example.test/app?{key}=supersecret"
    match = CONNECTION_STRING_RULE[1].search(text)
    assert match is not None
    # When
    suppressed = suppress_builtin_match(CONNECTION_STRING_RULE, match)
    # Then
    assert suppressed is False


@pytest.mark.parametrize("scheme", ["redis", "REDIS"])
def test_retains_connection_when_redis_has_multiple_hosts(scheme: str) -> None:
    # Given
    text = f"{scheme}://cache.example.test,other.example.test/0"
    match = CONNECTION_STRING_RULE[1].search(text)
    assert match is not None
    # When
    suppressed = suppress_builtin_match(CONNECTION_STRING_RULE, match)
    # Then
    assert suppressed is False


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
    text = f"{scheme}://{address}"
    match = CONNECTION_STRING_RULE[1].search(text)
    assert match is not None
    # When
    suppressed = suppress_builtin_match(CONNECTION_STRING_RULE, match)
    # Then
    assert suppressed is True


@pytest.mark.parametrize("scheme", ["mongodb", "postgres", "mysql"])
def test_suppresses_connection_when_all_hosts_are_valid(scheme: str) -> None:
    # Given
    text = f"{scheme}://node-a:1234,[2001:db8::2]:4321,node-b/app?replicaSet=rs0"
    match = CONNECTION_STRING_RULE[1].search(text)
    assert match is not None
    # When
    suppressed = suppress_builtin_match(CONNECTION_STRING_RULE, match)
    # Then
    assert suppressed is True


@pytest.mark.parametrize("quote", ["'", '"'])
def test_suppresses_connection_when_whole_url_is_quoted(quote: str) -> None:
    # Given
    text = f"DB={quote}postgres://database.internal:5432/app?sslmode=require{quote}"
    match = CONNECTION_STRING_RULE[1].search(text)
    assert match is not None
    # When
    suppressed = suppress_builtin_match(CONNECTION_STRING_RULE, match)
    # Then
    assert suppressed is True


@pytest.mark.parametrize("scheme", ["mongodb", "postgres", "mysql", "redis"])
@pytest.mark.parametrize("userinfo", ["alice@", "alice:password123@", "%61lice@", ":@", "alice%3Apass@"])
def test_retains_connection_when_any_userinfo_exists(scheme: str, userinfo: str) -> None:
    # Given
    text = f"{scheme}://{userinfo}database.internal/app"
    match = CONNECTION_STRING_RULE[1].search(text)
    assert match is not None
    # When
    suppressed = suppress_builtin_match(CONNECTION_STRING_RULE, match)
    # Then
    assert suppressed is False


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
    match = CONNECTION_STRING_RULE[1].search(text)
    assert match is not None
    # When
    suppressed = suppress_builtin_match(CONNECTION_STRING_RULE, match)
    # Then
    assert suppressed is False


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
    match = CONNECTION_STRING_RULE[1].search(text)
    assert match is not None
    # When
    suppressed = suppress_builtin_match(CONNECTION_STRING_RULE, match)
    # Then
    assert suppressed is False


@pytest.mark.parametrize("key", ["secret", "password", "passwd", "pwd", "PASSWORD"])
@pytest.mark.parametrize("reference", ["${oc.env:DB_PASSWORD}", "${oc.env:_PASS2}", "${settings.password}"])
@pytest.mark.parametrize("quote", ["", "'", '"'])
def test_suppresses_assignment_when_entire_value_is_supported_reference(key: str, reference: str, quote: str) -> None:
    # Given
    text = f"{key} = {quote}{reference}{quote}"
    match = GENERIC_SECRET_RULE[1].search(text)
    assert match is not None
    # When
    suppressed = suppress_builtin_match(GENERIC_SECRET_RULE, match)
    # Then
    assert suppressed is True


@pytest.mark.parametrize(
    "value",
    [
        "${oc.env:PASS,default}",
        "${oc.env:PASS:-default}",
        "${oc.env:9PASS}",
        "${OC.env:PASS}",
        "${env:PASS}",
        "${PASSWORD}",
        "${settings}",
        "${settings..password}",
        "${settings.password",
        "${settings.${password}}",
        r"\${settings.password}",
        "prefix${settings.password}",
        "${settings.password}literal",
        "${settings.password}${settings.other}",
        "'${settings.password}literal'",
        '"${settings.password} literal"',
        "'${settings.password}",
        "'${settings.password}\"",
        "'${settings.password}'literal",
        "'${settings.password}'+literal",
        "'${settings.password}' + 'literal'",
        "${settings.password} + literal",
        "${settings.password}'literal'",
        '"${settings.password}\\"literal"',
        "${settings.password} literal",
        "'${settings.password}' literal",
        "${settings.password} ${settings.other}",
    ],
)
def test_retains_assignment_when_value_is_not_whole_supported_reference(value: str) -> None:
    # Given
    text = f"password={value}"
    match = GENERIC_SECRET_RULE[1].search(text)
    assert match is not None
    # When
    suppressed = suppress_builtin_match(GENERIC_SECRET_RULE, match)
    # Then
    assert suppressed is False


@pytest.mark.parametrize("suffix", ["suffix=supersecret", "suffix:supersecret"])
def test_retains_reference_when_yaml_plain_scalar_has_assignment_suffix(suffix: str) -> None:
    # Given
    text = f"password: ${{settings.password}} {suffix}"
    match = GENERIC_SECRET_RULE[1].search(text)
    assert match is not None
    # When
    suppressed = suppress_builtin_match(GENERIC_SECRET_RULE, match)
    # Then
    assert suppressed is False
