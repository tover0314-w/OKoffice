"""Unit tests for Composition IR JSON Patch operations."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from okoffice.mcp.server import create_mcp_server
from okoffice.patch.transaction import (
    apply_composition_ir_patch,
    plan_composition_ir_patch,
    verify_composition_ir_patch,
)
from okoffice.schemas.errors import OKofficeException


SAMPLE_COMPOSITION = {
    "composition_ir": {
        "composition_version": "0.1",
        "composition_id": "cmp_test001",
        "context_packet_id": "ctxpkt_test001",
        "target_profile_id": "research_brief",
        "blocks": [
            {
                "block_id": "blk_001",
                "type": "section",
                "title": "Executive Summary",
                "source_refs": ["src://doc1"],
                "target_slot": "cover",
                "data": {"heading": "Summary", "body": "Test body text."},
            },
            {
                "block_id": "blk_002",
                "type": "section",
                "title": "Evidence",
                "source_refs": ["src://doc2"],
                "target_slot": "body",
                "data": {"heading": "Evidence", "body": "Evidence text."},
            },
            {
                "block_id": "blk_003",
                "type": "code",
                "title": "Code Review",
                "source_refs": ["src://doc3"],
                "target_slot": "code_review",
            },
        ],
    },
    "source_map": [
        {"block_id": "blk_001", "source_ref": "src://doc1", "type": "section"},
        {"block_id": "blk_002", "source_ref": "src://doc2", "type": "section"},
        {"block_id": "blk_003", "source_ref": "src://doc3", "type": "code"},
    ],
}


@pytest.fixture
def composition_file(tmp_path):
    path = tmp_path / "test.composition.json"
    path.write_text(json.dumps(SAMPLE_COMPOSITION, ensure_ascii=False), encoding="utf-8")
    return path


class TestPlanCompositionIRPatch:
    def test_plan_replace_block_title(self, composition_file, tmp_path):
        output = tmp_path / "patch-plan.json"
        result = plan_composition_ir_patch(
            composition_file,
            operations=[{"op": "replace_block_title", "block_id": "blk_001", "new_title": "Updated Summary"}],
            output_path=output,
        )
        assert result.status == "succeeded"
        assert output.exists()
        manifest = json.loads(output.read_text(encoding="utf-8"))
        assert manifest["operations"][0]["op"] == "replace_block_title"
        assert manifest["operations"][0]["new_title"] == "Updated Summary"

    def test_plan_rejects_unknown_block(self, composition_file, tmp_path):
        with pytest.raises(OKofficeException, match="block_not_found"):
            plan_composition_ir_patch(
                composition_file,
                operations=[{"op": "replace_block_title", "block_id": "blk_999", "new_title": "X"}],
                output_path=tmp_path / "plan.json",
            )

    def test_plan_reorder_blocks(self, composition_file, tmp_path):
        output = tmp_path / "patch-plan.json"
        result = plan_composition_ir_patch(
            composition_file,
            operations=[{"op": "reorder_blocks", "block_ids": ["blk_003", "blk_001", "blk_002"]}],
            output_path=output,
        )
        assert result.status == "succeeded"

    def test_plan_reorder_rejects_incomplete(self, composition_file, tmp_path):
        with pytest.raises(OKofficeException, match="Missing"):
            plan_composition_ir_patch(
                composition_file,
                operations=[{"op": "reorder_blocks", "block_ids": ["blk_001"]}],
                output_path=tmp_path / "plan.json",
            )

    def test_plan_add_block(self, composition_file, tmp_path):
        output = tmp_path / "patch-plan.json"
        result = plan_composition_ir_patch(
            composition_file,
            operations=[{
                "op": "add_block",
                "block": {
                    "block_id": "blk_004",
                    "type": "citation",
                    "title": "New Citation",
                    "source_refs": ["src://doc1"],
                },
            }],
            output_path=output,
        )
        assert result.status == "succeeded"

    def test_plan_add_block_rejects_duplicate(self, composition_file, tmp_path):
        with pytest.raises(OKofficeException, match="already exists"):
            plan_composition_ir_patch(
                composition_file,
                operations=[{
                    "op": "add_block",
                    "block": {"block_id": "blk_001", "type": "section", "title": "Dup"},
                }],
                output_path=tmp_path / "plan.json",
            )

    def test_plan_remove_block(self, composition_file, tmp_path):
        output = tmp_path / "patch-plan.json"
        result = plan_composition_ir_patch(
            composition_file,
            operations=[{"op": "remove_block", "block_id": "blk_003"}],
            output_path=output,
        )
        assert result.status == "succeeded"

    def test_plan_update_block_data(self, composition_file, tmp_path):
        output = tmp_path / "patch-plan.json"
        result = plan_composition_ir_patch(
            composition_file,
            operations=[{"op": "update_block_data", "block_id": "blk_001", "data": {"body": "New body text."}}],
            output_path=output,
        )
        assert result.status == "succeeded"

    def test_plan_rejects_empty_operations(self, composition_file, tmp_path):
        with pytest.raises(OKofficeException, match="at least one"):
            plan_composition_ir_patch(
                composition_file,
                operations=[],
                output_path=tmp_path / "plan.json",
            )

    def test_plan_reorder_after_add_block(self, composition_file, tmp_path):
        """reorder_blocks should accept a block added by a prior add_block in the same patch."""
        output = tmp_path / "patch-plan.json"
        result = plan_composition_ir_patch(
            composition_file,
            operations=[
                {"op": "add_block", "block": {"block_id": "blk_004", "type": "section", "title": "Added"}},
                {"op": "reorder_blocks", "block_ids": ["blk_003", "blk_004", "blk_001", "blk_002"]},
            ],
            output_path=output,
        )
        assert result.status == "succeeded"

    def test_plan_reorder_after_remove_block(self, composition_file, tmp_path):
        """reorder_blocks should work after a remove_block shrinks the block set."""
        output = tmp_path / "patch-plan.json"
        result = plan_composition_ir_patch(
            composition_file,
            operations=[
                {"op": "remove_block", "block_id": "blk_003"},
                {"op": "reorder_blocks", "block_ids": ["blk_002", "blk_001"]},
            ],
            output_path=output,
        )
        assert result.status == "succeeded"

    def test_plan_reorder_rejects_incomplete_after_add(self, composition_file, tmp_path):
        """reorder_blocks after add_block must still reference ALL effective blocks."""
        with pytest.raises(OKofficeException, match="Missing"):
            plan_composition_ir_patch(
                composition_file,
                operations=[
                    {"op": "add_block", "block": {"block_id": "blk_004", "type": "section", "title": "Added"}},
                    {"op": "reorder_blocks", "block_ids": ["blk_001", "blk_002", "blk_003"]},
                ],
                output_path=tmp_path / "plan.json",
            )

    def test_plan_rejects_unknown_op(self, composition_file, tmp_path):
        with pytest.raises(OKofficeException, match="Unsupported composition IR operation"):
            plan_composition_ir_patch(
                composition_file,
                operations=[{"op": "explode_everything"}],
                output_path=tmp_path / "plan.json",
            )


class TestApplyCompositionIRPatch:
    def test_apply_replace_title(self, composition_file, tmp_path):
        plan_output = tmp_path / "plan.json"
        plan_composition_ir_patch(
            composition_file,
            operations=[{"op": "replace_block_title", "block_id": "blk_001", "new_title": "Replaced!"}],
            output_path=plan_output,
        )
        patched_output = tmp_path / "patched.composition.json"
        result = apply_composition_ir_patch(plan_output, output_path=patched_output)
        assert result.status == "succeeded"

        patched = json.loads(patched_output.read_text(encoding="utf-8"))
        blocks = patched["composition_ir"]["blocks"]
        blk_001 = next(b for b in blocks if b["block_id"] == "blk_001")
        assert blk_001["title"] == "Replaced!"

    def test_apply_update_data_merges(self, composition_file, tmp_path):
        plan_output = tmp_path / "plan.json"
        plan_composition_ir_patch(
            composition_file,
            operations=[{"op": "update_block_data", "block_id": "blk_001", "data": {"extra_field": "added"}}],
            output_path=plan_output,
        )
        patched_output = tmp_path / "patched.composition.json"
        apply_composition_ir_patch(plan_output, output_path=patched_output)

        patched = json.loads(patched_output.read_text(encoding="utf-8"))
        blk_001 = next(b for b in patched["composition_ir"]["blocks"] if b["block_id"] == "blk_001")
        assert blk_001["data"]["extra_field"] == "added"
        assert blk_001["data"]["body"] == "Test body text."  # original preserved

    def test_apply_reorder_blocks(self, composition_file, tmp_path):
        plan_output = tmp_path / "plan.json"
        plan_composition_ir_patch(
            composition_file,
            operations=[{"op": "reorder_blocks", "block_ids": ["blk_003", "blk_002", "blk_001"]}],
            output_path=plan_output,
        )
        patched_output = tmp_path / "patched.composition.json"
        apply_composition_ir_patch(plan_output, output_path=patched_output)

        patched = json.loads(patched_output.read_text(encoding="utf-8"))
        blocks = patched["composition_ir"]["blocks"]
        assert [b["block_id"] for b in blocks] == ["blk_003", "blk_002", "blk_001"]

    def test_apply_add_and_remove_block(self, composition_file, tmp_path):
        plan_output = tmp_path / "plan.json"
        plan_composition_ir_patch(
            composition_file,
            operations=[
                {"op": "add_block", "block": {"block_id": "blk_new", "type": "section", "title": "Added"}},
                {"op": "remove_block", "block_id": "blk_002"},
            ],
            output_path=plan_output,
        )
        patched_output = tmp_path / "patched.composition.json"
        result = apply_composition_ir_patch(plan_output, output_path=patched_output)
        assert result.status == "succeeded"

        patched = json.loads(patched_output.read_text(encoding="utf-8"))
        block_ids = [b["block_id"] for b in patched["composition_ir"]["blocks"]]
        assert "blk_new" in block_ids
        assert "blk_002" not in block_ids
        assert result.usage["block_count_after"] == 3


class TestVerifyCompositionIRPatch:
    def test_verify_reports_block_changes(self, composition_file, tmp_path):
        plan_output = tmp_path / "plan.json"
        plan_composition_ir_patch(
            composition_file,
            operations=[
                {"op": "remove_block", "block_id": "blk_003"},
                {"op": "add_block", "block": {"block_id": "blk_new", "type": "section", "title": "New"}},
            ],
            output_path=plan_output,
        )
        patched_output = tmp_path / "patched.composition.json"
        apply_composition_ir_patch(plan_output, output_path=patched_output)

        result = verify_composition_ir_patch(plan_output, patched_path=patched_output)
        assert result.status == "succeeded"
        v = result.usage["verification"]
        assert "blk_new" in v["blocks_added"]
        assert "blk_003" in v["blocks_removed"]
        assert v["composition_ir_valid"] is True


class TestMCPToolRegistration:
    def test_composition_ir_patch_tools_registered(self):
        server = create_mcp_server()
        tool_names = {tool.name for tool in __import__("asyncio").run(server.list_tools())}
        assert "pdf_patch_composition_ir_plan" in tool_names
        assert "pdf_patch_composition_ir_apply" in tool_names
        assert "pdf_patch_composition_ir_verify" in tool_names

    def test_annotation_write_tools_not_marked_readonly(self):
        from okoffice.mcp.server import _infer_tool_annotations
        write_tools_with_readonly_substrings = [
            "pdf_extract_pages",
            "pdf_extract_images",
            "office_workflow_extract_to_sheet",
            "sheet_create_evidence_workbook",
            "pdf_artifacts_manifest",
            "pdf_artifacts_graph",
            "pdf_ai_create_plan_template_pack",
            "pdf_ai_create_validate_template_pack",
        ]
        for name in write_tools_with_readonly_substrings:
            ann = _infer_tool_annotations(name)
            assert ann.readOnlyHint is not True, f"{name} incorrectly marked readOnly"

    def test_annotation_readonly_tools_still_readonly(self):
        from okoffice.mcp.server import _infer_tool_annotations
        for name in ["pdf_inspect_document", "pdf_validate_output", "pdf_blank_page_check"]:
            ann = _infer_tool_annotations(name)
            assert ann.readOnlyHint is True, f"{name} should be readOnly"

    def test_annotation_destructive_tools(self):
        from okoffice.mcp.server import _infer_tool_annotations
        for name in ["pdf_security_redact", "pdf_security_sanitize", "pdf_remove_pages"]:
            ann = _infer_tool_annotations(name)
            assert ann.destructiveHint is True, f"{name} should be destructive"
