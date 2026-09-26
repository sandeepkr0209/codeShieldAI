"""
Report API routes. Ownership checked through scan -> project -> user.

Generation produces a self-contained HTML file (see
services/reporting/report_generator.py) built from the scan's real
findings — PDF export is not yet implemented (HTML first, per spec).
"""

import uuid
from pathlib import Path

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import FileResponse
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.db.session import get_db
from app.models.report import Report
from app.models.user import User
from app.schemas.report import ReportRead
from app.services.projects import service as project_service
from app.services.reporting.report_generator import save_report
from app.services.scans import service as scan_service


router = APIRouter(tags=["reports"])


def _get_owned_scan_and_project(
    db: Session,
    scan_id: uuid.UUID,
    user: User,
):
    scan = scan_service.get_scan(db, scan_id)

    if scan is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Scan not found",
        )

    project = project_service.get_project(
        db,
        scan.project_id,
        user_id=user.id,
    )

    if project is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Scan not found",
        )

    return scan, project


@router.post(
    "/scans/{scan_id}/reports",
    response_model=ReportRead,
    status_code=status.HTTP_201_CREATED,
)
def generate_report(
    scan_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> ReportRead:
    scan, project = _get_owned_scan_and_project(
        db,
        scan_id,
        current_user,
    )

    if scan.status.value != "completed":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Reports can only be generated for a completed scan",
        )

    file_path, report_name = save_report(
        db,
        scan,
        project,
    )

    report = Report(
        scan_id=scan.id,
        report_name=report_name,
        report_type="html",
        file_path=str(file_path),
    )

    db.add(report)
    db.commit()
    db.refresh(report)

    return ReportRead.model_validate(report)


@router.get(
    "/reports/scan/{scan_id}",
    response_model=list[ReportRead],
)
def list_reports_for_scan(
    scan_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> list[ReportRead]:
    _get_owned_scan_and_project(
        db,
        scan_id,
        current_user,
    )

    stmt = (
        select(Report)
        .where(Report.scan_id == scan_id)
        .order_by(Report.created_at.desc())
    )

    reports = list(
        db.execute(stmt).scalars().all()
    )

    return [
        ReportRead.model_validate(report)
        for report in reports
    ]


@router.get(
    "/reports/{report_id}",
    response_model=ReportRead,
)
def get_report(
    report_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> ReportRead:
    report = db.get(
        Report,
        report_id,
    )

    if report is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Report not found",
        )

    _get_owned_scan_and_project(
        db,
        report.scan_id,
        current_user,
    )

    return ReportRead.model_validate(report)

# download route
@router.get(
    "/reports/{report_id}/download"
)
def download_report(
    report_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> FileResponse:
    report = db.get(
        Report,
        report_id,
    )

    if report is None or not report.file_path:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Report not found",
        )

    _get_owned_scan_and_project(
        db,
        report.scan_id,
        current_user,
    )

    return FileResponse(
        report.file_path,
        media_type="text/html",
        filename=f"{report.report_name}.html",
    )

# deletion route

@router.delete(
    "/reports/{report_id}",
    status_code=status.HTTP_204_NO_CONTENT,
)
def delete_report(
    report_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> None:
    report = db.get(
        Report,
        report_id,
    )

    if report is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Report not found",
        )

    _get_owned_scan_and_project(
        db,
        report.scan_id,
        current_user,
    )

    # Delete generated HTML file from disk.
    if report.file_path:
        report_path = Path(report.file_path)

        if report_path.exists():
            report_path.unlink()

    # Delete report database record.
    db.delete(report)
    db.commit()