"""Labels for the invented sample tasks. The checks do not read them."""

from pathlib import Path

import yaml

from auditor.loader import load_task

REPO = Path(__file__).resolve().parents[1]
SAMPLE = REPO / "sample_tasks"
CHECKS = (
    "source_inspection_test",
    "weak_assertion",
    "hardcoded_solution",
    "brittle_format",
    "nondeterministic_test",
    "untested_requirement",
    "hidden_requirement",
    "solution_fails_tests",
    "cheat_solution_passes",
    "flaky_tests",
    "surviving_mutants",
)
GOOD_TASKS = (
    "slugify",
    "merge_intervals",
    "parse_duration",
    "rate_limiter",
    "double",
    "both_positive",
    "last_char",
    "scale",
)


def test_good_tasks_have_empty_labels_and_one_module() -> None:
    for task_id in GOOD_TASKS:
        root = SAMPLE / task_id
        assert _label(root) == []
        assert _environment_modules(root) == 1
        loaded = load_task(root)
        assert loaded.id == task_id
        assert len(loaded.requirements) >= 1
        yaml_text = (root / "task.yaml").read_text(encoding="utf-8")
        assert "expected_findings" not in yaml_text


def test_flawed_tasks_cover_each_check_three_times() -> None:
    plants = [
        path
        for path in SAMPLE.iterdir()
        if path.is_dir() and path.name not in GOOD_TASKS
    ]
    counts = {check: 0 for check in CHECKS}
    for root in plants:
        label = _label(root)
        assert label == [label[0]]
        assert label[0] in counts
        counts[label[0]] += 1
        assert _environment_modules(root) == 1
        loaded = load_task(root)
        assert loaded.id == root.name
        assert len(loaded.requirements) >= 1
        yaml_text = (root / "task.yaml").read_text(encoding="utf-8")
        assert "expected_findings" not in yaml_text
    assert counts == {check: 3 for check in CHECKS}
    assert sum(counts.values()) == 33
    assert len(plants) == 33


def test_loader_and_checks_do_not_read_expected_findings() -> None:
    sources = [REPO / "auditor" / "loader.py"]
    sources.extend((REPO / "auditor" / "checks").glob("*.py"))
    for path in sources:
        assert "expected_findings" not in path.read_text(encoding="utf-8")


def _label(root: Path) -> list[str]:
    label_path = root / "expected_findings.yaml"
    loaded: object = yaml.safe_load(label_path.read_text(encoding="utf-8"))
    if not isinstance(loaded, list):
        raise AssertionError(root.name)
    names: list[str] = []
    for item in loaded:
        if not isinstance(item, str):
            raise AssertionError(root.name)
        names.append(item)
    return names


def _environment_modules(root: Path) -> int:
    return len(
        [
            path
            for path in (root / "environment").glob("*.py")
            if path.name != "__init__.py"
        ]
    )
