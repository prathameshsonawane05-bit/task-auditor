"""Check 11, surviving mutants. Snippets are invented and same-author."""

import ast
from pathlib import Path

import pytest

from auditor.checks.dynamic import DYNAMIC_CHECKS, run_dynamic_checks, run_suite_source
from auditor.checks.model import Severity
from auditor.checks.mutation import (
    MUTATION_CAP,
    MUTATION_CHECKS,
    MUTATION_SEED,
    _constant_sites,
    _render,
    build_mutants,
    measure_mutations,
    mutation_score,
    run_surviving_mutants,
)
from tests.check_support import assert_one_sentence

REPO = Path(__file__).resolve().parents[1]
SLUGIFY = REPO / "sample_tasks" / "slugify"

_POSITIVE = "def is_positive(n: int) -> bool:\n    return n > 0\n"
_POSITIVE_TESTS = """\
from sign import is_positive

def test_one() -> None:
    assert is_positive(1) is True

def test_zero() -> None:
    assert is_positive(0) is False

def test_negative() -> None:
    assert is_positive(-1) is False
"""
_COUNTDOWN = """\
def countdown(n: int) -> int:
    while n > 0:
        n = n - 1
    return n
"""
_COUNTDOWN_TESTS = """\
from countdown import countdown

def test_two() -> None:
    assert countdown(2) == 0
"""


def _write_task(
    root: Path,
    *,
    module: str,
    solution: str,
    tests: str,
    test_name: str,
) -> None:
    (root / "environment").mkdir(parents=True)
    (root / "solution").mkdir(parents=True)
    (root / "tests").mkdir(parents=True)
    starter = "def unused() -> None:\n    raise NotImplementedError\n"
    (root / "environment" / f"{module}.py").write_text(starter, encoding="utf-8")
    (root / "solution" / "solution.py").write_text(solution, encoding="utf-8")
    (root / "tests" / test_name).write_text(tests, encoding="utf-8")


def _snapshot(root: Path) -> dict[str, bytes]:
    return {
        str(path.relative_to(root)): path.read_bytes()
        for path in sorted(root.rglob("*"))
        if path.is_file()
    }


def test_mutation_checks_stay_outside_checks_8_to_10() -> None:
    assert [rule.name for rule in DYNAMIC_CHECKS] == [
        "solution_fails_tests",
        "cheat_solution_passes",
        "flaky_tests",
    ]
    assert [rule.name for rule in MUTATION_CHECKS] == ["surviving_mutants"]
    assert MUTATION_CHECKS[0].severity == Severity.HIGH
    assert MUTATION_SEED == 11
    assert MUTATION_CAP == 48


def test_operator_map_and_bools_and_branches() -> None:
    source = (
        "def f(n: int, flag: bool) -> int:\n"
        "    if n > 0 and flag:\n"
        "        return 1\n"
        "    else:\n"
        "        return True\n"
    )
    mutants, excluded, sampled = build_mutants(source)
    descriptions = [mutant.description for mutant in mutants]

    assert "flipping > to <=" in descriptions
    assert "swapping and for or" in descriptions
    assert "deleting the if branch" in descriptions
    assert "deleting the else branch" in descriptions
    assert "changing constant 1 to 2" in descriptions
    assert "changing constant 1 to 0" in descriptions
    assert not any("True" in description for description in descriptions)
    assert not any("False" in description for description in descriptions)
    assert excluded == 0
    assert sampled is False


def test_each_comparison_flips_once() -> None:
    source = (
        "def f(a: int, b: int, c: object, items: list[int]) -> bool:\n"
        "    return a == b or a != b or a < b or a <= b or a > b or a >= b "
        "or c is b or c is not b or a in items or a not in items\n"
    )
    mutants, _excluded, _sampled = build_mutants(source)
    descriptions = {mutant.description for mutant in mutants}
    assert descriptions >= {
        "flipping == to !=",
        "flipping != to ==",
        "flipping < to >=",
        "flipping <= to >",
        "flipping > to <=",
        "flipping >= to <",
        "flipping is to is not",
        "flipping is not to is",
        "flipping in to not in",
        "flipping not in to in",
        "swapping or for and",
    }


def test_float_and_negative_constants_move_by_one() -> None:
    source = "def f() -> float:\n    return 1.5 + -2\n"
    mutants, excluded, _sampled = build_mutants(source)
    descriptions = {mutant.description for mutant in mutants}
    assert descriptions == {
        "changing constant 1.5 to 2.5",
        "changing constant 1.5 to 0.5",
        "changing constant 2 to 3",
        "changing constant 2 to 1",
    }
    stored = [label for label, _apply in _constant_sites(ast.Constant(value=-2))]
    assert stored == [
        "changing constant -2 to -1",
        "changing constant -2 to -3",
    ]
    assert list(_constant_sites(ast.Constant(value=True))) == []
    assert list(_constant_sites(ast.Constant(value=False))) == []
    assert excluded == 0


