from __future__ import annotations

from pathlib import Path

from pegazus.modules.etherhiding.filenames import check_suspicious_filename


def test_exact_known_name_is_flagged() -> None:
    findings = check_suspicious_filename(Path("C:/temp/SvcHostUpdate.py"))

    assert len(findings) == 1
    assert findings[0].severity.value == "high"


def test_quarantined_suffix_is_flagged() -> None:
    findings = check_suspicious_filename(Path("payload.js.QUARANTINED"))

    assert len(findings) == 1


def test_inz_marker_is_flagged() -> None:
    findings = check_suspicious_filename(Path("update.inz.dll"))

    assert len(findings) == 1


def test_ordinary_filename_is_not_flagged() -> None:
    findings = check_suspicious_filename(Path("index.js"))

    assert findings == []
