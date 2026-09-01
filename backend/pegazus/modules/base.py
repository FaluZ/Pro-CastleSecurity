from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass
from pathlib import Path

from pegazus.core.models import Severity


@dataclass
class ScanContext:
    """Contexto compartido que el orquestador pasa a cada modulo durante un escaneo."""

    project_root: Path
    scan_id: int


@dataclass
class ModuleFinding:
    """Hallazgo producido por un modulo, antes de persistirse como Finding en la DB."""

    title: str
    description: str
    severity: Severity
    file_path: str
    line: int | None = None
    evidence: str | None = None
    rule_id: str | None = None
    module: str | None = None  # p.ej. "malware.yara"; si es None se usa AnalysisModule.name


class AnalysisModule(ABC):
    """Un dominio de deteccion (malware, inyecciones, EtherHiding, Contagious Interview, ...).

    El orquestador no conoce las subclases concretas: las obtiene de
    modules/registry.py y las invoca sobre cada archivo enumerado por el walker.
    Anadir un modulo nuevo no requiere tocar el orquestador, la API ni el frontend.
    """

    name: str

    def scan_project(self, context: ScanContext) -> list[ModuleFinding]:
        """Chequeos a nivel de proyecto, ejecutados una vez por escaneo (opcional)."""
        return []

    @abstractmethod
    def scan_file(self, file_path: Path, context: ScanContext) -> list[ModuleFinding]:
        """Chequeos por archivo, ejecutados para cada archivo enumerado por el walker."""
        raise NotImplementedError
