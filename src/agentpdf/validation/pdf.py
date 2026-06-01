from __future__ import annotations

from pathlib import Path

from pypdf import PdfReader

from agentpdf.schemas.models import ValidationCheck, ValidationReport


def validate_pdf(path: str | Path, expected_pages: int | None = None) -> ValidationReport:
    checks: list[ValidationCheck] = []
    resolved = Path(path)
    if not resolved.exists():
        return ValidationReport(
            status="failed",
            checks=[
                ValidationCheck(
                    name="file_exists",
                    status="failed",
                    message=f"Output file does not exist: {resolved}",
                )
            ],
        )

    try:
        reader = PdfReader(resolved)
        page_count = len(reader.pages)
        checks.append(
            ValidationCheck(
                name="parseable_pdf",
                status="passed",
                details={"path": str(resolved)},
            )
        )
    except Exception as exc:
        return ValidationReport(
            status="failed",
            checks=[
                ValidationCheck(
                    name="parseable_pdf",
                    status="failed",
                    message=str(exc),
                )
            ],
        )

    checks.append(
        ValidationCheck(
            name="page_count_nonzero",
            status="passed" if page_count > 0 else "failed",
            details={"page_count": page_count},
        )
    )
    if expected_pages is not None:
        checks.append(
            ValidationCheck(
                name="expected_page_count",
                status="passed" if page_count == expected_pages else "failed",
                details={"expected": expected_pages, "actual": page_count},
            )
        )

    status = "passed" if all(check.status == "passed" for check in checks) else "failed"
    return ValidationReport(status=status, checks=checks, page_count=page_count)
