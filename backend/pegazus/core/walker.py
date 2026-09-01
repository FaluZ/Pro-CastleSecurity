from __future__ import annotations

import fnmatch
from dataclasses import dataclass
from pathlib import Path

from pegazus.core.config import settings


_PEGAZUS_PACKAGE_DIR = Path(__file__).resolve().parent.parent


@dataclass
class WalkResult:
    files: list[Path]
    skipped_large: list[Path]


def is_pegazus_own_file(path: Path) -> bool:
    """True si path esta dentro de la instalacion actual del paquete pegazus.

    Los propios modulos de deteccion (reglas YARA, listas de nombres/patrones
    sospechosos) contienen los marcadores literales que buscan, como datos,
    no como amenaza. Sin este chequeo, escanear el codigo fuente de Pegazus
    (o un repo que lo vendorice) genera falsos positivos contra si mismo --
    se confirmo empiricamente antes de agregar esto: 'pegazus scan' sobre su
    propio codigo marcaba 10 hallazgos, incluida 1 critica, todos falsos.
    """
    try:
        return path.resolve().is_relative_to(_PEGAZUS_PACKAGE_DIR)
    except OSError:
        return False


def _load_ignore_patterns(project_root: Path) -> list[str]:
    ignore_file = project_root / ".pegazusignore"
    if not ignore_file.exists():
        return []
    patterns = []
    for line in ignore_file.read_text(encoding="utf-8", errors="ignore").splitlines():
        line = line.strip()
        if line and not line.startswith("#"):
            patterns.append(line)
    return patterns


def _is_ignored(relative_path: Path, patterns: list[str]) -> bool:
    posix = relative_path.as_posix()
    return any(
        fnmatch.fnmatch(posix, pattern) or fnmatch.fnmatch(posix, f"{pattern}/*")
        for pattern in patterns
    )


def walk_project(project_root: Path) -> WalkResult:
    """Enumera los archivos analizables bajo project_root.

    Excluye directorios de infraestructura conocidos (.git, node_modules, ...),
    respeta un .pegazusignore opcional estilo .gitignore, y separa los archivos
    que superan el limite de tamano configurado en vez de fallar sobre ellos.
    """
    patterns = _load_ignore_patterns(project_root)
    files: list[Path] = []
    skipped_large: list[Path] = []

    for path in project_root.rglob("*"):
        if not path.is_file():
            continue
        if is_pegazus_own_file(path):
            continue

        relative = path.relative_to(project_root)
        if any(part in settings.excluded_dir_names for part in relative.parts[:-1]):
            continue
        if patterns and _is_ignored(relative, patterns):
            continue

        try:
            size = path.stat().st_size
        except OSError:
            continue

        if size > settings.max_file_size_bytes:
            skipped_large.append(path)
            continue

        files.append(path)

    return WalkResult(files=files, skipped_large=skipped_large)
