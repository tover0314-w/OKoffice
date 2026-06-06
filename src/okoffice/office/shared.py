from __future__ import annotations

from uuid import uuid4

from okoffice.schemas.models import OKofficeError, ToolResult, ValidationCheck


def job_id() -> str:
    return f"job_{uuid4().hex[:16]}"


def failed_result(tool: str, error: OKofficeError) -> ToolResult:
    return ToolResult(
        job_id=job_id(),
        status="failed",
        tool=tool,
        error=error,
        warnings=[error.message],
    )


def dedupe_strings(values: list[str]) -> list[str]:
    result: list[str] = []
    for value in values:
        if value and value not in result:
            result.append(value)
    return result


def validation_report_status(checks: list[ValidationCheck]) -> str:
    statuses = [check.status for check in checks]
    if "failed" in statuses:
        return "failed"
    if "warning" in statuses:
        return "warning"
    return "passed"
