"""Snippet tests for hardcoded_solution."""

import time

import pytest

from auditor.checks.hardcoded import run_hardcoded_solution
from auditor.checks.model import Severity
from tests.check_support import assert_one_sentence, snippet_target

GUARD = """\
import os
if os.environ.get("AUDITOR_IN_PROCESS") == "1":
    raise RuntimeError("imported in the auditor process")

"""

LITERAL_SOLUTION = (
    GUARD
    + """\
def answer(value: str) -> str:
    return "fixed"
"""
)

LITERAL_TEST = """\
def test_answer() -> None:
    assert answer("z") == "fixed"
"""

COMPUTED_SOLUTION = (
    GUARD
    + """\
def add(left: int, right: int) -> int:
    return left + right
"""
)

COMPUTED_TEST = """\
def test_add() -> None:
    assert add(1, 2) == 3
"""

CHAIN_SOLUTION = (
    GUARD
    + """\
def label(code: str) -> str:
    if code == "a":
        return "alpha"
    elif code == "b":
        return "beta"
    return "other"
"""
)

CHAIN_TEST = """\
def test_label() -> None:
    assert label("a") == "alpha"
"""

NO_ARG_SOLUTION = (
    GUARD
    + """\
def answer() -> str:
    return "fixed"
"""
)

NO_ARG_TEST = """\
def test_answer() -> None:
    assert answer() == "fixed"
"""

TIMEOUT_SOLUTION = (
    GUARD
    + """\
import time

def answer(value: str) -> str:
    time.sleep(30)
    return "fixed"
"""
)


@pytest.fixture(autouse=True)
def mark_auditor_process(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("AUDITOR_IN_PROCESS", "1")


def test_literal_return_is_confirmed_on_a_perturbed_input() -> None:
    findings = run_hardcoded_solution(
        snippet_target(LITERAL_TEST, solution=LITERAL_SOLUTION)
    )

    assert len(findings) == 1
    finding = findings[0]
    assert finding.check == "hardcoded_solution"
    assert finding.severity == Severity.HIGH
    assert "answer('zq')" in finding.explanation
    assert "'fixed'" in finding.explanation
    assert_one_sentence(finding.explanation)


def test_computed_return_is_not_flagged() -> None:
    findings = run_hardcoded_solution(
        snippet_target(COMPUTED_TEST, solution=COMPUTED_SOLUTION)
    )
    assert findings == []


def test_if_chain_on_literals_is_flagged_when_perturbation_changes() -> None:
    findings = run_hardcoded_solution(
        snippet_target(CHAIN_TEST, solution=CHAIN_SOLUTION)
    )

    assert len(findings) == 1
    explanation = findings[0].explanation
    assert "label('aq')" in explanation
    assert "'alpha'" in explanation
    assert "'other'" in explanation
    assert_one_sentence(explanation)


def test_literal_return_with_no_arguments_is_flagged() -> None:
    findings = run_hardcoded_solution(
        snippet_target(NO_ARG_TEST, solution=NO_ARG_SOLUTION)
    )

    assert len(findings) == 1
    assert "no input to perturb" in findings[0].explanation
    assert_one_sentence(findings[0].explanation)


def test_subprocess_timeout_does_not_flag(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr("auditor.checks.sandbox.SUBPROCESS_TIMEOUT_SECONDS", 0.5)
    started = time.monotonic()
    findings = run_hardcoded_solution(
        snippet_target(LITERAL_TEST, solution=TIMEOUT_SOLUTION)
    )
    elapsed = time.monotonic() - started

    assert findings == []
    assert elapsed < 5
    assert elapsed >= 0.3
