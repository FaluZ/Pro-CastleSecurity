from __future__ import annotations

import re
from pathlib import Path

from pegazus.core.models import Severity
from pegazus.modules.base import ModuleFinding

# Umbral practico: en un archivo de configuracion de build, una linea de mas
# de ~400 bytes es anomala -- estos archivos suelen tener lineas cortas y
# bien formateadas. Senal observada de forma consistente en varias variantes
# de ofuscacion distintas de la misma campana; no depende de strings
# literales, asi que sobrevive a que el atacante cambie de ofuscador.
LONG_LINE_THRESHOLD = 400

_BUILD_CONFIG_BASENAMES = {
    "vite.config.js", "vite.config.ts", "vite.config.mjs", "vite.config.cjs",
    "webpack.config.js", "webpack.config.ts", "webpack.mix.js",
    "next.config.js", "next.config.mjs", "next.config.ts",
    "postcss.config.js", "postcss.config.cjs", "postcss.config.mjs",
    "tailwind.config.js", "tailwind.config.cjs", "tailwind.config.mjs",
    "babel.config.js", "babel.config.cjs", ".babelrc", ".babelrc.js", ".babelrc.json",
    "rollup.config.js",
    "jest.config.js", "jest.config.cjs",
}

# El index.js/main.js de una app Electron solo se revisa si esta en la
# ubicacion tipica del proceso principal empaquetado (resources/app...), para
# no generar ruido sobre cualquier index.js/main.js de un proyecto comun.
_ELECTRON_ENTRY_BASENAMES = {"index.js", "main.js"}
_ELECTRON_PATH_MARKERS = ("resources/app", "app.asar.unpacked")

_GAP_PATTERNS = [
    re.compile(rb"\}\)\s*;[ \t]{50,}\S"),
    re.compile(rb"\],?[ \t]{50,}\S"),
]
_GAP_RELEVANT_EXTENSIONS = {".js", ".ts", ".jsx", ".tsx", ".mjs", ".cjs", ".json"}


def _is_watched_config(file_path: Path) -> bool:
    name = file_path.name.lower()
    if name in _BUILD_CONFIG_BASENAMES:
        return True
    if name in _ELECTRON_ENTRY_BASENAMES:
        posix = file_path.as_posix().lower()
        return any(marker in posix for marker in _ELECTRON_PATH_MARKERS)
    return False


def check_long_line(file_path: Path, data: bytes) -> list[ModuleFinding]:
    if not _is_watched_config(file_path):
        return []

    longest = max((len(line) for line in data.split(b"\n")), default=0)
    if longest < LONG_LINE_THRESHOLD:
        return []

    return [
        ModuleFinding(
            module="etherhiding.structural",
            title="Linea anormalmente larga en archivo de configuracion de build",
            description=(
                f"La linea mas larga de '{file_path.name}' tiene {longest} bytes. "
                f"Estos archivos suelen tener lineas cortas; una linea de este tamano "
                f"es consistente con codigo minificado/ofuscado inyectado al final de "
                f"una linea legitima."
            ),
            severity=Severity.MEDIUM,
            file_path=str(file_path),
            evidence=f"longest_line_bytes={longest}",
        )
    ]


def check_whitespace_gap(file_path: Path, data: bytes) -> list[ModuleFinding]:
    if file_path.suffix.lower() not in _GAP_RELEVANT_EXTENSIONS:
        return []

    for pattern in _GAP_PATTERNS:
        match = pattern.search(data)
        if match is None:
            continue
        return [
            ModuleFinding(
                module="etherhiding.structural",
                title="Codigo inyectado tras un cierre legitimo y un salto de espacios",
                description=(
                    "Se encontro un cierre de bloque valido (p.ej. '});' o '],') seguido "
                    "de un bloque grande de espacios/tabs y luego mas codigo en la misma "
                    "linea -- patron caracteristico de codigo anadido manualmente al "
                    "final de una linea existente para pasar desapercibido en un diff "
                    "colapsado."
                ),
                severity=Severity.HIGH,
                file_path=str(file_path),
                evidence=match.group(0)[:80].decode("utf-8", errors="replace"),
            )
        ]
    return []
