"""
HTML security report generation.

Builds a single self-contained HTML file (inline CSS, no external
requests) from a scan's real findings/evidence — never manufactures
statistics. PDF is explicitly out of scope for now (per the project's
"HTML must work first" instruction); the file can be printed to PDF
from any browser in the meantime.
"""
import html
from datetime import datetime, timezone
from pathlib import Path

import re

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.finding import Finding
from app.models.project import Project
from app.models.report import Report
from app.models.scan import Scan

REPORTS_DIR = Path(__file__).resolve().parent.parent.parent.parent / "storage" / "reports"

_SEVERITY_ORDER = {"critical": 0, "high": 1, "medium": 2, "low": 3, "informational": 4}
_SEVERITY_COLORS = {
    "critical": "#ef4444", "high": "#f97316", "medium": "#eab308", "low": "#3b82f6", "informational": "#64748b",
}


def _e(value) -> str:
    """HTML-escapes any value for safe inline rendering."""
    return html.escape(str(value)) if value is not None else ""


def generate_html_report(db: Session, scan: Scan, project: Project) -> str:
    stmt = select(Finding).where(Finding.scan_id == scan.id)
    findings = list(db.execute(stmt).scalars().all())
    findings.sort(key=lambda f: _SEVERITY_ORDER.get(f.severity.value, 5))

    severity_counts = {"critical": 0, "high": 0, "medium": 0, "low": 0, "informational": 0}
    for f in findings:
        severity_counts[f.severity.value] = severity_counts.get(f.severity.value, 0) + 1

    confirmed = [f for f in findings if f.verified]
    generated_at = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")

    findings_html = "".join(_render_finding(f) for f in findings) or (
        "<p class='muted'>No verified findings detected.</p>"
    )

    return f"""<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<title>CodeShieldAI Security Report — {_e(project.name)}</title>
<style>
  body {{ font-family: -apple-system, Segoe UI, Roboto, sans-serif; background: #0a0e14; color: #cbd5e1; margin: 0; padding: 40px; line-height: 1.5; }}
  .container {{ max-width: 900px; margin: 0 auto; }}
  h1 {{ color: #f1f5f9; font-size: 24px; margin-bottom: 4px; }}
  h2 {{ color: #f1f5f9; font-size: 16px; margin-top: 36px; border-bottom: 1px solid #1e2635; padding-bottom: 8px; }}
  .subtitle {{ color: #64748b; font-size: 13px; margin-bottom: 24px; }}
  .muted {{ color: #64748b; font-size: 13px; }}
  .meta-grid {{ display: grid; grid-template-columns: repeat(3, 1fr); gap: 12px; margin: 16px 0; }}
  .meta-item {{ background: #0f1420; border: 1px solid #1e2635; border-radius: 8px; padding: 12px; }}
  .meta-item .label {{ font-size: 11px; color: #64748b; text-transform: uppercase; }}
  .meta-item .value {{ font-size: 14px; color: #e2e8f0; margin-top: 4px; }}
  .severity-grid {{ display: flex; gap: 10px; flex-wrap: wrap; margin: 16px 0; }}
  .sev-badge {{ padding: 10px 16px; border-radius: 8px; font-size: 13px; font-weight: 600; color: white; }}
  .finding {{ background: #0f1420; border: 1px solid #1e2635; border-radius: 10px; padding: 20px; margin-bottom: 16px; }}
  .finding-title {{ font-size: 15px; font-weight: 600; color: #f1f5f9; }}
  .badge {{ display: inline-block; padding: 2px 8px; border-radius: 6px; font-size: 11px; font-weight: 600; color: white; margin-right: 6px; }}
  .field {{ margin-top: 10px; font-size: 13px; }}
  .field .k {{ color: #64748b; text-transform: uppercase; font-size: 10px; }}
  code, pre {{ background: #131a29; border: 1px solid #1e2635; border-radius: 6px; padding: 8px; display: block; font-size: 12px; overflow-x: auto; white-space: pre-wrap; }}
  .footer {{ margin-top: 40px; padding-top: 16px; border-top: 1px solid #1e2635; font-size: 12px; color: #64748b; }}
</style>
</head>
<body>
<div class="container">

  <h1>CodeShieldAI Security Report</h1>
  <p class="subtitle">AI-Assisted Application Security Analysis — generated {_e(generated_at)}</p>

  <h2>1. Executive Summary</h2>
  <p>This report covers one security scan of project <strong>{_e(project.name)}</strong>.
  {_e(len(findings))} total finding(s) were produced, of which {_e(len(confirmed))} passed
  deterministic verification (see "Verification" in each finding below) and were marked confirmed;
  the remainder are potential findings that warrant manual review.</p>

  <h2>2. Project Information</h2>
  <div class="meta-grid">
    <div class="meta-item"><div class="label">Name</div><div class="value">{_e(project.name)}</div></div>
    <div class="meta-item"><div class="label">Target type</div><div class="value">{_e(project.target_type.value)}</div></div>
    <div class="meta-item"><div class="label">Target</div><div class="value">{_e(project.target_value)}</div></div>
  </div>

  <h2>3. Scan Configuration</h2>
  <div class="meta-grid">
    <div class="meta-item"><div class="label">Scan type</div><div class="value">{_e(scan.scan_type.value)}</div></div>
    <div class="meta-item"><div class="label">Status</div><div class="value">{_e(scan.status.value)}</div></div>
    <div class="meta-item"><div class="label">Started</div><div class="value">{_e(scan.started_at)}</div></div>
  </div>

  <h2>4. Application Overview</h2>
  <p class="muted">Pages discovered: {_e(scan.pages_discovered)} &middot; Endpoints discovered: {_e(scan.endpoints_discovered)} &middot; Requests made: {_e(scan.requests_made)}</p>

  <h2>5. Attack Surface</h2>
  <p class="muted">See the Application Map in the CodeShieldAI dashboard for the full list of discovered pages and endpoints for this scan.</p>

  <h2>6. Security Statistics</h2>
  <div class="severity-grid">
    {''.join(f'<div class="sev-badge" style="background:{_SEVERITY_COLORS[s]}">{s.upper()}: {c}</div>' for s, c in severity_counts.items() if c)}
  </div>

  <h2>7. Findings Summary</h2>
  <p class="muted">{_e(len(findings))} finding(s) total, sorted by severity.</p>

  <h2>8. Detailed Findings</h2>
  {findings_html}

  <h2>9-12. Source Locations, Evidence, CWE/OWASP Mapping</h2>
  <p class="muted">Included inline within each finding above — see "Location", "CWE/OWASP", and "Evidence" fields.</p>

  <h2>13-14. Impact &amp; Remediation</h2>
  <p class="muted">Included inline within each finding above.</p>

  <h2>15. Limitations</h2>
  <p class="muted">CodeShieldAI is an AI-assisted application security analysis platform, not an autonomous
  penetration-testing system. Static analysis may produce false positives; dynamic checks used here are
  heuristic indicators (especially the IDOR check, deliberately scored at low confidence) requiring human
  verification. Only the vulnerability classes described in the project README are covered. No destructive
  testing was performed.</p>

  <h2>16. Scan Errors / Warnings</h2>
  <p class="muted">{_e(scan.warnings) or 'None recorded.'}</p>
  {f'<p class="muted">Error: {_e(scan.error_message)}</p>' if scan.error_message else ''}

  <div class="footer">Generated by CodeShieldAI — an AI-assisted application security analysis platform. Not a substitute for professional penetration testing.</div>
</div>
</body>
</html>"""


