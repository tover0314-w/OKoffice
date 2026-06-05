from __future__ import annotations

import json
from pathlib import Path
from typing import Any
from urllib.parse import urlparse
from uuid import uuid4

from okoffice.artifacts.store import build_artifact
from okoffice.schemas.errors import OKofficeException
from okoffice.schemas.models import ToolResult, ValidationCheck, ValidationReport
from okoffice.security.paths import resolve_input_path
from okoffice.validation.pdf import blank_page_check_pdf, render_check_pdf, validate_pdf


TOOL_NAME = "pdf.qa.visual_report"
SUPPORTED_HTML_PACKAGE_CONTRACTS = {"authoring-html-package-v0", "html-package-v0"}


def run_visual_qa(
    *,
    input_path: str | Path,
    expected_page_count: int | None = None,
    html_package_manifest_path: str | Path | None = None,
    pages: str = "all",
) -> ToolResult:
    return visual_report(
        input_path=input_path,
        expected_page_count=expected_page_count,
        html_package_manifest_path=html_package_manifest_path,
        pages=pages,
    )


def visual_report(
    *,
    input_path: str | Path,
    expected_page_count: int | None = None,
    html_package_manifest_path: str | Path | None = None,
    pages: str = "all",
) -> ToolResult:
    try:
        if expected_page_count is not None and expected_page_count < 1:
            raise OKofficeException(
                "unsafe_input_rejected",
                "Expected page count must be at least 1.",
                details={"payload": "expected_page_count"},
            )
        pdf_path = resolve_input_path(input_path)
        page_report = validate_pdf(pdf_path, expected_pages=expected_page_count)
        render_report, render_usage = render_check_pdf(pdf_path, pages=pages)
        blank_report, blank_usage = blank_page_check_pdf(pdf_path, pages=pages)
        manifest_check, manifest_payload = _manifest_check(html_package_manifest_path)
        validation = _combined_validation(
            page_report,
            render_report,
            blank_report,
            manifest_check,
        )
        checks = _usage_checks(page_report, render_report, blank_report, manifest_check)
        issues = _issues(validation)
        usage = {
            "visual_qa": {
                "qa_id": f"qa_{uuid4().hex[:12]}",
                "input_pdf": str(pdf_path),
                "expected_page_count": expected_page_count,
                "checks": checks,
                "issues": issues,
                "render_usage": render_usage,
                "blank_page_usage": blank_usage,
                "html_package_manifest": manifest_payload,
                "next_actions": ["pdf.artifacts.export_bundle", "pdf.workflow.report"],
            }
        }
        return ToolResult(
            job_id=_job_id(),
            status="failed" if validation.status == "failed" else "succeeded",
            tool=TOOL_NAME,
            artifacts=[build_artifact(pdf_path, source_tool=TOOL_NAME)],
            validation=validation,
            warnings=[*page_report.warnings, *render_report.warnings, *blank_report.warnings],
            usage=usage,
            next_recommended_tools=["pdf.artifacts.export_bundle", "pdf.workflow.report"],
        )
    except OKofficeException as exc:
        return ToolResult(
            job_id=_job_id(),
            status="failed",
            tool=TOOL_NAME,
            warnings=[exc.message],
            error=exc.to_error(),
        )


def _manifest_check(path: str | Path | None) -> tuple[ValidationCheck, dict[str, Any] | None]:
    if path is None:
        return (
            ValidationCheck(
                name="html_package_manifest",
                status="skipped",
                message="No HTML package manifest supplied.",
            ),
            None,
        )

    manifest_path = resolve_input_path(path)
    try:
        payload = json.loads(manifest_path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        return (
            ValidationCheck(
                name="html_package_manifest",
                status="failed",
                details={"manifest_path": str(manifest_path)},
                message=f"Manifest is not valid JSON: {exc}",
            ),
            None,
        )

    if not isinstance(payload, dict):
        return (
            ValidationCheck(
                name="html_package_manifest",
                status="failed",
                details={"manifest_path": str(manifest_path)},
                message="Manifest must be a JSON object.",
            ),
            None,
        )

    failures = _manifest_failures(payload)
    status = "failed" if failures else "passed"
    return (
        ValidationCheck(
            name="html_package_manifest",
            status=status,
            details={
                "manifest_path": str(manifest_path),
                "renderer_contract": payload.get("renderer_contract"),
                "javascript_enabled": payload.get("javascript_enabled"),
                "remote_assets_enabled": payload.get("remote_assets_enabled"),
            },
            message="; ".join(failures) if failures else None,
        ),
        payload,
    )


def _manifest_failures(payload: dict[str, Any]) -> list[str]:
    failures: list[str] = []
    if payload.get("renderer_contract") not in SUPPORTED_HTML_PACKAGE_CONTRACTS:
        allowed = ", ".join(sorted(SUPPORTED_HTML_PACKAGE_CONTRACTS))
        failures.append(f"Manifest renderer contract must be one of: {allowed}.")
    if payload.get("javascript_enabled") is not False:
        failures.append("Manifest must disable JavaScript.")
    if payload.get("remote_assets_enabled") is not False:
        failures.append("Manifest must disable remote assets.")
    html_path = str(payload.get("html_path") or "")
    if not html_path or _is_remote_ref(html_path):
        failures.append("Manifest html_path must be a local file.")
    elif not Path(html_path).expanduser().resolve().is_file():
        failures.append("Manifest html_path does not exist.")
    return failures


def _combined_validation(*reports_or_checks: ValidationReport | ValidationCheck) -> ValidationReport:
    checks: list[ValidationCheck] = []
    warnings: list[str] = []
    page_count: int | None = None
    for item in reports_or_checks:
        if isinstance(item, ValidationReport):
            checks.extend(item.checks)
            warnings.extend(item.warnings)
            page_count = item.page_count if item.page_count is not None else page_count
        else:
            checks.append(item)
    if any(check.status == "failed" for check in checks):
        status = "failed"
    elif any(check.status == "warning" for check in checks):
        status = "warning"
    elif checks and all(check.status == "skipped" for check in checks):
        status = "skipped"
    else:
        status = "passed"
    return ValidationReport(status=status, checks=checks, page_count=page_count, warnings=warnings)


def _usage_checks(
    page_report: ValidationReport,
    render_report: ValidationReport,
    blank_report: ValidationReport,
    manifest_check: ValidationCheck,
) -> dict[str, str]:
    page_count = "passed" if _check_status(page_report, "expected_page_count") == "passed" else page_report.status
    return {
        "page_count": page_count,
        "render_check": render_report.status,
        "blank_page_check": blank_report.status,
        "html_package_manifest": manifest_check.status,
    }


def _check_status(report: ValidationReport, name: str) -> str | None:
    for check in report.checks:
        if check.name == name:
            return check.status
    return None


def _issues(report: ValidationReport) -> list[dict[str, Any]]:
    return [
        {
            "check": check.name,
            "status": check.status,
            "message": check.message,
            "details": check.details,
        }
        for check in report.checks
        if check.status in {"failed", "warning"}
    ]


def _is_remote_ref(value: str) -> bool:
    parsed = urlparse(value)
    return parsed.scheme in {"http", "https", "ftp", "file", "data", "javascript"}


def _job_id() -> str:
    return f"job_{uuid4().hex[:16]}"
