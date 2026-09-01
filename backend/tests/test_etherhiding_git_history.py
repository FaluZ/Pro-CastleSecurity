from __future__ import annotations

import subprocess
from pathlib import Path

from pegazus.modules.etherhiding.git_history import scan_git_history


def _git(cwd: Path, *args: str) -> None:
    subprocess.run(["git", *args], cwd=cwd, check=True, capture_output=True)


def _init_repo(path: Path) -> None:
    _git(path, "init", "-q")
    _git(path, "config", "user.email", "test@example.com")
    _git(path, "config", "user.name", "Test")


def test_finds_marker_buried_in_old_commit(tmp_path: Path) -> None:
    repo = tmp_path / "repo"
    repo.mkdir()
    _init_repo(repo)

    config = repo / "vite.config.js"
    config.write_text("export default {}\n", encoding="utf-8")
    _git(repo, "add", ".")
    _git(repo, "commit", "-q", "-m", "initial config")

    config.write_text('export default {}\nglobal.i="A8-deadbeef";\n', encoding="utf-8")
    _git(repo, "add", ".")
    _git(repo, "commit", "-q", "-m", "fix: ajustar formato")

    config.write_text("export default {}\n", encoding="utf-8")
    _git(repo, "add", ".")
    _git(repo, "commit", "-q", "-m", "revert accidental change")

    findings = scan_git_history(repo)

    # git -G marca tanto el commit que introduce el patron como el que lo
    # elimina (la "limpieza"): ambos son forensicamente relevantes.
    matches = [f for f in findings if "A8" in f.title]
    assert len(matches) == 2
    assert all(f.severity.value == "critical" for f in matches)


def test_clean_history_has_no_findings(tmp_path: Path) -> None:
    repo = tmp_path / "repo"
    repo.mkdir()
    _init_repo(repo)

    (repo / "README.md").write_text("hello\n", encoding="utf-8")
    _git(repo, "add", ".")
    _git(repo, "commit", "-q", "-m", "initial")

    findings = scan_git_history(repo)

    assert findings == []


def test_non_git_directory_returns_empty(tmp_path: Path) -> None:
    findings = scan_git_history(tmp_path)

    assert findings == []
