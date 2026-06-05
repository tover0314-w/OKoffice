from __future__ import annotations

from collections.abc import Mapping
from copy import deepcopy
from typing import Any
from uuid import uuid4

from pydantic import ValidationError

from okoffice.authoring.models import DesignTokens, PageDocument
from okoffice.schemas.errors import OKofficeException
from okoffice.schemas.models import OKofficeError, ToolResult, ValidationCheck, ValidationReport


EDITABLE_PAGE_FIELDS = {"title", "subtitle", "blocks", "source_footer", "evidence_refs", "layout"}


def revise_pages(
    *,
    page_document: PageDocument | Mapping[str, object],
    revisions: list[Mapping[str, object]] | None = None,
    design_tokens: DesignTokens | Mapping[str, object] | None = None,
) -> ToolResult:
    try:
        document = (
            page_document
            if isinstance(page_document, PageDocument)
            else PageDocument.model_validate(page_document)
        )
        revised = document.model_dump(mode="json")
        changed_pages = _apply_revisions(revised, revisions or [])
        if design_tokens is not None:
            revised["design_tokens"] = (
                design_tokens.model_dump(mode="json")
                if isinstance(design_tokens, DesignTokens)
                else DesignTokens.model_validate(design_tokens).model_dump(mode="json")
            )
        revised_document = PageDocument.model_validate(revised)
    except OKofficeException as exc:
        return ToolResult(
            job_id=_job_id(),
            status="failed",
            tool="pdf.pages.revise",
            warnings=[exc.message],
            error=exc.to_error(),
        )
    except ValidationError as exc:
        return _failed("Page revision payload is invalid or unsafe.", validation_error=exc)

    revision_report = {
        "revision_id": f"pagerev_{uuid4().hex[:12]}",
        "changed_pages": changed_pages,
        "preserves_source_refs_by_default": True,
        "mutates_input": False,
    }
    return ToolResult(
        job_id=_job_id(),
        status="succeeded",
        tool="pdf.pages.revise",
        validation=ValidationReport(
            status="passed",
            checks=[
                ValidationCheck(
                    name="page_revision_valid",
                    status="passed",
                    details={"changed_pages": changed_pages, "page_count": revised_document.page_count},
                ),
                ValidationCheck(
                    name="page_count_preserved",
                    status="passed",
                    details={"page_count": revised_document.page_count},
                ),
            ],
            page_count=revised_document.page_count,
        ),
        usage={
            "page_document": revised_document.model_dump(mode="json"),
            "revision_report": revision_report,
        },
        next_recommended_tools=["pdf.create.html_package", "pdf.qa.visual_report"],
    )


def _apply_revisions(page_document: dict[str, Any], revisions: list[Mapping[str, object]]) -> list[int]:
    pages = page_document.get("pages")
    if not isinstance(pages, list):
        raise OKofficeException("authoring_invalid_page_document", "Page document must include a pages array.")
    page_index = {int(page.get("page_number")): page for page in pages if isinstance(page, dict)}
    changed_pages: list[int] = []
    for raw_revision in revisions:
        if not isinstance(raw_revision, Mapping):
            raise OKofficeException("unsafe_input_rejected", "Each page revision must be an object.")
        page_number = _page_number(raw_revision)
        target = page_index.get(page_number)
        if target is None:
            raise OKofficeException(
                "invalid_page_range",
                f"Revision page_number is outside the page document: {page_number}",
                details={"page_number": page_number, "page_count": len(pages)},
            )
        before = deepcopy(target)
        for field in EDITABLE_PAGE_FIELDS:
            if field in raw_revision:
                target[field] = deepcopy(raw_revision[field])
        if target != before and page_number not in changed_pages:
            changed_pages.append(page_number)
    return sorted(changed_pages)


def _page_number(raw_revision: Mapping[str, object]) -> int:
    value = raw_revision.get("page_number")
    try:
        page_number = int(value)  # type: ignore[arg-type]
    except (TypeError, ValueError) as exc:
        raise OKofficeException(
            "unsafe_input_rejected",
            "Each page revision must include an integer page_number.",
        ) from exc
    if page_number < 1:
        raise OKofficeException("invalid_page_range", "Revision page_number must be at least 1.")
    return page_number


def _failed(message: str, *, validation_error: ValidationError) -> ToolResult:
    error = OKofficeError(
        code="authoring_invalid_page_document",
        message=message,
        retry_hint="Provide a valid PageDocument and page-numbered revisions.",
        details={"payload": "page_document", "validation_errors": validation_error.errors(include_context=False)},
    )
    return ToolResult(
        job_id=_job_id(),
        status="failed",
        tool="pdf.pages.revise",
        warnings=[message],
        error=error,
    )


def _job_id() -> str:
    return f"job_{uuid4().hex[:16]}"
