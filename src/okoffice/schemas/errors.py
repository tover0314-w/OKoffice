from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from okoffice.schemas.models import OKofficeError


KNOWN_ERROR_CODES = {
    "file_not_found",
    "unsupported_file_type",
    "encrypted_pdf_requires_password",
    "invalid_password",
    "invalid_page_range",
    "pdf_parse_failed",
    "pdf_render_failed",
    "output_validation_failed",
    "html_asset_missing",
    "html_invalid_package",
    "html_render_failed",
    "authoring_invalid_brief",
    "authoring_invalid_storyboard",
    "authoring_invalid_page_document",
    "html_package_invalid_manifest",
    "visual_qa_failed",
    "dependency_missing",
    "tool_not_implemented",
    "unsafe_input_rejected",
    "path_traversal_rejected",
    "overwrite_not_allowed",
    "quota_required_for_cloud_feature",
    "cloud_feature_disabled",
    "source_ref_not_found",
    "invalid_artifact_graph",
    "html_layer_ref_not_found",
    "layer_operation_not_allowed",
}


@dataclass(slots=True)
class OKofficeException(Exception):
    code: str
    message: str
    retry_hint: str | None = None
    details: dict[str, Any] | None = None

    def to_error(self) -> OKofficeError:
        return OKofficeError(
            code=self.code,
            message=self.message,
            retry_hint=self.retry_hint,
            details=self.details or {},
        )
