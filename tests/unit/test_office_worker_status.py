import json

from typer.testing import CliRunner


def test_office_workers_status_reports_feature_flagged_contracts() -> None:
    from agentpdf.office.workers import inspect_office_workers

    result = inspect_office_workers()

    assert result.status == "succeeded"
    assert result.tool == "office.workers.status"
    assert result.validation is not None
    assert result.validation.status == "passed"
    assert result.usage["summary"] == {
        "worker_count": 6,
        "enabled_count": 0,
        "available_count": 0,
        "missing_dependency_count": 0,
        "cloud_required_count": 1,
        "default_core_dependency_count": 0,
    }
    worker_ids = {worker["worker_id"] for worker in result.usage["workers"]}
    assert worker_ids == {
        "officecli",
        "libreoffice",
        "browser_renderer",
        "ocr",
        "formula_engine",
        "ai_provider",
    }
    assert all(worker["enabled"] is False for worker in result.usage["workers"])
    assert all(worker["status"] == "disabled" for worker in result.usage["workers"])
    assert all(worker["default_core_dependency"] is False for worker in result.usage["workers"])
    assert "office.worker_contracts" in result.usage


def test_office_workers_status_reports_missing_enabled_dependency() -> None:
    from agentpdf.office.workers import inspect_office_workers

    result = inspect_office_workers(
        feature_flags={"libreoffice": True},
        command_paths={"libreoffice": "__okoffice_missing_libreoffice_binary__"},
    )

    libreoffice = _worker(result.usage["workers"], "libreoffice")
    assert result.validation is not None
    assert result.validation.status == "warning"
    assert libreoffice["enabled"] is True
    assert libreoffice["status"] == "missing_dependency"
    assert libreoffice["command"] == "__okoffice_missing_libreoffice_binary__"
    assert libreoffice["checks"][0] == {
        "name": "feature_flag_enabled",
        "status": "passed",
    }
    assert libreoffice["checks"][1]["name"] == "dependency_available"
    assert libreoffice["checks"][1]["status"] == "failed"
    assert "LibreOffice worker is enabled but its executable was not found." in result.warnings


def test_okoffice_workers_status_cli_returns_tool_result_json() -> None:
    from okoffice.cli.main import app

    result = CliRunner().invoke(app, ["workers", "status", "--json"])

    assert result.exit_code == 0
    payload = json.loads(result.stdout)
    assert payload["tool"] == "office.workers.status"
    assert payload["usage"]["summary"]["worker_count"] == 6


def test_office_workers_status_runs_through_rest_api() -> None:
    from fastapi.testclient import TestClient

    from agentpdf.api.app import create_app

    response = TestClient(create_app()).post(
        "/v1/tools/office.workers.status/run",
        json={
            "feature_flags": {"libreoffice": True},
            "command_paths": {"libreoffice": "__okoffice_missing_libreoffice_binary__"},
        },
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["tool"] == "office.workers.status"
    assert _worker(payload["usage"]["workers"], "libreoffice")["status"] == "missing_dependency"


def test_office_workers_status_runs_through_mcp_function() -> None:
    from agentpdf.mcp.server import office_workers_status

    payload = json.loads(
        office_workers_status(
            feature_flags={"libreoffice": True},
            command_paths={"libreoffice": "__okoffice_missing_libreoffice_binary__"},
        )
    )

    assert payload["tool"] == "office.workers.status"
    assert _worker(payload["usage"]["workers"], "libreoffice")["status"] == "missing_dependency"


def test_office_workers_status_runs_through_generic_workflow_runner() -> None:
    from agentpdf.workflows.runner import run_workflow

    result = run_workflow(
        {
            "steps": [
                {
                    "tool": "office.workers.status",
                    "input": {},
                }
            ]
        }
    )

    assert result.status == "succeeded"
    step = result.usage["workflow_run"]["step_results"][0]
    assert step["tool"] == "office.workers.status"
    assert step["validation"]["status"] == "passed"


def _worker(workers: list[dict[str, object]], worker_id: str) -> dict[str, object]:
    return next(worker for worker in workers if worker["worker_id"] == worker_id)
