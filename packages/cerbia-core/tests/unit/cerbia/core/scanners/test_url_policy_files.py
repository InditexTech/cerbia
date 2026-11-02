from pathlib import Path
from unittest.mock import patch

import pytest
from cerbia.core.config import ScannerConfig
from cerbia.core.exceptions import CerbIAConfigError
from cerbia.core.factories import ScannerFactory

pytestmark = pytest.mark.unit


@pytest.mark.parametrize("kind", ["allowlist", "denylist"])
def test_policy_reads_utf8_once_when_constructed_from_relative_file(
    kind: str, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    # Given
    monkeypatch.chdir(tmp_path)
    path = Path("rules.TXT")
    path.write_text("\n  # comment\n https://bücher.example/* \nhttps://second.example/*\n", encoding="utf-8")
    key = "allowed_domains" if kind == "allowlist" else "blocked_domains"
    config = ScannerConfig(
        scanner=f"cerbia.core.scanners.Url{kind.removesuffix('list').title()}ListScanner", init_args={key: path}
    )
    # When
    with patch.object(Path, "read_text", autospec=True, side_effect=Path.read_text) as read:
        scanner = ScannerFactory.build(config)
        outcomes = [scanner.scan(url) for url in ("https://bücher.example/docs", "https://second.example/docs")]
    # Then
    read.assert_called_once_with(path, encoding="utf-8")
    assert [outcome.risk_score > 0 for outcome in outcomes] == [kind == "denylist"] * 2


@pytest.mark.parametrize("kind", ["allowlist", "denylist"])
@pytest.mark.parametrize("failure", ["missing", "suffix", "decode", "directory", "permission"])
def test_policy_raises_path_error_when_file_cannot_be_loaded(kind: str, failure: str, tmp_path: Path) -> None:
    # Given
    path = tmp_path / ("rules.csv" if failure == "suffix" else "rules.txt")
    if failure == "directory":
        path.mkdir()
    elif failure != "missing":
        path.write_bytes(b"\xff" if failure == "decode" else b"https://example.com/*")
    key = "allowed_domains" if kind == "allowlist" else "blocked_domains"
    config = ScannerConfig(
        scanner=f"cerbia.core.scanners.Url{kind.removesuffix('list').title()}ListScanner",
        init_args={key: path},
    )
    # When / Then
    if failure == "permission":
        with (
            patch.object(Path, "read_text", side_effect=PermissionError("denied")),
            pytest.raises(CerbIAConfigError) as error,
        ):
            ScannerFactory.build(config)
    else:
        with pytest.raises(CerbIAConfigError) as error:
            ScannerFactory.build(config)
    assert str(path) in str(error.value)


@pytest.mark.parametrize("kind", ["allowlist", "denylist"])
def test_policy_reports_line_when_file_rule_fails_existing_compiler(kind: str, tmp_path: Path) -> None:
    # Given
    path = tmp_path / "rules.txt"
    path.write_text("# comment\n\nhttps://[invalid]/\n", encoding="utf-8")
    key = "allowed_domains" if kind == "allowlist" else "blocked_domains"
    config = ScannerConfig(
        scanner=f"cerbia.core.scanners.Url{kind.removesuffix('list').title()}ListScanner",
        init_args={key: path},
    )
    # When / Then
    with pytest.raises(CerbIAConfigError) as error:
        ScannerFactory.build(config)
    assert f"{path}:3" in str(error.value)


@pytest.mark.parametrize("kind", ["allowlist", "denylist"])
def test_policy_keeps_inline_comments_literal_when_loading_rules(kind: str, tmp_path: Path) -> None:
    # Given
    path = tmp_path / "rules.txt"
    path.write_text("not a URL [literal]\n* # literal\n", encoding="utf-8")
    key = "allowed_domains" if kind == "allowlist" else "blocked_domains"
    config = ScannerConfig(
        scanner=f"cerbia.core.scanners.Url{kind.removesuffix('list').title()}ListScanner", init_args={key: path}
    )
    scanner = ScannerFactory.build(config)
    # When
    outcome = scanner.scan("https://example.com/")
    # Then
    assert outcome.risk_score == (0.95 if kind == "allowlist" else 0.0)
