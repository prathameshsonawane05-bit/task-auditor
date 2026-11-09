"""Snippet tests for brittle_format."""

from auditor.checks.brittle_format import LONG_STRING_MIN_LENGTH, run_brittle_format
from auditor.checks.model import Severity
from tests.check_support import assert_one_sentence, snippet_target

LONG = "w" * 40
SHORT = "w" * 39
INSTRUCTION = "Write render() so that it describes an invented receipt.\n"


def _source(literal: str) -> str:
    return f"def test_receipt() -> None:\n    assert render() == {literal!r}\n"


def test_cutoff_is_40_characters() -> None:
    assert LONG_STRING_MIN_LENGTH == 40
    assert len(LONG) == 40
    assert len(SHORT) == 39


def test_long_string_equality_without_a_specified_format_is_flagged() -> None:
    findings = run_brittle_format(
        snippet_target(_source(LONG), instruction=INSTRUCTION)
    )

    assert len(findings) == 1
    finding = findings[0]
    assert finding.check == "brittle_format"
    assert finding.severity == Severity.MEDIUM
    assert "40-character" in finding.explanation
    assert "==" in finding.explanation
    assert_one_sentence(finding.explanation)


def test_numeric_equality_is_not_flagged() -> None:
    source = "def test_total() -> None:\n    assert render() == 3\n"
    findings = run_brittle_format(snippet_target(source, instruction=INSTRUCTION))
    assert findings == []


def test_same_literal_is_not_flagged_when_the_instruction_specifies_it() -> None:
    instruction = f"The output format is exactly {LONG}.\n"
    findings = run_brittle_format(
        snippet_target(_source(LONG), instruction=instruction)
    )
    assert findings == []


def test_short_string_equality_is_not_flagged() -> None:
    findings = run_brittle_format(
        snippet_target(_source(SHORT), instruction=INSTRUCTION)
    )
    assert findings == []
