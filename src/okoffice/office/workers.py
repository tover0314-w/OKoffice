from __future__ import annotations

import os
import shutil
from typing import Any, Literal
from uuid import uuid4

from pydantic import Field

from okoffice.schemas.models import OKofficeModel, ToolResult, ValidationCheck, ValidationReport


TOOL_NAME = "office.workers.status"
WorkerStatus = Literal["disabled", "available", "missing_dependency", "not_configured"]


class OfficeWorkerContract(OKofficeModel):
    worker_id: str
    label: str
    category: str
    feature_flag: str
    command_name: str | None = None
    install_extra: str | None = None
    default_core_dependency: bool = False
    cloud_required: bool = False
    license_note: str
    description: str
    output_evidence: list[str] = Field(default_factory=list)


WORKER_CONTRACTS: list[OfficeWorkerContract] = [
    OfficeWorkerContract(
        worker_id="officecli",
        label="OfficeCLI adapter",
        category="office_dom",
        feature_flag="OKOFFICE_ENABLE_OFFICECLI_WORKER",
        command_name="officecli",
        install_extra="officecli-worker",
        license_note="Optional external worker; not a default core dependency.",
        description="High-fidelity Word, Excel, and PowerPoint DOM operations through an explicit local worker.",
        output_evidence=["worker_version", "capability_list", "license_note"],
    ),
    OfficeWorkerContract(
        worker_id="libreoffice",
        label="LibreOffice conversion/render adapter",
        category="office_conversion",
        feature_flag="OKOFFICE_ENABLE_LIBREOFFICE_WORKER",
        command_name="soffice",
        install_extra="libreoffice-worker",
        license_note="Optional system dependency; document license and runtime boundary before enabling.",
        description="Local Office-to-PDF conversion and preview rendering via LibreOffice-compatible commands.",
        output_evidence=["executable_path", "worker_version", "conversion_log"],
    ),
    OfficeWorkerContract(
        worker_id="browser_renderer",
        label="Browser render adapter",
        category="rendering",
        feature_flag="OKOFFICE_ENABLE_BROWSER_RENDERER",
        command_name="playwright",
        install_extra="browser-renderer",
        license_note="Optional browser automation worker; not required for default OSS tools.",
        description="Browser-backed HTML/PDF previews, screenshots, and visual QA evidence.",
        output_evidence=["renderer_backend", "screenshot_path", "pdf_path", "render_log"],
    ),
    OfficeWorkerContract(
        worker_id="ocr",
        label="OCR adapter",
        category="ocr",
        feature_flag="OKOFFICE_ENABLE_OCR_WORKER",
        command_name="tesseract",
        install_extra="ocr-worker",
        license_note="Optional OCR runtime; outputs must include confidence and source page refs.",
        description="Local OCR for scanned PDFs and images with explicit confidence and bounding-box evidence.",
        output_evidence=["text_regions", "confidence", "page_refs", "bbox_refs"],
    ),
    OfficeWorkerContract(
        worker_id="formula_engine",
        label="Formula calculation adapter",
        category="spreadsheet_calculation",
        feature_flag="OKOFFICE_ENABLE_FORMULA_WORKER",
        command_name=None,
        install_extra="formula-worker",
        license_note="Optional calculation engine; default validation remains structural only.",
        description="Workbook formula recalculation and cached-value verification behind an explicit feature flag.",
        output_evidence=["calculation_engine", "recalculated_cells", "formula_errors"],
    ),
    OfficeWorkerContract(
        worker_id="ai_provider",
        label="Configured AI provider router",
        category="ai",
        feature_flag="OKOFFICE_ENABLE_AI_PROVIDER",
        command_name=None,
        install_extra=None,
        cloud_required=True,
        license_note="Configured provider only; no hosted AI is called by default.",
        description="Optional model/VLM routing for extraction, explanation, and generation with explicit user configuration.",
        output_evidence=["provider_id", "model_id", "usage", "source_policy"],
    ),
]


