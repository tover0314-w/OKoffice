from __future__ import annotations

from typing import Literal

from pydantic import Field

from agentpdf.schemas.models import AgentPDFModel, ToolStatus


OfficeDomain = Literal["office", "word", "sheet", "deck", "pdf"]


class OfficeToolSpec(AgentPDFModel):
    name: str
    status: ToolStatus
    description: str
    domain: OfficeDomain
    interfaces: list[str] = Field(default_factory=list)
    implemented: bool = False
    oss_default: bool = True
    requires_model: bool = False


class OfficeToolManifest(AgentPDFModel):
    manifest_version: str = "0.1"
    product: str = "okoffice"
    compatibility_package: str = "agentpdf"
    tool_count: int
    domains: list[OfficeDomain]
    namespace_strategy: dict[str, str] = Field(default_factory=dict)
    tools: list[OfficeToolSpec]
