"""Snippet tests for source_inspection_test."""

from auditor.checks.model import Severity
from auditor.checks.source_inspection import run_source_inspection
from tests.check_support import assert_one_sentence, snippet_target

POSITIVE = """\
import ast

def test_reads_solution() -> None:
    path = "solution/solution.py"
    source = open(path).read()
    tree = ast.parse(source)
    assert "return" in source
    assert tree is not None
"""

NEGATIVE = """\
def test_reads_notes() -> None:
    notes = open("notes.txt").read()
    assert "hello" in notes
    assert len(notes) >= 0
"""

EDGE = """\
import inspect as ins

def solve(value: str) -> str:
    return value

def test_reads_source() -> None:
    text = ins.getsource(solve)
    assert "return" in text
"""


def test_open_parse_and_membership_on_the_solution_are_flagged() -> None:
    findings = run_source_inspection(snippet_target(POSITIVE))

    explanations = [finding.explanation for finding in findings]
    assert any("calls open on 'solution/solution.py'" in text for text in explanations)
    assert any("ast.parse" in text for text in explanations)
    assert any("membership" in text for text in explanations)
    for finding in findings:
        assert finding.check == "source_inspection_test"
        assert finding.severity == Severity.HIGH
        assert_one_sentence(finding.explanation)


def test_open_of_a_non_solution_path_is_ignored() -> None:
    assert run_source_inspection(snippet_target(NEGATIVE)) == []


def test_reassigned_path_is_not_treated_as_the_solution() -> None:
    source = """\
def test_opens_other(other: str) -> None:
    path = "solution/solution.py"
    path = other
    open(path).read()
"""
    assert run_source_inspection(snippet_target(source)) == []


def test_aliased_inspect_getsource_is_flagged() -> None:
    findings = run_source_inspection(snippet_target(EDGE))

    assert any("ins.getsource" in finding.explanation for finding in findings)
    for finding in findings:
        assert finding.check == "source_inspection_test"
        assert finding.severity == Severity.HIGH
        assert_one_sentence(finding.explanation)
