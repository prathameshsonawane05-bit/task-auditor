"""Build a static-check target from a task directory."""

from pathlib import Path

import yaml

from auditor.checks.model import Snippet, StaticTarget


def target_from_task(root: Path) -> StaticTarget:
    """Read instruction, solution, tests, and requirement ids.

    This parses source text and task.yaml. It does not import or run tests.
    A task.yaml that is missing or not a mapping contributes no ids, and the
    coverage percentage for that target is 0.0.
    """
    instruction_path = root / "instruction.md"
    instruction = ""
    if instruction_path.is_file():
        instruction = instruction_path.read_text(encoding="utf-8")
    solution_path = root / "solution" / "solution.py"
    solution = None
    if solution_path.is_file():
        solution = Snippet(
            "solution/solution.py",
            solution_path.read_text(encoding="utf-8"),
        )
    tests = tuple(
        Snippet(f"tests/{path.name}", path.read_text(encoding="utf-8"))
        for path in sorted((root / "tests").glob("test_*.py"))
    )
    return StaticTarget(
        tests=tests,
        solution=solution,
        instruction=instruction,
        requirements=_requirement_ids(root),
    )


def _requirement_ids(root: Path) -> tuple[str, ...]:
    path = root / "task.yaml"
    if not path.is_file():
        return ()
    try:
        loaded: object = yaml.safe_load(path.read_text(encoding="utf-8"))
    except yaml.YAMLError:
        return ()
    if not isinstance(loaded, dict):
        return ()
    raw = loaded.get("requirements")
    if not isinstance(raw, list):
        return ()
    ids: list[str] = []
    for item in raw:
        if not isinstance(item, dict):
            continue
        value = item.get("id")
        if isinstance(value, str) and value:
            ids.append(value)
    return tuple(ids)
