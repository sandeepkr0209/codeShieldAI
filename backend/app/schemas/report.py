"""
Pydantic schemas for Report.
"""
import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict


class ReportRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    scan_id: uuid.UUID
    report_name: str
    report_type: str
    file_path: str | None
    created_at: datetime

    