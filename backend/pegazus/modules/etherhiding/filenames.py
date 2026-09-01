from __future__ import annotations

import fnmatch
from pathlib import Path

from pegazus.core.models import Severity
from pegazus.modules.base import ModuleFinding

# Nombres/patrones de archivo asociados a artefactos conocidos de esta
# campana (implante o limpiezas previas). Deliberadamente NO se incluye la
# IP del C2 (23.27.13.135) como indicador: el mecanismo la resuelve
# dinamicamente desde una transaccion de Ethereum, asi que un IOC de IP fija
# caducaria de inmediato y daria falsa confianza.
_EXACT_NAMES = {"SvcHostUpdate.py", "97icr5.py"}
_GLOB_PATTERNS = ("*.inz.*", "*.QUARANTINED")


def check_suspicious_filename(file_path: Path) -> list[ModuleFinding]:
    name = file_path.name
    matched: str | None = None
    if name in _EXACT_NAMES:
        matched = name
    else:
        for pattern in _GLOB_PATTERNS:
            if fnmatch.fnmatch(name, pattern):
                matched = pattern
                break

    if matched is None:
        return []

    return [
        ModuleFinding(
            module="etherhiding.filename",
            title="Nombre de archivo asociado a un artefacto conocido de esta campana",
            description=(
                f"El archivo '{name}' coincide con un nombre/patron ('{matched}') visto "
                f"en implantes o limpiezas previas de esta campana. Los nombres exactos "
                f"cambian entre variantes, asi que la ausencia de coincidencia no "
                f"descarta compromiso."
            ),
            severity=Severity.HIGH,
            file_path=str(file_path),
            evidence=matched,
        )
    ]
