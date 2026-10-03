"""
Scan model.

A Scan represents one analysis run against a Project's target.
`current_stage` drives the frontend progress stepper — separate stage
sets exist for source-code scans vs. web-application scans (see
ScanStage). Live counters (pages_discovered etc.) let the UI show
real progress metrics instead of a bare spinner.
"""
import enum
import uuid
from datetime import datetime

from sqlalchemy import DateTime, Enum, ForeignKey, Integer, String, Uuid, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.database import Base


class ScanStatus(str, enum.Enum):
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"


class ScanType(str, enum.Enum):
    SOURCE_CODE = "source_code"
    WEB_APPLICATION = "web_application"


class ScanStage(str, enum.Enum):
    """Granular progress within a running scan."""

    QUEUED = "queued"
    # source-code stages
    EXTRACTING = "extracting"
    PARSING = "parsing"
    STATIC_ANALYSIS = "static_analysis"
    AI_ANALYSIS = "ai_analysis"
    # web-application stages
    SCOPE_VALIDATION = "scope_validation"
    RECONNAISSANCE = "reconnaissance"
    APPLICATION_MAPPING = "application_mapping"
    SECURITY_TESTING = "security_testing"
    EVIDENCE_COLLECTION = "evidence_collection"
    VERIFICATION = "verification"
    # shared terminal stages
    COMPLETED = "completed"
    FAILED = "failed"


class Scan(Base):
    __tablename__ = "scans"

    id: Mapped[uuid.UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4)
    project_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("projects.id", ondelete="CASCADE"), nullable=False
    )

    status: Mapped[ScanStatus] = mapped_column(
        Enum(ScanStatus, name="scan_status", values_callable=lambda obj: [e.value for e in obj]),
        nullable=False,
        default=ScanStatus.PENDING,
    )
    scan_type: Mapped[ScanType] = mapped_column(
        Enum(ScanType, name="scan_type", values_callable=lambda obj: [e.value for e in obj]),
        nullable=False,
    )
    current_stage: Mapped[str | None] = mapped_column(String(50), nullable=True)
    error_message: Mapped[str | None] = mapped_column(String(2048), nullable=True)
    # Pipe-separated list of non-fatal tool/analyzer warnings (e.g. "bandit:
    # not installed, skipped"). A completed scan with warnings means
    # "completed with limited analysis", never silently reported as clean.
    warnings: Mapped[str | None] = mapped_column(String(2048), nullable=True)
    auth_config_json: Mapped[str | None] = mapped_column(String, nullable=True)

    # --- Live progress counters (web-application scans) ---
    pages_discovered: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    endpoints_discovered: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    requests_made: Mapped[int] = mapped_column(Integer, nullable=False, default=0)

    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    project: Mapped["Project"] = relationship("Project", back_populates="scans")
    findings: Mapped[list["Finding"]] = relationship(
        "Finding", back_populates="scan", cascade="all, delete-orphan"
    )
    reports: Mapped[list["Report"]] = relationship(
        "Report", back_populates="scan", cascade="all, delete-orphan"
    )
    source_files: Mapped[list["SourceFile"]] = relationship(
        "SourceFile", back_populates="scan", cascade="all, delete-orphan"
    )
    observations: Mapped[list["Observation"]] = relationship(
        "Observation", back_populates="scan", cascade="all, delete-orphan"
    )
    web_pages: Mapped[list["WebPage"]] = relationship(
        "WebPage", back_populates="scan", cascade="all, delete-orphan"
    )
    endpoints: Mapped[list["Endpoint"]] = relationship(
        "Endpoint", back_populates="scan", cascade="all, delete-orphan"
    )
