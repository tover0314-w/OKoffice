from agentpdf.workflows.planner import plan_workflow


def test_plan_workflow_for_pdf_chat_returns_agent_tool_chain() -> None:
    result = plan_workflow(
        goal="Chat with this PDF and cite the answer with page evidence.",
        input_path="report.pdf",
    )

    assert result.status == "succeeded"
    assert result.tool == "pdf.workflow.plan"
    workflow = result.usage["workflow"]
    assert workflow["plan_id"].startswith("wfplan_")
    assert workflow["goal"] == "Chat with this PDF and cite the answer with page evidence."
    assert "parser" in workflow["agents"]
    assert "retriever" in workflow["agents"]
    assert "citation_checker" in workflow["agents"]
    assert "validator" in workflow["agents"]
    tool_chain = [step["tool"] for step in workflow["steps"]]
    assert tool_chain[:2] == ["pdf.inspect.document", "pdf.inspect.pages"]
    assert "pdf.ai.parse.lite" in tool_chain
    assert "pdf.ai.rag.ingest" in tool_chain
    assert "pdf.ai.rag.query" in tool_chain
    assert "pdf.ai.rag.cite_answer" in tool_chain
    assert "pdf.ai.rag.highlight_sources" in tool_chain
    assert workflow["steps"][0]["input"]["path"] == "report.pdf"
    assert workflow["cloud_boundary"]["local_first"] is True
    assert result.next_recommended_tools[0] == "pdf.inspect.document"


def test_plan_workflow_for_optimize_returns_deterministic_validation_chain() -> None:
    result = plan_workflow(
        goal="Compress and repair this PDF, then validate it before sharing.",
        input_path="report.pdf",
    )

    workflow = result.usage["workflow"]
    tool_chain = [step["tool"] for step in workflow["steps"]]

    assert "pdf.optimize.compress" in tool_chain
    assert "pdf.optimize.repair" in tool_chain
    assert tool_chain[-2:] == ["pdf.validation.validate_output", "pdf.validation.render_check"]
    assert "validator" in workflow["agents"]
