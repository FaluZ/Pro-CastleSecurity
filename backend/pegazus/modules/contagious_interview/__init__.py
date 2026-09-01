from __future__ import annotations

from pathlib import Path

from pegazus.modules.base import AnalysisModule, ModuleFinding, ScanContext
from pegazus.modules.contagious_interview.vscode_tasks import check_autorun_tasks


class ContagiousInterviewModule(AnalysisModule):
    """Persistencia via VS Code -- patron caracteristico de la campana Contagious Interview.

    Hoy cubre la ejecucion automatica de tareas al abrir la carpeta
    (.vscode/tasks.json + .vscode/settings.json). Es un chequeo de proyecto,
    no de archivo: solo mira los dos puntos de configuracion conocidos, no
    recorre todo el arbol de archivos.
    """

    name = "contagious_interview"

    def scan_file(self, file_path: Path, context: ScanContext) -> list[ModuleFinding]:
        return []

    def scan_project(self, context: ScanContext) -> list[ModuleFinding]:
        return check_autorun_tasks(context.project_root)
