from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path

from typer.testing import CliRunner

from pegazus.cli import app

runner = CliRunner()


def _git(cwd: Path, *args: str) -> None:
    subprocess.run(["git", *args], cwd=cwd, check=True, capture_output=True)


def _init_repo(path: Path) -> None:
    _git(path, "init", "-q")
    _git(path, "config", "user.email", "test@example.com")
    _git(path, "config", "user.name", "Test")


def test_scan_staged_blocks_on_critical_finding(tmp_path: Path) -> None:
    repo = tmp_path / "repo"
    repo.mkdir()
    _init_repo(repo)

    config = repo / "vite.config.js"
    config.write_text('export default {};\nglobal.i="A8-deadbeef";\n', encoding="utf-8")
    _git(repo, "add", ".")

    result = runner.invoke(app, ["scan-staged", str(repo)])

    assert result.exit_code == 1
    assert "CRITICAL" in result.stdout


def test_scan_staged_passes_clean_files(tmp_path: Path) -> None:
    repo = tmp_path / "repo"
    repo.mkdir()
    _init_repo(repo)

    (repo / "README.md").write_text("hello\n", encoding="utf-8")
    _git(repo, "add", ".")

    result = runner.invoke(app, ["scan-staged", str(repo)])

    assert result.exit_code == 0


def test_scan_staged_with_nothing_staged(tmp_path: Path) -> None:
    repo = tmp_path / "repo"
    repo.mkdir()
    _init_repo(repo)

    result = runner.invoke(app, ["scan-staged", str(repo)])

    assert result.exit_code == 0
    assert "No hay archivos en stage" in result.stdout


def test_scan_diff_flags_changed_file(tmp_path: Path) -> None:
    repo = tmp_path / "repo"
    repo.mkdir()
    _init_repo(repo)

    config = repo / "vite.config.js"
    config.write_text("export default {};\n", encoding="utf-8")
    _git(repo, "add", ".")
    _git(repo, "commit", "-q", "-m", "initial")

    config.write_text('export default {};\nglobal.i="A8-deadbeef";\n', encoding="utf-8")
    _git(repo, "add", ".")
    _git(repo, "commit", "-q", "-m", "pulled change")

    result = runner.invoke(app, ["scan-diff", str(repo), "HEAD~1", "HEAD"])

    assert result.exit_code == 1
    assert "CRITICAL" in result.stdout


def test_scan_diff_with_no_changes(tmp_path: Path) -> None:
    repo = tmp_path / "repo"
    repo.mkdir()
    _init_repo(repo)

    (repo / "README.md").write_text("hello\n", encoding="utf-8")
    _git(repo, "add", ".")
    _git(repo, "commit", "-q", "-m", "initial")

    result = runner.invoke(app, ["scan-diff", str(repo), "HEAD", "HEAD"])

    assert result.exit_code == 0


def test_scan_exits_nonzero_on_blocking_finding(tmp_path: Path) -> None:
    repo = tmp_path / "repo"
    repo.mkdir()
    (repo / "vite.config.js").write_text('global.i="A8-deadbeef";\n', encoding="utf-8")

    result = runner.invoke(app, ["scan", str(repo)])

    assert result.exit_code == 1
    assert "CRITICAL" in result.stdout


def test_scan_exits_zero_on_clean_project(tmp_path: Path) -> None:
    repo = tmp_path / "repo"
    repo.mkdir()
    (repo / "README.md").write_text("hello\n", encoding="utf-8")

    result = runner.invoke(app, ["scan", str(repo)])

    assert result.exit_code == 0


def test_install_hooks_writes_shareable_hooks_and_sets_config(tmp_path: Path) -> None:
    repo = tmp_path / "repo"
    repo.mkdir()
    _init_repo(repo)

    result = runner.invoke(app, ["install-hooks", str(repo)])

    assert result.exit_code == 0
    for name in ("pre-commit", "post-merge", "post-checkout"):
        hook_file = repo / ".githooks" / name
        assert hook_file.exists()
        assert "pegazus scan" in hook_file.read_text(encoding="utf-8")

    for workflow_name in ("pegazus-scan.yml", "pegazus-full-scan.yml"):
        assert (repo / ".github" / "workflows" / workflow_name).exists()

    hooks_path_config = subprocess.run(
        ["git", "config", "core.hooksPath"], cwd=repo, capture_output=True, text=True, check=True
    )
    assert hooks_path_config.stdout.strip() == ".githooks"


def test_install_hooks_without_workflow_flag(tmp_path: Path) -> None:
    repo = tmp_path / "repo"
    repo.mkdir()
    _init_repo(repo)

    result = runner.invoke(app, ["install-hooks", str(repo), "--no-workflow"])

    assert result.exit_code == 0
    assert not (repo / ".github").exists()
    assert (repo / ".githooks" / "pre-commit").exists()


def test_install_hooks_rejects_non_git_directory(tmp_path: Path) -> None:
    not_a_repo = tmp_path / "not-a-repo"
    not_a_repo.mkdir()

    result = runner.invoke(app, ["install-hooks", str(not_a_repo)])

    assert result.exit_code == 1


def test_installed_hooks_actually_block_a_commit(tmp_path: Path) -> None:
    """Verifica el flujo real de punta a punta: hook instalado via core.hooksPath, no copiado a .git/hooks/."""
    repo = tmp_path / "repo"
    repo.mkdir()
    _init_repo(repo)

    install_result = runner.invoke(app, ["install-hooks", str(repo), "--no-workflow"])
    assert install_result.exit_code == 0

    (repo / "vite.config.js").write_text('global.i="A8-deadbeef";\n', encoding="utf-8")
    _git(repo, "add", "vite.config.js")

    # El hook invoca 'pegazus' como comando bare; en un entorno real esto
    # requiere el venv activado o el paquete instalado globalmente. Aca
    # replicamos esa precondicion sin depender de que pytest se haya
    # lanzado con el venv activado.
    scripts_dir = str(Path(sys.executable).resolve().parent)
    env = {**os.environ, "PATH": scripts_dir + os.pathsep + os.environ.get("PATH", "")}

    commit = subprocess.run(
        ["git", "commit", "-m", "intento de commit malicioso"],
        cwd=repo,
        capture_output=True,
        text=True,
        env=env,
    )

    assert commit.returncode != 0
    # git reenvia la salida del hook por stderr independientemente de por
    # donde la haya escrito el hook.
    assert "CRITICAL" in commit.stdout + commit.stderr
