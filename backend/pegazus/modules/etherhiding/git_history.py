from __future__ import annotations

import re
import subprocess
from pathlib import Path

from pegazus.core.models import Severity
from pegazus.modules.base import ModuleFinding

_TIMEOUT_SECONDS = 30

# Mismos marcadores literales que rules/etherhiding.yar, pero aplicados sobre
# TODO el historial (git log --all), no solo el estado actual de los
# archivos -- para detectar codigo que fue anadido y luego revertido/
# "limpiado" pero sigue enterrado en un commit viejo. Sin IOC de IP fija por
# la misma razon que en filenames.py: el C2 se resuelve dinamicamente.
_PATTERNS: list[tuple[re.Pattern[bytes], Severity, str]] = [
    (re.compile(rb"global\.i=\"A8-"), Severity.CRITICAL, "Marcador de implante (variante A8)"),
    (re.compile(rb"global\['!'\]='"), Severity.CRITICAL, "Marcador de implante (variante Restaurante)"),
    (
        re.compile(rb"global\['e'\]='app-[\w.-]+-eval'"),
        Severity.CRITICAL,
        "Marcador de implante (app-*-eval)",
    ),
    (re.compile(rb"windowsHide"), Severity.MEDIUM, "Uso de windowsHide"),
    (
        re.compile(rb"1rpc\.io|drpc\.org|publicnode\.com|blockscout\.com|blastapi\.io"),
        Severity.MEDIUM,
        "Referencia a RPC publico de Ethereum",
    ),
    (
        re.compile(rb"createRequire\(import\.meta\.url\)"),
        Severity.INFO,
        "Scaffolding createRequire(import.meta.url)",
    ),
]

# Alternancia combinada (regex extendido de git, sintaxis POSIX ERE) para
# encontrar commits candidatos en una sola llamada a git log, en vez de una
# llamada por patron -- el historial completo de un repo puede ser grande.
_COMBINED_PATTERN = (
    r"global\.i=\"A8-"
    r"|global\['!'\]='"
    r"|global\['e'\]='app-[a-zA-Z0-9_.-]+-eval'"
    r"|windowsHide"
    r"|1rpc\.io|drpc\.org|publicnode\.com|blockscout\.com|blastapi\.io"
    r"|createRequire\(import\.meta\.url\)"
)


def scan_git_history(project_root: Path) -> list[ModuleFinding]:
    if not (project_root / ".git").exists():
        return []

    findings: list[ModuleFinding] = []
    for commit_hash, subject in _find_candidate_commits(project_root):
        diff = _show_commit(project_root, commit_hash)
        if diff is None:
            continue
        for pattern, severity, label in _PATTERNS:
            if not pattern.search(diff):
                continue
            findings.append(
                ModuleFinding(
                    module="etherhiding.git_history",
                    title=f"Patron encontrado en el historial de git: {label}",
                    description=(
                        f"El commit {commit_hash} ('{subject}') introduce o modifica "
                        f"contenido que coincide con '{label}'. Puede no estar presente "
                        f"en el estado actual del proyecto -- revisar con "
                        f"'git show {commit_hash}'."
                    ),
                    severity=severity,
                    file_path=str(project_root),
                    evidence=f"commit={commit_hash}",
                )
            )
    return findings


def _find_candidate_commits(project_root: Path) -> list[tuple[str, str]]:
    output = _run_git(project_root, ["log", "--all", "--oneline", "-E", f"-G{_COMBINED_PATTERN}"])
    if output is None:
        return []

    commits: list[tuple[str, str]] = []
    for line in output.decode("utf-8", errors="replace").splitlines():
        line = line.strip()
        if not line:
            continue
        commit_hash, _, subject = line.partition(" ")
        commits.append((commit_hash, subject))
    return commits


def _show_commit(project_root: Path, commit_hash: str) -> bytes | None:
    return _run_git(project_root, ["show", commit_hash])


def _run_git(project_root: Path, args: list[str]) -> bytes | None:
    try:
        result = subprocess.run(
            ["git", *args],
            cwd=project_root,
            capture_output=True,
            timeout=_TIMEOUT_SECONDS,
            check=False,
        )
    except (OSError, subprocess.TimeoutExpired):
        return None

    if result.returncode != 0:
        return None
    return result.stdout
