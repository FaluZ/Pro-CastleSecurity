from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, ConfigDict


class ScanCreateRequest(BaseModel):
    path: str


class ScanSummary(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    target_path: str
    status: str
    files_scanned: int
    files_total: int
    started_at: datetime
    finished_at: datetime | None
    error_message: str | None
    severity_counts: dict[str, int]


class FindingOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    module: str
    severity: str
    title: str
    description: str
    file_path: str
    line: int | None
    evidence: str | None
    rule_id: str | None
    created_at: datetime