def test_if_expression_deletes_one_side() -> None:
    source = "def f(flag: bool) -> int:\n    return 1 if flag else 0\n"
    mutants, _excluded, _sampled = build_mutants(source)
    bodies = [mutant.source for mutant in mutants]
    assert any("return 0" in body and "else" not in body for body in bodies)
    assert any("return 1" in body and "else" not in body for body in bodies)


def test_cap_and_seed_keep_the_same_subset() -> None:
    lines = ["def f() -> int:", "    total = 0"]
    lines.extend(f"    total = total + {index}" for index in range(30))
    lines.append("    return total")
    source = "\n".join(lines) + "\n"
    first, excluded, sampled = build_mutants(source, seed=11, cap=2)
    second, _, _ = build_mutants(source, seed=11, cap=2)
    assert first == second
    assert len(first) == 2
    assert excluded == 0
    assert sampled is True
    full, _, full_sampled = build_mutants(source, seed=11, cap=48)
    assert full_sampled is True
    assert len(full) == 48


def test_unparseable_text_is_excluded(monkeypatch: pytest.MonkeyPatch) -> None:
    def broken(_tree: ast.AST) -> str:
        return "def ("

    monkeypatch.setattr("auditor.checks.mutation._render", broken)
    mutants, excluded, sampled = build_mutants("def f() -> int:\n    return 1\n")
    assert mutants == ()
    assert excluded == 2
    assert sampled is False


def test_render_rejects_a_tree_that_does_not_parse() -> None:
    tree = ast.Module(
        body=[ast.Expr(value=ast.Name(id="not an id", ctx=ast.Load()))],
        type_ignores=[],
    )
    assert _render(tree) is None


def test_score_is_zero_when_there_are_no_mutants() -> None:
    assert mutation_score(0, 0) == 0.0
    assert mutation_score(1, 2) == 0.5
    missing = measure_mutations(Path("/this/path/is/not/a/task"))
    assert missing.score == 0.0
    assert missing.total == 0
    assert missing.survivors == ()


def test_auditor_does_not_import_or_exec_the_solution() -> None:
    source = (REPO / "auditor" / "checks" / "mutation.py").read_text(encoding="utf-8")
    assert "importlib" not in source
    assert "exec(" not in source


def test_slugify_mutation_score_is_stable_and_files_stay() -> None:
    before = _snapshot(SLUGIFY)

    report = measure_mutations(SLUGIFY)

    assert (report.killed, report.total, report.excluded) == (3, 3, 0)
    assert report.score == 1.0
    assert report.sampled is False
    assert report.survivors == ()
    assert report.total == report.killed + len(report.survivors)
    mutants, excluded, sampled = build_mutants(
        (SLUGIFY / "solution" / "solution.py").read_text(encoding="utf-8")
    )
    assert excluded == 0
    assert sampled is False
    assert [(mutant.line, mutant.description) for mutant in mutants] == [
        (5, "deleting the if branch"),
        (5, "deleting the else branch"),
        (8, "deleting the if branch"),
    ]
    assert _snapshot(SLUGIFY) == before
    assert run_dynamic_checks(SLUGIFY) == []
    again = measure_mutations(SLUGIFY)
    assert again == report


def test_positive_tests_kill_every_mutant(tmp_path: Path) -> None:
    root = tmp_path / "sign"
    _write_task(
        root,
        module="sign",
        solution=_POSITIVE,
        tests=_POSITIVE_TESTS,
        test_name="test_sign.py",
    )

    report = measure_mutations(root)

    assert report.excluded == 0
    assert report.total > 0
    assert report.survivors == ()
    assert report.killed == report.total
    assert report.score == 1.0


def test_weak_countdown_leaves_a_survivor_and_kills_a_timeout(
    tmp_path: Path,
) -> None:
    root = tmp_path / "countdown"
    _write_task(
        root,
        module="countdown",
        solution=_COUNTDOWN,
        tests=_COUNTDOWN_TESTS,
        test_name="test_countdown.py",
    )

    mutants, _excluded, _sampled = build_mutants(_COUNTDOWN)
    assert not any("deleting" in mutant.description for mutant in mutants)

    report = measure_mutations(root)
    survivor_text = " ".join(finding.explanation for finding in report.survivors)

    assert (report.killed, report.total, report.excluded) == (4, 5, 0)
    assert report.score == mutation_score(4, 5)
    assert len(report.survivors) == 1
    assert "changing constant 1 to 2" in survivor_text
    assert "changing constant 1 to 0" not in survivor_text
    assert report.survivors[0].location == "solution/solution.py:3"
    assert report.survivors[0].severity == Severity.HIGH
    assert MUTATION_CHECKS[0].run is run_surviving_mutants
    timeout = next(
        mutant for mutant in mutants if mutant.description == "changing constant 1 to 0"
    )
    timed = run_suite_source(root, timeout.source)
    assert timed.timed_out
    assert timed.passed is False
    for finding in report.survivors:
        assert_one_sentence(finding.explanation)
