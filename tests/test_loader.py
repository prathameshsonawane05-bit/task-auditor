"""Tests for task-folder validation."""

import shutil
from pathlib import Path

import pytest

from auditor.errors import TaskValidationError
from auditor.loader import load_task
from tests.task_factory import VALID_YAML, make_task

REPO = Path(__file__).resolve().parents[1]
REAL_SAMPLE = REPO / "sample_tasks" / "slugify"


def test_valid_folder_loads_id_title_and_requirement_count(tmp_path: Path) -> None:
    sample_root = tmp_path / "sample_tasks"
    task_dir = make_task(sample_root, "slugify", VALID_YAML)

    loaded = load_task(task_dir, sample_root=sample_root)

    assert loaded.id == "slugify"
    assert loaded.title == "Turn a phrase into a URL slug"
    assert loaded.language == "python"
    assert len(loaded.requirements) == 2
    assert loaded.requirements[0].id == "R1"
    assert loaded.root == task_dir.resolve()


def test_real_sample_task_loads_from_another_working_directory(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    monkeypatch.chdir(tmp_path)

    loaded = load_task(REAL_SAMPLE)

    assert loaded.id == "slugify"
    assert loaded.title == "Turn a phrase into a URL slug"
    assert tuple(requirement.id for requirement in loaded.requirements) == ("R1", "R2")


@pytest.mark.parametrize(
    ("relative", "field", "message"),
    [
        ("task.yaml", "task.yaml", "required file is missing"),
        ("instruction.md", "instruction.md", "required file is missing"),
        ("solution/solution.py", "solution/solution.py", "required file is missing"),
        ("environment", "environment", "required directory is missing"),
        ("tests", "tests", "required directory is missing"),
    ],
)
def test_missing_file_or_directory_names_the_path(
    tmp_path: Path,
    relative: str,
    field: str,
    message: str,
) -> None:
    sample_root = tmp_path / "sample_tasks"
    task_dir = make_task(sample_root, "slugify", VALID_YAML)
    target = task_dir / relative
    if target.is_dir():
        shutil.rmtree(target)
    else:
        target.unlink()

    with pytest.raises(TaskValidationError) as caught:
        load_task(task_dir, sample_root=sample_root)

    err = caught.value
    assert err.field == field
    assert err.value is None
    assert err.message == message


def test_environment_file_is_rejected(tmp_path: Path) -> None:
    sample_root = tmp_path / "sample_tasks"
    task_dir = make_task(sample_root, "slugify", VALID_YAML)
    environment = task_dir / "environment"
    shutil.rmtree(environment)
    environment.write_text("not a directory\n", encoding="utf-8")

    with pytest.raises(TaskValidationError) as caught:
        load_task(task_dir, sample_root=sample_root)

    err = caught.value
    assert err.field == "environment"
    assert err.message == "expected a directory"
    assert err.value == str(environment.resolve())


def test_missing_pytest_file_names_the_pattern(tmp_path: Path) -> None:
    sample_root = tmp_path / "sample_tasks"
    task_dir = make_task(sample_root, "slugify", VALID_YAML)
    (task_dir / "tests" / "test_slugify.py").unlink()

    with pytest.raises(TaskValidationError) as caught:
        load_task(task_dir, sample_root=sample_root)

    err = caught.value
    assert err.field == "tests/test_*.py"
    assert err.value is None
    assert err.message == "required file is missing"


def test_missing_field_names_the_field(tmp_path: Path) -> None:
    yaml_text = """\
id: slugify
language: python
requirements:
  - id: R1
    text: Lowercase the text.
"""
    err = _load_error(tmp_path, "slugify", yaml_text)

    assert err.field == "title"
    assert err.value is None
    assert err.message == "required field is missing"


def test_wrong_field_type_names_the_value(tmp_path: Path) -> None:
    yaml_text = """\
id: slugify
title: 12
language: python
requirements:
  - id: R1
    text: Lowercase the text.
"""
    err = _load_error(tmp_path, "slugify", yaml_text)

    assert err.field == "title"
    assert err.value == 12
    assert err.message == "expected a string"


def test_unknown_field_names_the_value(tmp_path: Path) -> None:
    yaml_text = """\
id: slugify
title: Turn a phrase into a URL slug
language: python
owner: invented
requirements:
  - id: R1
    text: Lowercase the text.
"""
    err = _load_error(tmp_path, "slugify", yaml_text)

    assert err.field == "owner"
    assert err.value == "invented"
    assert err.message == "unknown field"


def test_non_python_language_names_the_value(tmp_path: Path) -> None:
    yaml_text = VALID_YAML.replace("language: python", "language: javascript")

    err = _load_error(tmp_path, "slugify", yaml_text)

    assert err.field == "language"
    assert err.value == "javascript"
    assert err.message == "must be 'python'"
    assert "javascript" in str(err)


def test_empty_requirements_names_the_value(tmp_path: Path) -> None:
    yaml_text = """\
id: slugify
title: Turn a phrase into a URL slug
language: python
requirements: []
"""
    err = _load_error(tmp_path, "slugify", yaml_text)

    assert err.field == "requirements"
    assert err.value == []
    assert err.message == "must not be empty"


def test_duplicate_requirement_id_names_the_later_value(tmp_path: Path) -> None:
    yaml_text = """\
id: slugify
title: Turn a phrase into a URL slug
language: python
requirements:
  - id: R1
    text: Lowercase the text.
  - id: R2
    text: Strip hyphens.
  - id: R1
    text: Repeated id.
"""
    err = _load_error(tmp_path, "slugify", yaml_text)

    assert err.field == "requirements[2].id"
    assert err.value == "R1"
    assert err.message == "duplicate requirement id"


def test_task_id_must_match_folder_name(tmp_path: Path) -> None:
    yaml_text = VALID_YAML.replace("id: slugify", "id: other-slug")

    err = _load_error(tmp_path, "slugify", yaml_text)

    assert err.field == "id"
    assert err.value == "other-slug"
    assert err.message == "does not match folder name 'slugify'"


def test_path_outside_sample_tasks_names_the_path(tmp_path: Path) -> None:
    sample_root = tmp_path / "sample_tasks"
    sample_root.mkdir()
    outside = tmp_path / "elsewhere"
    outside.mkdir()

    with pytest.raises(TaskValidationError) as caught:
        load_task(outside, sample_root=sample_root)

    err = caught.value
    assert err.field == "path"
    assert err.value == str(outside.resolve())
    assert err.message == "must be inside sample_tasks"


def test_symlink_that_escapes_sample_tasks_is_refused(tmp_path: Path) -> None:
    sample_root = tmp_path / "sample_tasks"
    sample_root.mkdir()
    outside = tmp_path / "outside-task"
    outside.mkdir()
    link = sample_root / "linked"
    link.symlink_to(outside, target_is_directory=True)

    with pytest.raises(TaskValidationError) as caught:
        load_task(link, sample_root=sample_root)

    err = caught.value
    assert err.field == "path"
    assert err.value == str(outside.resolve())
    assert err.message == "must be inside sample_tasks"


def test_nested_path_inside_sample_tasks_is_refused(tmp_path: Path) -> None:
    sample_root = tmp_path / "sample_tasks"
    task_dir = make_task(sample_root, "slugify", VALID_YAML)
    nested = task_dir / "solution"

    with pytest.raises(TaskValidationError) as caught:
        load_task(nested, sample_root=sample_root)

    err = caught.value
    assert err.field == "path"
    assert err.value == str(nested.resolve())
    assert err.message == "must be a direct child of sample_tasks"


def test_task_yaml_must_be_a_mapping(tmp_path: Path) -> None:
    err = _load_error(tmp_path, "slugify", "- just-a-list\n")

    assert err.field == "task.yaml"
    assert err.value == ["just-a-list"]
    assert err.message == "expected a mapping"


def test_invalid_yaml_names_the_parser_error(tmp_path: Path) -> None:
    err = _load_error(tmp_path, "slugify", "id: [\n")

    assert err.field == "task.yaml"
    assert err.message == "invalid YAML"
    assert isinstance(err.value, str)
    assert err.value


def _load_error(tmp_path: Path, folder: str, yaml_text: str) -> TaskValidationError:
    sample_root = tmp_path / "sample_tasks"
    task_dir = make_task(sample_root, folder, yaml_text)
    with pytest.raises(TaskValidationError) as caught:
        load_task(task_dir, sample_root=sample_root)
    return caught.value
