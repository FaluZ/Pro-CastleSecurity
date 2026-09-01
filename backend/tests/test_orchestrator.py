from __future__ import annotations

from pathlib import Path

from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

from pegazus.core.db import Base
from pegazus.core.models import Scan, ScanStatus
from pegazus.core.orchestrator import run_scan


def _make_session() -> Session:
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(bind=engine)
    return sessionmaker(bind=engine)()


def test_run_scan_finds_eicar(tmp_path: Path, fixtures_dir: Path) -> None:
    target = tmp_path / "project"
    target.mkdir()
    (target / "sample.txt").write_bytes((fixtures_dir / "eicar_test.txt").read_bytes())
    (target / "clean.txt").write_text("nada sospechoso aqui", encoding="utf-8")

    session = _make_session()
    scan = Scan(target_path=str(target), status=ScanStatus.PENDING)
    session.add(scan)
    session.commit()
    session.refresh(scan)

    run_scan(session, scan.id)
    session.refresh(scan)

    assert scan.status == ScanStatus.COMPLETED
    assert scan.files_scanned == 2
    assert any(f.rule_id == "Eicar_Test_File" for f in scan.findings)


def test_run_scan_missing_path_marks_failed(tmp_path: Path) -> None:
    missing = tmp_path / "does-not-exist"

    session = _make_session()
    scan = Scan(target_path=str(missing), status=ScanStatus.PENDING)
    session.add(scan)
    session.commit()
    session.refresh(scan)

    run_scan(session, scan.id)
    session.refresh(scan)

    assert scan.status == ScanStatus.FAILED
    assert scan.error_message is not None
