from __future__ import annotations

from typing import Literal

from pydantic import Field

from okoffice.schemas.models import OKofficeModel, ToolStatus


OfficeDomain = Literal["office", "word", "sheet", "deck", "pdf"]


class OfficeToolSpec(OKofficeModel):
    name: str
    status: ToolStatus
    description: str
    domain: OfficeDomain
    interfaces: list[str] = Field(default_factory=list)
    implemented: bool = False
    oss_default: bool = True
    requires_model: bool = False


class OfficeToolManifest(OKofficeModel):
    manifest_version: str = "0.1"
    product: str = "okoffice"
    compatibility_package: str = "okoffice"
    tool_count: int
    domains: list[OfficeDomain]
    namespace_strategy: dict[str, str] = Field(default_factory=dict)
    tools: list[OfficeToolSpec]
