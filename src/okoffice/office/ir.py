from __future__ import annotations

from typing import Annotated, Any, Literal

from pydantic import Field, field_validator

from okoffice.schemas.models import OKofficeModel


SourceNodeType = Literal[
    "pdf",
    "pdf_page",
    "pdf_block",
    "word_document",
    "word_section",
    "word_paragraph",
    "word_run",
    "word_table",
    "word_cell",
    "word_comment",
    "word_revision",
    "word_field",
    "workbook",
    "sheet",
    "cell",
    "sheet_range",
    "formula",
    "table",
    "pivot_table",
    "chart",
    "named_range",
    "deck",
    "slide",
    "shape",
    "slide_table",
    "slide_chart",
    "speaker_note",
    "media",
    "image",
    "image_region",
    "scan",
    "video",
    "video_frame",
    "transcript_segment",
    "audio",
    "web_page",
    "markdown",
    "html",
    "text",
    "code_file",
    "code_range",
    "csv_row",
    "database_row",
    "json_field",
    "prompt",
    "review_note",
]
ArtifactKind = Literal["pdf", "docx", "xlsx", "pptx", "document", "workbook", "deck", "bundle", "context"]
Confidence = Annotated[float, Field(ge=0.0, le=1.0)]


class PdfLocator(OKofficeModel):
    kind: Literal["pdf"] = "pdf"
    page: int | None = Field(default=None, ge=1)
    bbox: list[float] | None = None
    annotation_id: str | None = None
    form_field: str | None = None

    @field_validator("bbox")
    @classmethod
    def _validate_bbox(cls, value: list[float] | None) -> list[float] | None:
        return _validate_bbox(value)


class WordLocator(OKofficeModel):
    kind: Literal["word"] = "word"
    section: int | None = Field(default=None, ge=1)
    section_id: str | None = None
    paragraph_id: str | None = None
    paragraph_index: int | None = Field(default=None, ge=0)
    run_index: int | None = Field(default=None, ge=0)
    table_id: str | None = None
    table_index: int | None = Field(default=None, ge=0)
    row_index: int | None = Field(default=None, ge=0)
    column_index: int | None = Field(default=None, ge=0)
    comment_id: str | None = None
    field_id: str | None = None


class SheetLocator(OKofficeModel):
    kind: Literal["sheet"] = "sheet"
    sheet: str
    cell: str | None = None
    range: str | None = None
    row: int | None = Field(default=None, ge=1)
    column: str | int | None = None
    table: str | None = None
    chart: str | None = None
    formula: str | None = None
    named_range: str | None = None


class DeckLocator(OKofficeModel):
    kind: Literal["deck"] = "deck"
    slide: int | None = Field(default=None, ge=1)
    slide_id: str | None = None
    shape_id: str | None = None
    placeholder: str | None = None
    notes: bool | None = None
    bbox: list[float] | None = None
    unit: Literal["pt", "in", "cm", "px"] | None = None

    @field_validator("bbox")
    @classmethod
    def _validate_bbox(cls, value: list[float] | None) -> list[float] | None:
        return _validate_bbox(value)


class CodeLocator(OKofficeModel):
    kind: Literal["code"] = "code"
    path: str
    line_start: int | None = Field(default=None, ge=1)
    line_end: int | None = Field(default=None, ge=1)


class TimeLocator(OKofficeModel):
    kind: Literal["time"] = "time"
    time_range: list[str]

    @field_validator("time_range")
    @classmethod
    def _validate_time_range(cls, value: list[str]) -> list[str]:
        if len(value) != 2:
            raise ValueError("time_range must contain start and end timestamps")
        return value


OfficeLocator = Annotated[
    PdfLocator | WordLocator | SheetLocator | DeckLocator | CodeLocator | TimeLocator,
    Field(discriminator="kind"),
]


class SourceRef(OKofficeModel):
    source_id: str
    locator: OfficeLocator
    confidence: Confidence | None = None
    excerpt: str | None = None


class SourceGraphNode(OKofficeModel):
    source_id: str
    source_type: SourceNodeType
    parent_source_id: str | None = None
    artifact_id: str | None = None
    locator: OfficeLocator | None = None
    text: str | None = None
    sha256: str | None = None
    confidence: Confidence | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)


class SourceGraphEdge(OKofficeModel):
    edge_id: str
    from_source_id: str
    to_source_id: str
    relation: Literal["contains", "derived_from", "cites", "summarizes", "validates", "renders_to"]
    confidence: Confidence | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)


class SourceGraph(OKofficeModel):
    source_graph_id: str
    nodes: list[SourceGraphNode] = Field(default_factory=list)
    edges: list[SourceGraphEdge] = Field(default_factory=list)


class OfficeIR(OKofficeModel):
    ir_version: str = "0.3"
    document_id: str
    artifact_kind: ArtifactKind
    source: dict[str, Any] = Field(default_factory=dict)
    metadata: dict[str, Any] = Field(default_factory=dict)
    pages: list[dict[str, Any]] = Field(default_factory=list)
    sections: list[dict[str, Any]] = Field(default_factory=list)
    paragraphs: list[dict[str, Any]] = Field(default_factory=list)
    sheets: list[dict[str, Any]] = Field(default_factory=list)
    slides: list[dict[str, Any]] = Field(default_factory=list)
    source_refs: list[SourceRef] = Field(default_factory=list)


def _validate_bbox(value: list[float] | None) -> list[float] | None:
    if value is None:
        return None
    if len(value) != 4:
        raise ValueError("bbox must contain four numeric coordinates")
    return value
