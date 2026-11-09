"""Tests for the audit command."""

import json
from pathlib import Path

import pytest
from typer.testing import CliRunner, Result

from auditor.cli import app
from tests.task_factory import VALID_YAML, make_task

REPO = Path(__file__).resolve().parents[1]
REAL_SAMPLE = REPO / "sample_tasks" / "slugify"

runner = CliRunner()


def test_audit_prints_id_title_count_and_sandbox_warning(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.chdir(REPO)
    out = tmp_path / "reports"

    result = runner.invoke(app, ["audit", "sample_tasks/slugify", "--out", str(out)])

    text = _combined(result)
    assert result.exit_code == 0
    assert "id: slugify" in text
    assert "title: Turn a phrase into a URL slug" in text
    assert "requirements: 2" in text
    assert "requirement_coverage: 1.000" in text
    assert "mutation_score: 1.000" in text
    assert "findings: 0" in text
    assert "later stages run task code" in text
    assert "not a security sandbox" in text
    assert "Traceback" not in text
    assert REAL_SAMPLE.is_dir()
    payload = _load(out / "slugify.json")
    markdown = (out / "slugify.md").read_text(encoding="utf-8")
    assert payload["findings"] == []
    assert payload["requirement_coverage"] == 1.0
    assert payload["mutation_score"] == 1.0
    assert "requirement_coverage: 1.000" in markdown
    assert "mutation_score: 1.000" in markdown
    assert "No findings." in markdown


def test_audit_prints_validation_error_and_exits_nonzero(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    def fail_if_called(task: object) -> object:
        raise AssertionError(f"checks ran for {task!r}")

    monkeypatch.setattr("auditor.cli.run_audit", fail_if_called)
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


def test_audit_refuses_a_path_outside_sample_tasks(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    def fail_if_called(task: object) -> object:
        raise AssertionError(f"checks ran for {task!r}")

    monkeypatch.setattr("auditor.cli.run_audit", fail_if_called)
    result = runner.invoke(app, ["audit", str(tmp_path)])

    text = _combined(result)
    assert result.exit_code == 1
    assert "error: path: must be inside sample_tasks" in text
    assert str(tmp_path.resolve()) in text
    assert "later stages run task code" in text
    assert "Traceback" not in text


def test_audit_writes_the_planted_finding_in_both_reports(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.chdir(REPO)
    out = tmp_path / "reports"

    result = runner.invoke(
        app,
        ["audit", "sample_tasks/plant_weak_assertion_1", "--out", str(out)],
    )

    text = _combined(result)
    assert result.exit_code == 0
    assert "later stages run task code" in text
    assert "not a security sandbox" in text
    assert "Traceback" not in text
    payload = _load(out / "plant_weak_assertion_1.json")
    markdown = (out / "plant_weak_assertion_1.md").read_text(encoding="utf-8")
    finding = _one_finding(payload, "weak_assertion")
    coverage = payload["requirement_coverage"]
    score = payload["mutation_score"]
    assert isinstance(coverage, float)
    assert isinstance(score, float)
    assert f"requirement_coverage: {coverage:.3f}" in markdown
    assert f"mutation_score: {score:.3f}" in markdown
    assert f"check: {finding['check']}" in markdown
    assert f"severity: {finding['severity']}" in markdown
    assert f"location: {finding['location']}" in markdown
    assert f"explanation: {finding['explanation']}" in markdown


def _combined(result: Result) -> str:
    if result.stderr in result.output:
        return result.output
    return f"{result.output}{result.stderr}"


def _load(path: Path) -> dict[str, object]:
    loaded: object = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(loaded, dict):
        raise AssertionError("report is not an object")
    parsed: dict[str, object] = {}
    for key, value in loaded.items():
        if not isinstance(key, str):
            raise AssertionError("report key is not a string")
        parsed[key] = value
    return parsed


def _one_finding(payload: dict[str, object], check: str) -> dict[str, str]:
    raw = payload["findings"]
    if not isinstance(raw, list):
        raise AssertionError("findings is not a list")
    matches: list[dict[str, str]] = []
    for item in raw:
        if not isinstance(item, dict):
            raise AssertionError("finding is not an object")
        finding = _finding(item)
        if finding["check"] == check:
            matches.append(finding)
    if len(matches) != 1:
        raise AssertionError(f"{check} count is {len(matches)}")
    return matches[0]


def _finding(item: dict[object, object]) -> dict[str, str]:
    finding: dict[str, str] = {}
    for field in ("check", "severity", "location", "explanation"):
        value = item.get(field)
        if not isinstance(value, str) or not value:
            raise AssertionError(f"{field} is missing")
        finding[field] = value
    return finding
