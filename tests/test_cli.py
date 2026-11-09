"""Tests for the audit command."""

from pathlib import Path

import pytest
from typer.testing import CliRunner, Result

from auditor.cli import app
from tests.task_factory import VALID_YAML, make_task

REPO = Path(__file__).resolve().parents[1]
REAL_SAMPLE = REPO / "sample_tasks" / "slugify"

runner = CliRunner()


def test_audit_prints_id_title_count_and_sandbox_warning(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.chdir(REPO)

    result = runner.invoke(app, ["audit", "sample_tasks/slugify"])

    text = _combined(result)
    assert result.exit_code == 0
    assert "id: slugify" in text
    assert "title: Turn a phrase into a URL slug" in text
    assert "requirements: 2" in text
    assert "later stages run task code" in text
    assert "not a security sandbox" in text
    assert "Traceback" not in text
    assert REAL_SAMPLE.is_dir()


def test_audit_prints_validation_error_and_exits_nonzero(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    sample_root = tmp_path / "sample_tasks"
    yaml_text = VALID_YAML.replace("language: python", "language: javascript")
    task_dir = make_task(sample_root, "slugify", yaml_text)
    monkeypatch.setattr("auditor.loader.default_sample_root", lambda: sample_root)

    result = runner.invoke(app, ["audit", str(task_dir)])

    text = _combined(result)
    assert result.exit_code == 1
    assert "error: language: must be 'python' (value: 'javascript')" in text
    assert "later stages run task code" in text
    assert "not a security sandbox" in text
    assert "Traceback" not in text


def test_audit_refuses_a_path_outside_sample_tasks(tmp_path: Path) -> None:
    result = runner.invoke(app, ["audit", str(tmp_path)])

    text = _combined(result)
    assert result.exit_code == 1
    assert "error: path: must be inside sample_tasks" in text
    assert str(tmp_path.resolve()) in text
    assert "later stages run task code" in text
    assert "Traceback" not in text


def test_audit_command_stays_validation_only() -> None:
    source = (REPO / "auditor" / "cli.py").read_text(encoding="utf-8")
    assert "auditor.checks" not in source
    assert "run_static_checks" not in source
    assert "run_coverage_checks" not in source
    assert "requirement_coverage" not in source
    assert "run_dynamic_checks" not in source


def _combined(result: Result) -> str:
    if result.stderr in result.output:
        return result.output
    return f"{result.output}{result.stderr}"
