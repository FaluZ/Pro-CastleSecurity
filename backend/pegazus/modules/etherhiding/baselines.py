from __future__ import annotations

from pathlib import Path

from pegazus.core.models import Severity
from pegazus.modules.base import ModuleFinding

# Tamanos de referencia para archivos "shim" pequenos y estables de apps
# Electron instaladas por usuario, indexados por sufijo de ruta relativa.
# Lista deliberadamente pequena: el objetivo es documentar el mecanismo, no
# ser exhaustivo. Anadir entradas a medida que se identifiquen otros shims.
KNOWN_FILE_SIZE_BASELINES: dict[str, int] = {
    "discord_desktop_core/index.js": 41,
}

# Estos archivos de referencia son minusculos, asi que cualquier crecimiento
# sustancial es sospechoso; una tolerancia chica evita falsos positivos por
# diferencias de saltos de linea/BOM sin dejar pasar un reemplazo real.
_TOLERANCE_BYTES = 64


def check_size_anomaly(file_path: Path, size: int) -> list[ModuleFinding]:
    posix = file_path.as_posix()
    for suffix, expected in KNOWN_FILE_SIZE_BASELINES.items():
        if not posix.endswith(suffix):
            continue

        diff = abs(size - expected)
        if diff <= _TOLERANCE_BYTES:
            return []

        return [
            ModuleFinding(
                module="etherhiding.baseline",
                title="Tamano de archivo distinto al esperado para un shim conocido",
                description=(
                    f"'{suffix}' deberia pesar ~{expected} bytes, pero este archivo pesa "
                    f"{size} bytes. Este tipo de shim de una app Electron instalada por "
                    f"usuario casi nunca cambia de tamano; una diferencia grande sugiere "
                    f"que fue modificado o reemplazado."
                ),
                severity=Severity.HIGH,
                file_path=str(file_path),
                evidence=f"expected={expected} actual={size}",
            )
        ]
    return []