def inspect_office_workers(
    *,
    feature_flags: dict[str, bool] | None = None,
    command_paths: dict[str, str] | None = None,
) -> ToolResult:
    flags = feature_flags or {}
    commands = command_paths or {}
    workers = [_worker_status(contract, flags=flags, commands=commands) for contract in WORKER_CONTRACTS]
    warnings = _warnings(workers)
    validation = _validation_report(workers, warnings)
    return ToolResult(
        job_id=f"job_{uuid4().hex[:16]}",
        status="succeeded",
        tool=TOOL_NAME,
        validation=validation,
        warnings=warnings,
        usage={
            "summary": _summary(workers),
            "workers": workers,
            "office.worker_contracts": [contract.model_dump(mode="json") for contract in WORKER_CONTRACTS],
            "feature_flag_policy": {
                "default_enabled": False,
                "source": "explicit input or environment variables",
                "cloud_required_by_default": False,
            },
        },
        next_recommended_tools=["office.inspect.file", "office.workflow.board_pack"],
    )


def _worker_status(
    contract: OfficeWorkerContract,
    *,
    flags: dict[str, bool],
    commands: dict[str, str],
) -> dict[str, Any]:
    enabled = _flag_enabled(contract, flags)
    command = commands.get(contract.worker_id, contract.command_name)
    checks = [
        {
            "name": "feature_flag_enabled",
            "status": "passed" if enabled else "skipped",
        }
    ]
    executable_path = None
    if not enabled:
        status: WorkerStatus = "disabled"
    elif command:
        executable_path = shutil.which(command)
        if executable_path:
            status = "available"
            checks.append({"name": "dependency_available", "status": "passed", "path": executable_path})
        else:
            status = "missing_dependency"
            checks.append({"name": "dependency_available", "status": "failed", "command": command})
    else:
        status = "not_configured"
        checks.append({"name": "worker_configuration_present", "status": "failed"})

    return {
        "worker_id": contract.worker_id,
        "label": contract.label,
        "category": contract.category,
        "enabled": enabled,
        "status": status,
        "feature_flag": contract.feature_flag,
        "command": command,
        "executable_path": executable_path,
        "install_extra": contract.install_extra,
        "cloud_required": contract.cloud_required,
        "default_core_dependency": contract.default_core_dependency,
        "license_note": contract.license_note,
        "description": contract.description,
        "output_evidence": contract.output_evidence,
        "checks": checks,
    }


def _flag_enabled(contract: OfficeWorkerContract, flags: dict[str, bool]) -> bool:
    if contract.worker_id in flags:
        return bool(flags[contract.worker_id])
    value = os.environ.get(contract.feature_flag, "")
    return value.lower() in {"1", "true", "yes", "on"}


def _summary(workers: list[dict[str, Any]]) -> dict[str, int]:
    return {
        "worker_count": len(workers),
        "enabled_count": len([worker for worker in workers if worker["enabled"]]),
        "available_count": len([worker for worker in workers if worker["status"] == "available"]),
        "missing_dependency_count": len([worker for worker in workers if worker["status"] == "missing_dependency"]),
        "cloud_required_count": len([worker for worker in workers if worker["cloud_required"]]),
        "default_core_dependency_count": len([worker for worker in workers if worker["default_core_dependency"]]),
    }


def _warnings(workers: list[dict[str, Any]]) -> list[str]:
    messages = []
    for worker in workers:
        if worker["status"] == "missing_dependency":
            label = "LibreOffice" if worker["worker_id"] == "libreoffice" else str(worker["label"]).replace(" adapter", "")
            messages.append(f"{label} worker is enabled but its executable was not found.")
        if worker["status"] == "not_configured":
            messages.append(f"{worker['label']} is enabled but no local worker command or provider is configured.")
    return messages


def _validation_report(workers: list[dict[str, Any]], warnings: list[str]) -> ValidationReport:
    checks = [
        ValidationCheck(
            name=f"worker_{worker['worker_id']}",
            status="warning" if worker["status"] in {"missing_dependency", "not_configured"} else "passed",
            details={
                "enabled": worker["enabled"],
                "status": worker["status"],
                "feature_flag": worker["feature_flag"],
                "default_core_dependency": worker["default_core_dependency"],
                "cloud_required": worker["cloud_required"],
            },
        )
        for worker in workers
    ]
    return ValidationReport(
        status="warning" if warnings else "passed",
        checks=checks,
        warnings=warnings,
    )
