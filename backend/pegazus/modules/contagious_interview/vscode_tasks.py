from __future__ import annotations

import re
from pathlib import Path

from pegazus.core.models import Severity
from pegazus.modules.base import ModuleFinding

_RUN_ON_FOLDER_OPEN = re.compile(r'"runOn"\s*:\s*"folderOpen"')
_ALLOW_AUTOMATIC_TASKS = re.compile(r'"task\.allowAutomaticTasks"\s*:\s*(true|"on")')
_HIDDEN_REVEAL = re.compile(r'"reveal"\s*:\s*"never"')
_HIDDEN_FLAG = re.compile(r'"hide"\s*:\s*true')


def check_autorun_tasks(project_root: Path) -> list[ModuleFinding]:
    """Detecta ejecucion automatica de tareas de VS Code al abrir la carpeta.

    Requiere la combinacion de .vscode/tasks.json con "runOn": "folderOpen" Y
    .vscode/settings.json con "task.allowAutomaticTasks" habilitado -- ambas
    condiciones son necesarias para que VS Code corra algo sin build ni
    confirmacion del usuario, solo con abrir la carpeta.
    """
    tasks_path = project_root / ".vscode" / "tasks.json"
    settings_path = project_root / ".vscode" / "settings.json"
    if not tasks_path.exists() or not settings_path.exists():
        return []

    tasks_text = _read_text(tasks_path)
    settings_text = _read_text(settings_path)
    if tasks_text is None or settings_text is None:
        return []

    has_autorun_task = bool(_RUN_ON_FOLDER_OPEN.search(tasks_text))
    allows_automatic = bool(_ALLOW_AUTOMATIC_TASKS.search(settings_text))
    if not (has_autorun_task and allows_automatic):
        return []

    is_hidden = bool(_HIDDEN_REVEAL.search(tasks_text) and _HIDDEN_FLAG.search(tasks_text))
    severity = Severity.CRITICAL if is_hidden else Severity.HIGH
    description = (
        "'.vscode/tasks.json' define una tarea con \"runOn\": \"folderOpen\" y "
        "'.vscode/settings.json' tiene \"task.allowAutomaticTasks\" habilitado: la "
        "tarea se ejecuta automaticamente solo con abrir la carpeta en VS Code, sin "
        "necesidad de build ni confirmacion del usuario."
    )
    if is_hidden:
        description += (
            " Ademas, usa \"reveal\": \"never\" + \"hide\": true, lo que oculta la "
            "ejecucion en la terminal integrada: el usuario no veria ningun rastro "
            "visual."
        )

    evidence = "runOn=folderOpen, task.allowAutomaticTasks habilitado"
    if is_hidden:
        evidence += ", reveal=never+hide=true"

    return [
        ModuleFinding(
            module="contagious_interview.vscode_autorun",
            title="Ejecucion automatica de tareas de VS Code al abrir la carpeta",
            description=description,
            severity=severity,
            file_path=str(tasks_path),
            evidence=evidence,
        )
    ]


def _read_text(path: Path) -> str | None:
    try:
        return path.read_text(encoding="utf-8", errors="ignore")
    except OSError:
        return None
