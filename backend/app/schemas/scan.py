"""
Pydantic schemas for Scan.
"""
import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict

from app.models.scan import ScanStatus, ScanType


class ScanCreate(BaseModel):
    scan_type: ScanType
    auth_cookies: dict[str, str] | None = None
    auth_headers: dict[str, str] | None = None


class ScanRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    project_id: uuid.UUID
    status: ScanStatus
    scan_type: ScanType
    current_stage: str | None = None
    error_message: str | None = None
    warnings: str | None = None
    pages_discovered: int = 0
    endpoints_discovered: int = 0
    requests_made: int = 0
    started_at: datetime | None
    completed_at: datetime | None
    created_at: datetime
    finding_count: int = 0
