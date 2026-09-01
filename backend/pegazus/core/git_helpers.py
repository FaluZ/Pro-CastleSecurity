from __future__ import annotations

import subprocess
from pathlib import Path

_TIMEOUT_SECONDS = 30
_NULL_SHA = "0" * 40


def get_staged_files(project_root: Path) -> list[Path]:
    """Archivos en stage (git diff --cached), listos para commitear.

    Usado por 'pegazus scan-staged' en un hook pre-commit: revisa solo lo que
    va a entrar en el commit, no todo el repositorio, para que el hook sea
    rapido.
    """
    output = _run_git(
        project_root, ["diff", "--cached", "--name-only", "--diff-filter=ACM"]
    )
    return _resolve_existing_files(project_root, output)


def get_changed_files(project_root: Path, from_ref: str, to_ref: str) -> list[Path]:
    """Archivos que cambiaron entre from_ref y to_ref.

    Usado por 'pegazus scan-diff' en hooks post-merge/post-checkout (git pull
    / git clone). Si from_ref es la referencia nula que git pasa en un
    checkout inicial (no hay estado previo), no hay diff posible: se listan
    todos los archivos versionados en to_ref.
    """
    if from_ref == _NULL_SHA or set(from_ref) == {"0"}:
        output = _run_git(project_root, ["ls-tree", "-r", "--name-only", to_ref])
    else:
        output = _run_git(
            project_root, ["diff", "--name-only", "--diff-filter=ACM", f"{from_ref}..{to_ref}"]
        )
    return _resolve_existing_files(project_root, output)


def _resolve_existing_files(project_root: Path, output: str | None) -> list[Path]:
    if output is None:
        return []

    files: list[Path] = []
    for line in output.splitlines():
        line = line.strip()
        if not line:
            continue
        candidate = project_root / line
        if candidate.is_file():
            files.append(candidate)
    return files


def _run_git(project_root: Path, args: list[str]) -> str | None:
    try:
        result = subprocess.run(
            ["git", *args],
            cwd=project_root,
            capture_output=True,
            text=True,
            timeout=_TIMEOUT_SECONDS,
            check=False,
        )
    except (OSError, subprocess.TimeoutExpired):
        return None

    if result.returncode != 0:
        return None
    return result.stdout
