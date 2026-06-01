from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field, field_serializer


ToolStatus = Literal["stable", "beta", "experimental", "planned", "cloud_only"]
ResultStatus = Literal["succeeded", "failed"]
ValidationStatus = Literal["passed", "failed", "warning", "skipped"]


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


class AgentPDFModel(BaseModel):
    model_config = ConfigDict(arbitrary_types_allowed=True)


class FileRef(AgentPDFModel):
    path: Path
    mime_type: str | None = None
    size_bytes: int | None = None
    sha256: str | None = None

    @field_serializer("path")
    def serialize_path(self, value: Path) -> str:
        return value.as_posix()


class Artifact(AgentPDFModel):
    artifact_id: str
    path: Path
    mime_type: str
    size_bytes: int
    sha256: str
    source_tool: str
    page_count: int | None = None
    created_at: datetime = Field(default_factory=utc_now)
    retention_hint: str = "local"

    @field_serializer("path")
    def serialize_path(self, value: Path) -> str:
        return value.as_posix()


class Job(AgentPDFModel):
    job_id: str
    tool: str
    status: ResultStatus
    created_at: datetime = Field(default_factory=utc_now)
    completed_at: datetime | None = None


class ValidationCheck(AgentPDFModel):
    name: str
    status: ValidationStatus
    details: dict[str, Any] = Field(default_factory=dict)
    message: str | None = None


class ValidationReport(AgentPDFModel):
    status: Literal["passed", "failed", "warning", "skipped"]
    checks: list[ValidationCheck] = Field(default_factory=list)
    page_count: int | None = None
    warnings: list[str] = Field(default_factory=list)


class AgentPDFError(AgentPDFModel):
    code: str
    message: str
    retry_hint: str | None = None
    details: dict[str, Any] = Field(default_factory=dict)


class ToolResult(AgentPDFModel):
    job_id: str
    status: ResultStatus
    tool: str
    artifacts: list[Artifact] = Field(default_factory=list)
    validation: ValidationReport | None = None
    warnings: list[str] = Field(default_factory=list)
    usage: dict[str, Any] = Field(default_factory=dict)
    next_recommended_tools: list[str] = Field(default_factory=list)
    error: AgentPDFError | None = None


class ToolSpec(AgentPDFModel):
    name: str
    status: ToolStatus
    description: str
    category: str | None = None
    interfaces: list[str] = Field(default_factory=list)
    input_schema: dict[str, Any] | None = None
    output_schema: dict[str, Any] | None = None
    implemented: bool = False


class ToolManifest(AgentPDFModel):
    manifest_version: str = "0.1"
    tools: list[ToolSpec]