def _render_finding(f: Finding) -> str:
    color = _SEVERITY_COLORS.get(f.severity.value, "#64748b")
    location = ""
    if f.file:
        loc_line = f"{f.file}" + (f":{f.start_line}-{f.end_line}" if f.start_line else "")
        location = f'<div class="field"><div class="k">Location</div>{_e(loc_line)}</div>'
    elif f.endpoint:
        location = f'<div class="field"><div class="k">Location</div>{_e(f.http_method or "GET")} {_e(f.endpoint)}</div>'

    snippet = f'<pre>{_e(f.code_snippet)}</pre>' if f.code_snippet else ""

    return f"""
  <div class="finding">
    <div><span class="badge" style="background:{color}">{_e(f.severity.value.upper())}</span>
         <span class="badge" style="background:#1e2635">{_e(f.status.value)}</span>
         <span class="finding-title">{_e(f.title)}</span></div>
    <div class="field"><div class="k">Category</div>{_e(f.category)}</div>
    {location}
    {snippet}
    <div class="field"><div class="k">CWE / OWASP</div>{_e(f.cwe_id) or 'Not mapped'} / {_e(f.owasp_category) or 'Not mapped'}</div>
    <div class="field"><div class="k">Description</div>{_e(f.description)}</div>
    <div class="field"><div class="k">Impact</div>{_e(f.impact)}</div>
    <div class="field"><div class="k">Remediation</div>{_e(f.recommendation)}</div>
    <div class="field"><div class="k">Verification</div>{'Verified' if f.verified else 'Not verified'} ({_e(f.verification_method)}) — {_e(f.verification_reason)}</div>
    <div class="field"><div class="k">Confidence</div>{_e(round(f.confidence * 100))}%</div>
  </div>"""


