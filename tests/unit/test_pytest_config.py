from pathlib import Path
import tomllib


def test_pytest_config_uses_runtime_temp_dir() -> None:
    pyproject_path = Path(__file__).resolve().parents[2] / "pyproject.toml"
    config = tomllib.loads(pyproject_path.read_text(encoding="utf-8"))
    addopts = config["tool"]["pytest"]["ini_options"].get("addopts", "")

    assert "--basetemp" not in addopts
