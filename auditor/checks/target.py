"""Build a static-check target from a task directory."""

from pathlib import Path

from auditor.checks.model import Snippet, StaticTarget


def target_from_task(root: Path) -> StaticTarget:
    """Read instruction, solution, and test_*.py files. Does not run them."""
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
    return StaticTarget(tests=tests, solution=solution, instruction=instruction)
