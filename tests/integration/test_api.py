from pathlib import Path

from fastapi.testclient import TestClient

from agentpdf.api.app import create_app


def test_api_healthz() -> None:
    client = TestClient(create_app())

    response = client.get("/healthz")

    assert response.status_code == 200
    assert response.json() == {"status": "ok", "service": "agentpdf"}


def test_api_lists_complete_tool_manifest() -> None:
    client = TestClient(create_app())

    response = client.get("/v1/tools")

    assert response.status_code == 200
    payload = response.json()
    assert len(payload["tools"]) >= 100
    assert any(tool["name"] == "pdf.inspect.document" for tool in payload["tools"])


def test_api_shows_single_tool() -> None:
    client = TestClient(create_app())

    response = client.get("/v1/tools/pdf.inspect.document")

    assert response.status_code == 200
    payload = response.json()
    assert payload["name"] == "pdf.inspect.document"
    assert payload["implemented"] is True


def test_api_runs_inspect_tool(simple_pdf: Path) -> None:
    client = TestClient(create_app())

    response = client.post(
        "/v1/tools/pdf.inspect.document/run",
        json={"path": str(simple_pdf)},
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["status"] == "succeeded"
    assert payload["tool"] == "pdf.inspect.document"
    assert payload["usage"]["page_count"] == 1


def test_api_runs_merge_tool(simple_pdf: Path, two_page_pdf: Path, tmp_path: Path) -> None:
    client = TestClient(create_app())
    output = tmp_path / "merged.pdf"

    response = client.post(
        "/v1/tools/pdf.organize.merge/run",
        json={"input_paths": [str(simple_pdf), str(two_page_pdf)], "output_path": str(output)},
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["status"] == "succeeded"
    assert payload["artifacts"][0]["page_count"] == 3
    assert output.exists()


def test_api_stores_job_and_artifact_after_run(
    simple_pdf: Path, two_page_pdf: Path, tmp_path: Path
) -> None:
    client = TestClient(create_app())
    output = tmp_path / "merged.pdf"

    run_response = client.post(
        "/v1/tools/pdf.organize.merge/run",
        json={"input_paths": [str(simple_pdf), str(two_page_pdf)], "output_path": str(output)},
    )
    result = run_response.json()
    job_id = result["job_id"]
    artifact_id = result["artifacts"][0]["artifact_id"]

    job_response = client.get(f"/v1/jobs/{job_id}")
    artifact_response = client.get(f"/v1/artifacts/{artifact_id}")
    download_response = client.get(f"/v1/artifacts/{artifact_id}/download")

    assert job_response.status_code == 200
    assert job_response.json()["job_id"] == job_id
    assert artifact_response.status_code == 200
    assert artifact_response.json()["artifact_id"] == artifact_id
    assert download_response.status_code == 200
    assert download_response.content.startswith(b"%PDF")


def test_api_runs_split_tool(two_page_pdf: Path, tmp_path: Path) -> None:
    client = TestClient(create_app())
    output = tmp_path / "first.pdf"

    response = client.post(
        "/v1/tools/pdf.organize.split/run",
        json={"input_path": str(two_page_pdf), "pages": "1", "output_path": str(output)},
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["status"] == "succeeded"
    assert payload["artifacts"][0]["page_count"] == 1


def test_api_runs_extract_remove_and_rotate_tools(two_page_pdf: Path, tmp_path: Path) -> None:
    client = TestClient(create_app())

    extract = client.post(
        "/v1/tools/pdf.organize.extract_pages/run",
        json={"input_path": str(two_page_pdf), "pages": "1", "output_path": str(tmp_path / "e.pdf")},
    )
    remove = client.post(
        "/v1/tools/pdf.organize.remove_pages/run",
        json={"input_path": str(two_page_pdf), "pages": "1", "output_path": str(tmp_path / "r.pdf")},
    )
    rotate = client.post(
        "/v1/tools/pdf.organize.rotate_pages/run",
        json={
            "input_path": str(two_page_pdf),
            "pages": "1",
            "degrees": 90,
            "output_path": str(tmp_path / "rot.pdf"),
        },
    )

    assert extract.status_code == 200
    assert extract.json()["tool"] == "pdf.organize.extract_pages"
    assert remove.status_code == 200
    assert remove.json()["tool"] == "pdf.organize.remove_pages"
    assert rotate.status_code == 200
    assert rotate.json()["tool"] == "pdf.organize.rotate_pages"


def test_api_runs_render_tool(simple_pdf: Path, tmp_path: Path) -> None:
    client = TestClient(create_app())

    response = client.post(
        "/v1/tools/pdf.convert.pdf_to_images/run",
        json={
            "input_path": str(simple_pdf),
            "pages": "1",
            "image_format": "png",
            "out_dir": str(tmp_path),
        },
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["status"] == "succeeded"
    assert payload["artifacts"][0]["mime_type"] == "image/png"


def test_api_runs_text_and_metadata_tools(text_pdf: Path, metadata_pdf: Path, tmp_path: Path) -> None:
    client = TestClient(create_app())

    text = client.post(
        "/v1/tools/pdf.convert.pdf_to_text/run",
        json={"input_path": str(text_pdf), "pages": "1"},
    )
    read = client.post("/v1/tools/pdf.metadata.read/run", json={"input_path": str(metadata_pdf)})
    update = client.post(
        "/v1/tools/pdf.metadata.update/run",
        json={
            "input_path": str(metadata_pdf),
            "metadata": {"Title": "API Title"},
            "output_path": str(tmp_path / "updated.pdf"),
        },
    )
    remove = client.post(
        "/v1/tools/pdf.metadata.remove/run",
        json={"input_path": str(metadata_pdf), "output_path": str(tmp_path / "clean.pdf")},
    )

    assert text.status_code == 200
    assert "AgentPDF local text layer" in text.json()["usage"]["text"]
    assert read.status_code == 200
    assert read.json()["usage"]["metadata"]["Title"] == "Original Title"
    assert update.status_code == 200
    assert update.json()["tool"] == "pdf.metadata.update"
    assert remove.status_code == 200
    assert remove.json()["tool"] == "pdf.metadata.remove"


def test_api_rejects_unimplemented_tool() -> None:
    client = TestClient(create_app())

    response = client.post("/v1/tools/pdf.ai.parse.agentic/run", json={})

    assert response.status_code == 400
    assert response.json()["error"]["code"] == "tool_not_implemented"
