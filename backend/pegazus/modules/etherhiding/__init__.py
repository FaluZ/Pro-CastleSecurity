from __future__ import annotations

from pathlib import Path

from pegazus.modules.base import AnalysisModule, ModuleFinding, ScanContext
from pegazus.modules.etherhiding.baselines import check_size_anomaly
from pegazus.modules.etherhiding.filenames import check_suspicious_filename
from pegazus.modules.etherhiding.git_history import scan_git_history
from pegazus.modules.etherhiding.structural import check_long_line, check_whitespace_gap
from pegazus.modules.yara_utils import YaraScanner

RULES_DIR = Path(__file__).resolve().parent / "rules"


class EtherHidingModule(AnalysisModule):
    """Inyeccion de codigo en configs de build + C2 resuelto via blockchain (EtherHiding).

    Combina senales estructurales (linea anomala, patron de padding con
    espacios, anomalia de tamano contra una linea base) -- que sobreviven a
    que el atacante cambie de ofuscador -- con marcadores literales conocidos
    (YARA) y una busqueda en todo el historial de git, no solo el HEAD. Ver
    docs/architecture.md para el detalle de cada tecnica.
    """

    name = "etherhiding"

    def __init__(self) -> None:
        self._yara = YaraScanner(RULES_DIR, module_name="etherhiding.yara")

    def scan_file(self, file_path: Path, context: ScanContext) -> list[ModuleFinding]:
        findings: list[ModuleFinding] = list(check_suspicious_filename(file_path))

        try:
            data = file_path.read_bytes()
        except OSError:
            return findings

        findings.extend(check_size_anomaly(file_path, len(data)))
        findings.extend(check_long_line(file_path, data))
        findings.extend(check_whitespace_gap(file_path, data))
        findings.extend(self._yara.scan_bytes(data, file_path))
        return findings

    def scan_project(self, context: ScanContext) -> list[ModuleFinding]:
        return scan_git_history(context.project_root)
