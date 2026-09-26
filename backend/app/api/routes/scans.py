"""
Scan API routes. All require authentication; access is scoped through
the owning project (a scan has no owner of its own — it belongs to a
project, which belongs to a user).
"""
import uuid
from pathlib import Path

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.db.session import get_db
from app.models.endpoint import Endpoint
from app.models.observation import Observation
from app.models.scan import ScanStatus, ScanType
from app.models.source_file import SourceFile
from app.models.user import User
from app.models.web_page import WebPage
from app.schemas.finding import FindingRead
from app.schemas.observation import ObservationRead
from app.schemas.scan import ScanCreate, ScanRead
from app.schemas.source_file import SourceFileRead
from app.schemas.web_analysis import EndpointRead, WebPageRead
from app.services.findings.service import list_findings_for_scan
from app.services.projects import service as project_service
from app.services.scans import service as scan_service
from app.services.scans.pipeline import run_source_scan
from app.services.scans.web_pipeline import run_web_scan

router = APIRouter(tags=["scans"])


def _get_owned_scan_or_404(db: Session, scan_id: uuid.UUID, user: User):
    scan = scan_service.get_scan(db, scan_id)
    if scan is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Scan not found")
    if project_service.get_project(db, scan.project_id, user_id=user.id) is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Scan not found")
    return scan


@router.post(
    "/projects/{project_id}/scans",
    response_model=ScanRead,
    status_code=status.HTTP_201_CREATED,
)
def create_scan(
    project_id: uuid.UUID,
    payload: ScanCreate,
    background_tasks: BackgroundTasks,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> ScanRead:
    project = project_service.get_project(db, project_id, user_id=current_user.id)
    if project is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Project not found")

    scan = scan_service.create_scan(db, project_id=project_id, scan_type=payload.scan_type)

    if payload.scan_type == ScanType.SOURCE_CODE:
        background_tasks.add_task(run_source_scan, scan.id)
    elif payload.scan_type == ScanType.WEB_APPLICATION:
        background_tasks.add_task(run_web_scan, scan.id)

    return ScanRead(**ScanRead.model_validate(scan).model_dump(exclude={"finding_count"}), finding_count=0)


@router.get("/projects/{project_id}/scans", response_model=list[ScanRead])
def list_scans(
    project_id: uuid.UUID, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)
) -> list[ScanRead]:
    project = project_service.get_project(db, project_id, user_id=current_user.id)
    if project is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Project not found")

    scans = scan_service.list_scans_for_project(db, project_id)
    return [
        ScanRead(
            **ScanRead.model_validate(scan).model_dump(exclude={"finding_count"}),
            finding_count=scan_service.scan_finding_count(db, scan.id),
        )
        for scan in scans
    ]


@router.get("/scans/{scan_id}", response_model=ScanRead)
def get_scan(
    scan_id: uuid.UUID, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)
) -> ScanRead:
    scan = _get_owned_scan_or_404(db, scan_id, current_user)
    return ScanRead(
        **ScanRead.model_validate(scan).model_dump(exclude={"finding_count"}),
        finding_count=scan_service.scan_finding_count(db, scan.id),
    )

@router.delete(
    "/scans/{scan_id}",
    status_code=status.HTTP_204_NO_CONTENT,
)
def delete_scan(
    scan_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> None:
    scan = _get_owned_scan_or_404(
        db,
        scan_id,
        current_user,
    )

    if scan.status in {
        ScanStatus.PENDING,
        ScanStatus.RUNNING,
    }:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cannot delete a scan while it is pending or running",
        )

    # Delete generated report files from disk.
    for report in scan.reports:
        if report.file_path:
            report_path = Path(report.file_path)

            if report_path.exists():
                report_path.unlink()

    # SQLAlchemy cascade deletes related scan data.
    db.delete(scan)
    db.commit()
    
@router.get("/scans/{scan_id}/findings", response_model=list[FindingRead])
def get_scan_findings(
    scan_id: uuid.UUID, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)
) -> list[FindingRead]:
    _get_owned_scan_or_404(db, scan_id, current_user)
    findings = list_findings_for_scan(db, scan_id)
    return [FindingRead.model_validate(f) for f in findings]


@router.get("/scans/{scan_id}/observations", response_model=list[ObservationRead])
def get_scan_observations(
    scan_id: uuid.UUID, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)
) -> list[ObservationRead]:
    _get_owned_scan_or_404(db, scan_id, current_user)
    stmt = select(Observation).where(Observation.scan_id == scan_id).order_by(Observation.created_at)
    observations = list(db.execute(stmt).scalars().all())
    return [ObservationRead.model_validate(o) for o in observations]


@router.get("/scans/{scan_id}/source-files", response_model=list[SourceFileRead])
def get_scan_source_files(
    scan_id: uuid.UUID, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)
) -> list[SourceFileRead]:
    _get_owned_scan_or_404(db, scan_id, current_user)
    stmt = select(SourceFile).where(SourceFile.scan_id == scan_id).order_by(SourceFile.path)
    files = list(db.execute(stmt).scalars().all())
    return [SourceFileRead.model_validate(f) for f in files]


@router.get("/scans/{scan_id}/pages", response_model=list[WebPageRead])
def get_scan_pages(
    scan_id: uuid.UUID, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)
) -> list[WebPageRead]:
    """Discovered pages — the 'application map' pages list."""
    _get_owned_scan_or_404(db, scan_id, current_user)
    stmt = select(WebPage).where(WebPage.scan_id == scan_id).order_by(WebPage.url)
    pages = list(db.execute(stmt).scalars().all())
    return [WebPageRead.model_validate(p) for p in pages]


@router.get("/scans/{scan_id}/endpoints", response_model=list[EndpointRead])
def get_scan_endpoints(
    scan_id: uuid.UUID, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)
) -> list[EndpointRead]:
    """Discovered endpoints/routes — the 'application map' endpoints list."""
    _get_owned_scan_or_404(db, scan_id, current_user)
    stmt = select(Endpoint).where(Endpoint.scan_id == scan_id).order_by(Endpoint.url)
    endpoints = list(db.execute(stmt).scalars().all())
    return [EndpointRead.model_validate(e) for e in endpoints]
