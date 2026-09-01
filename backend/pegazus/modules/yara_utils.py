from __future__ import annotations

from pathlib import Path

import yara

from pegazus.core.models import Severity
from pegazus.modules.base import ModuleFinding

_SEVERITY_BY_TAG = {
    "critical": Severity.CRITICAL,
    "high": Severity.HIGH,
    "medium": Severity.MEDIUM,
    "low": Severity.LOW,
    "info": Severity.INFO,
}


class YaraScanner:
    """Compila y ejecuta un ruleset YARA de un directorio dado.

    Compartido por cualquier modulo (malware, etherhiding, ...); cada uno
    aporta su propio directorio de reglas y un nombre de modulo para que los
    findings queden etiquetados por dominio (p.ej. "malware.yara" vs
    "etherhiding.yara").
    """

    def __init__(self, rules_dir: Path, module_name: str) -> None:
        self._module_name = module_name
        rule_files = sorted(rules_dir.glob("*.yar"))
        self._rules = (
            yara.compile(filepaths={p.stem: str(p) for p in rule_files}) if rule_files else None
        )

    def scan_bytes(self, data: bytes, file_path: Path) -> list[ModuleFinding]:
        if self._rules is None:
            return []

        findings: list[ModuleFinding] = []
        for match in self._rules.match(data=data):
            severity = next(
                (sev for tag, sev in _SEVERITY_BY_TAG.items() if tag in match.tags),
                Severity.MEDIUM,
            )
            meta = match.meta or {}
            description = meta.get(
                "description", f"El archivo coincide con la regla YARA '{match.rule}'."
            )
            findings.append(
                ModuleFinding(
                    module=self._module_name,
                    title=description,
                    description=description,
                    severity=severity,
                    file_path=str(file_path),
                    evidence=_matched_identifiers(match),
                    rule_id=match.rule,
                )
            )
        return findings


def _matched_identifiers(match: "yara.Match") -> str | None:
    identifiers: set[str] = set()
    for string_match in match.strings:
        identifier = getattr(string_match, "identifier", None)
        if identifier is None and isinstance(string_match, tuple) and len(string_match) >= 2:
            identifier = string_match[1]
        if identifier:
            identifiers.add(identifier)
    return ", ".join(sorted(identifiers)) if identifiers else None
