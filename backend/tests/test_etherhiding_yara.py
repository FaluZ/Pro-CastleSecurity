from __future__ import annotations

from pathlib import Path

from pegazus.modules.etherhiding import RULES_DIR
from pegazus.modules.yara_utils import YaraScanner


def _scanner() -> YaraScanner:
    return YaraScanner(RULES_DIR, module_name="etherhiding.yara")


def test_detects_a8_marker() -> None:
    findings = _scanner().scan_bytes(b'global.i="A8-abcdef123456";', Path("vite.config.js"))

    matches = [f for f in findings if f.rule_id == "EtherHiding_Implant_Marker_A8"]
    assert len(matches) == 1
    assert matches[0].severity.value == "critical"


def test_detects_bang_marker() -> None:
    findings = _scanner().scan_bytes(b"global['!']='xyz';", Path("vite.config.js"))

    assert any(f.rule_id == "EtherHiding_Implant_Marker_Bang" for f in findings)


def test_detects_app_eval_marker() -> None:
    findings = _scanner().scan_bytes(b"global['e']='app-vscode-eval';", Path("vite.config.js"))

    assert any(f.rule_id == "EtherHiding_Implant_Marker_AppEval" for f in findings)


def test_detects_hidden_node_spawn() -> None:
    data = b"spawn('node', ['-e', payload], { windowsHide: true, detached: true });"

    findings = _scanner().scan_bytes(data, Path("preload.js"))

    matches = [f for f in findings if f.rule_id == "EtherHiding_Hidden_Node_Spawn"]
    assert len(matches) == 1
    assert matches[0].severity.value == "high"


def test_detects_blockchain_rpc_reference() -> None:
    findings = _scanner().scan_bytes(b"const rpc = 'https://1rpc.io/eth';", Path("config.js"))

    matches = [f for f in findings if f.rule_id == "EtherHiding_Blockchain_RPC_Reference"]
    assert len(matches) == 1
    assert matches[0].severity.value == "medium"


def test_create_require_marker_is_info_severity() -> None:
    data = b"const require = createRequire(import.meta.url);"

    findings = _scanner().scan_bytes(data, Path("vite.config.js"))

    matches = [f for f in findings if f.rule_id == "EtherHiding_CreateRequire_Scaffold"]
    assert len(matches) == 1
    assert matches[0].severity.value == "info"


def test_benign_file_has_no_matches(fixtures_dir: Path) -> None:
    data = (fixtures_dir / "benign.txt").read_bytes()

    findings = _scanner().scan_bytes(data, fixtures_dir / "benign.txt")

    assert findings == []
