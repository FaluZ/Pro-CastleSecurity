from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path

from sqlalchemy.orm import Session

from pegazus.core.models import Finding, Scan, ScanStatus, Severity
from pegazus.core.walker import walk_project
from pegazus.modules.base import ModuleFinding, ScanContext
from pegazus.modules.registry import get_enabled_modules

# Cada cuantos archivos se persiste el progreso (evita un commit por archivo en escaneos grandes).
PROGRESS_COMMIT_INTERVAL = 25


def run_scan(session: Session, scan_id: int) -> None:
    """Ejecuta todos los modulos habilitados sobre un Scan ya creado en la DB."""
    scan = session.get(Scan, scan_id)
    if scan is None:
        return

    scan.status = ScanStatus.RUNNING
    session.commit()

    project_root = Path(scan.target_path)
    modules = get_enabled_modules()
    context = ScanContext(project_root=project_root, scan_id=scan_id)

    try:
        if not project_root.exists():
            raise FileNotFoundError(f"La ruta '{project_root}' no existe.")
        if not project_root.is_dir():
            raise NotADirectoryError(f"La ruta '{project_root}' no es un directorio.")

        walk_result = walk_project(project_root)
        scan.files_total = len(walk_result.files)
        session.commit()

        for module in modules:
            for module_finding in module.scan_project(context):
                session.add(_to_db_finding(scan_id, module.name, module_finding))

        for file_path in walk_result.files:
            for module in modules:
                for module_finding in module.scan_file(file_path, context):
                    session.add(_to_db_finding(scan_id, module.name, module_finding))
            scan.files_scanned += 1

            if scan.files_scanned % PROGRESS_COMMIT_INTERVAL == 0:
                session.commit()

        for skipped in walk_result.skipped_large:
            session.add(
                Finding(
                    scan_id=scan_id,
                    module="core.walker",
                    severity=Severity.INFO,
                    title="Archivo omitido por tamano",
                    description=(
                        f"'{skipped}' supera el limite de tamano configurado y no fue analizado."
                    ),
                    file_path=str(skipped),
                )
            )

        scan.status = ScanStatus.COMPLETED
    except Exception as exc:  # noqa: BLE001 - un fallo del escaneo se registra, no se propaga
        scan.status = ScanStatus.FAILED
        scan.error_message = str(exc)
    finally:
        scan.finished_at = datetime.now(timezone.utc)
        session.commit()


def _to_db_finding(scan_id: int, module_name: str, module_finding: ModuleFinding) -> Finding:
    return Finding(
        scan_id=scan_id,
        module=module_finding.module or module_name,
        severity=module_finding.severity,
        title=module_finding.title,
        description=module_finding.description,
        file_path=module_finding.file_path,
        line=module_finding.line,
        evidence=module_finding.evidence,
        rule_id=module_finding.rule_id,
    )
