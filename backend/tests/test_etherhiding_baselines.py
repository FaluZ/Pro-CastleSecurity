from __future__ import annotations

from pathlib import Path

from pegazus.modules.etherhiding.baselines import check_size_anomaly


def test_expected_size_is_not_flagged() -> None:
    path = Path("AppData/Local/Discord/app-1.0/resources/discord_desktop_core/index.js")

    findings = check_size_anomaly(path, 41)

    assert findings == []


def test_much_larger_size_is_flagged() -> None:
    path = Path("AppData/Local/Discord/app-1.0/resources/discord_desktop_core/index.js")

    findings = check_size_anomaly(path, 250_000)

    assert len(findings) == 1
    assert findings[0].severity.value == "high"


def test_unrelated_file_is_not_checked() -> None:
    findings = check_size_anomaly(Path("src/index.js"), 250_000)

    assert findings == []
