from __future__ import annotations

from pegazus.modules.base import AnalysisModule
from pegazus.modules.contagious_interview import ContagiousInterviewModule
from pegazus.modules.etherhiding import EtherHidingModule
from pegazus.modules.malware import MalwareModule


def get_enabled_modules() -> list[AnalysisModule]:
    """Modulos de analisis activos para un escaneo.

    Anadir un modulo nuevo (p.ej. inyecciones de codigo genericas) es: crear
    su clase en modules/<nombre>/ implementando AnalysisModule, e incluirla
    aqui. El orquestador no necesita cambios.
    """
    return [
        MalwareModule(),
        EtherHidingModule(),
        ContagiousInterviewModule(),
    ]
