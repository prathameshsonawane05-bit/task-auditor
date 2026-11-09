"""Build tiny invented task folders for loader tests."""

from pathlib import Path

VALID_YAML = """\
id: slugify
title: Turn a phrase into a URL slug
language: python
requirements:
  - id: R1
    text: Lowercase the text and collapse separators into one hyphen.
  - id: R2
    text: Strip leading and trailing hyphens.
"""


def make_task(sample_root: Path, folder: str, yaml_text: str) -> Path:
    """Create a task directory with the stage-1 file layout."""
    task_dir = sample_root / folder
    environment = task_dir / "environment"
    solution = task_dir / "solution"
    tests = task_dir / "tests"
    environment.mkdir(parents=True)
    solution.mkdir(parents=True)
    tests.mkdir(parents=True)
    (environment / "slugify.py").write_text(
        "def slugify(text: str) -> str:\n    raise NotImplementedError\n",
        encoding="utf-8",
    )
    (solution / "solution.py").write_text(
        "def slugify(text: str) -> str:\n    return text\n",
        encoding="utf-8",
    )
    (tests / "test_slugify.py").write_text(
        "def test_slugify() -> None:\n    assert slugify('A') == 'a'\n",
        encoding="utf-8",
    )
    (task_dir / "instruction.md").write_text("# Slugify\n", encoding="utf-8")
    (task_dir / "task.yaml").write_text(yaml_text, encoding="utf-8")
    return task_dir
