from __future__ import annotations

from pathlib import Path

from fastapi import APIRouter, BackgroundTasks, HTTPException, Query
from sqlalchemy import select

from pegazus.api.schemas import FindingOut, ScanCreateRequest, ScanSummary
from pegazus.core.db import SessionLocal
from pegazus.core.models import Finding, Scan, ScanStatus, Severity
from pegazus.core.orchestrator import run_scan

router = APIRouter(prefix="/api/scans", tags=["scans"])


def _scan_to_summary(scan: Scan) -> ScanSummary:
    return ScanSummary(
        id=scan.id,
        target_path=scan.target_path,
        status=scan.status.value,
        files_scanned=scan.files_scanned,
        files_total=scan.files_total,
        started_at=scan.started_at,
        finished_at=scan.finished_at,
        error_message=scan.error_message,
        severity_counts=scan.severity_counts(),
    )


def _run_scan_job(scan_id: int) -> None:
    session = SessionLocal()
    try:
        run_scan(session, scan_id)
    finally:
        session.close()


@router.post("", response_model=ScanSummary, status_code=201)
def create_scan(payload: ScanCreateRequest, background_tasks: BackgroundTasks) -> ScanSummary:
    target = Path(payload.path)
    if not target.exists():
        raise HTTPException(status_code=400, detail=f"La ruta '{payload.path}' no existe.")
    if not target.is_dir():
        raise HTTPException(status_code=400, detail=f"La ruta '{payload.path}' no es un directorio.")

    session = SessionLocal()
    try:
        scan = Scan(target_path=str(target), status=ScanStatus.PENDING)
        session.add(scan)
        session.commit()
        session.refresh(scan)
        scan_id = scan.id
        summary = _scan_to_summary(scan)
    finally:
        session.close()

    background_tasks.add_task(_run_scan_job, scan_id)
    return summary


@router.get("", response_model=list[ScanSummary])
def list_scans() -> list[ScanSummary]:
    session = SessionLocal()
    try:
        scans = session.execute(select(Scan).order_by(Scan.started_at.desc())).scalars().all()
        return [_scan_to_summary(scan) for scan in scans]
    finally:
        session.close()


@router.get("/{scan_id}", response_model=ScanSummary)
def get_scan(scan_id: int) -> ScanSummary:
    session = SessionLocal()
    try:
        scan = session.get(Scan, scan_id)
        if scan is None:
            raise HTTPException(status_code=404, detail="Escaneo no encontrado.")
        return _scan_to_summary(scan)
    finally:
        session.close()


@router.get("/{scan_id}/findings", response_model=list[FindingOut])
def get_scan_findings(
    scan_id: int,
    severity: str | None = Query(default=None),
    module: str | None = Query(default=None),
    limit: int = Query(default=200, le=1000),
    offset: int = Query(default=0, ge=0),
) -> list[FindingOut]:
    session = SessionLocal()
    try:
        scan = session.get(Scan, scan_id)
        if scan is None:
            raise HTTPException(status_code=404, detail="Escaneo no encontrado.")

        stmt = select(Finding).where(Finding.scan_id == scan_id)
        if severity:
            try:
                stmt = stmt.where(Finding.severity == Severity(severity))
            except ValueError:
                raise HTTPException(status_code=400, detail=f"Severidad invalida: '{severity}'.")
        if module:
            stmt = stmt.where(Finding.module == module)
        stmt = stmt.order_by(Finding.id).offset(offset).limit(limit)

        findings = session.execute(stmt).scalars().all()
        return [FindingOut.model_validate(f) for f in findings]
    finally:
        session.close()
