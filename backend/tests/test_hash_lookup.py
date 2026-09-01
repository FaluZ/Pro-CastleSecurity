from __future__ import annotations

import hashlib
from pathlib import Path

from pegazus.modules.malware.hash_lookup import HashLookup


def test_known_hash_is_flagged(fixtures_dir: Path) -> None:
    file_path = fixtures_dir / "eicar_test.txt"
    data = file_path.read_bytes()
    lookup = HashLookup({hashlib.sha256(data).hexdigest(): "EICAR-Test-File"})

    findings = lookup.check(data, file_path)

    assert len(findings) == 1
    assert findings[0].severity.value == "critical"


def test_unknown_hash_is_not_flagged() -> None:
    lookup = HashLookup({})

    findings = lookup.check(b"contenido benigno", Path("file.txt"))

    assert findings == []