def _sanitize_project_name(name: str) -> str:
    """
    Convert the project name into a safe filename component.
    """
    name = name.strip()

    # Remove characters that are invalid in Windows filenames.
    name = re.sub(r'[<>:"/\\|?*]', "", name)

    # Convert spaces to hyphens.
    name = re.sub(r"\s+", "-", name)

    # Remove repeated hyphens.
    name = re.sub(r"-+", "-", name)

    return name.strip("-") or "CodeShieldAI"


def _get_report_type(project: Project) -> str:
    """
    Convert the project target type into the report naming type.

    website -> web
    github  -> source
    zip     -> zip
    """
    return {
        "website": "web",
        "github": "source",
        "zip": "zip",
    }.get(project.target_type.value, "source")


def _get_next_report_name(
    db: Session,
    project: Project,
) -> str:
    """
    Generate a unique report name for this project.

    Examples:
        MyProject-web
        MyProject-web-1
        MyProject-web-2

        MyProject-source
        MyProject-source-1

        MyProject-zip
        MyProject-zip-1
    """
    project_name = _sanitize_project_name(project.name)
    report_type = _get_report_type(project)

    prefix = f"{project_name}-{report_type}"

    stmt = (
        select(Report.report_name)
        .join(Scan, Report.scan_id == Scan.id)
        .where(Scan.project_id == project.id)
    )

    existing_names = {
        name
        for name in db.execute(stmt).scalars().all()
        if name
    }

    # First report for this project/type.
    if prefix not in existing_names:
        return prefix

    # Subsequent reports.
    counter = 1

    while f"{prefix}-{counter}" in existing_names:
        counter += 1

    return f"{prefix}-{counter}"


def save_report(
    db: Session,
    scan: Scan,
    project: Project,
) -> tuple[Path, str]:
    """
    Generate and save an HTML report.

    Returns:
        (file_path, report_name)
    """
    REPORTS_DIR.mkdir(
        parents=True,
        exist_ok=True,
    )

    html_content = generate_html_report(
        db,
        scan,
        project,
    )

    report_name = _get_next_report_name(
        db,
        project,
    )

    file_path = REPORTS_DIR / f"{report_name}.html"

    file_path.write_text(
        html_content,
        encoding="utf-8",
    )

    return file_path, report_name
