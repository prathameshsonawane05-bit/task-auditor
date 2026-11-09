"""Helpers for static-check snippet tests."""

from auditor.checks.model import Snippet, StaticTarget


def snippet_target(
    test_source: str,
    *,
    solution: str | None = None,
    instruction: str = "",
    test_label: str = "tests/test_snippet.py",
    solution_label: str = "solution/solution.py",
) -> StaticTarget:
    solution_snippet = None
    if solution is not None:
        solution_snippet = Snippet(solution_label, solution)
    return StaticTarget(
        tests=(Snippet(test_label, test_source),),
        solution=solution_snippet,
        instruction=instruction,
    )


def assert_one_sentence(text: str) -> None:
    assert "\n" not in text
    assert text.endswith(".")
    assert ". " not in text
