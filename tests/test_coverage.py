"""Snippet tests for coverage checks 6 and 7."""

from pathlib import Path

from auditor.checks import (
    COVERAGE_CHECKS,
    Severity,
    requirement_coverage,
    run_coverage_checks,
    run_static_checks,
    target_from_task,
)
from auditor.checks.coverage import run_hidden_requirement, run_untested_requirement
from auditor.loader import load_task
from tests.check_support import assert_one_sentence, snippet_target

REPO = Path(__file__).resolve().parents[1]
_REQUIREMENTS = ("R1", "R2")

_BOTH_DECORATORS = """\
@covers("R2")
@covers("R1")
def test_both() -> None:
    assert missing() == 1
"""

_ONE_DECORATOR = """\
@covers("R1")
def test_one() -> None:
    assert missing() == 1
"""

_NO_DECORATOR = """\
def test_plain() -> None:
    assert 1 == 1
"""

_ALIAS = """\
from conftest import covers as mark

@mark("R1")
@mark("R2")
def test_both() -> None:
    assert 1 == 1
"""


def test_coverage_checks_are_registered() -> None:
    assert [rule.name for rule in COVERAGE_CHECKS] == [
        "untested_requirement",
        "hidden_requirement",
    ]
    assert [rule.severity for rule in COVERAGE_CHECKS] == [
        Severity.HIGH,
        Severity.MEDIUM,
    ]


def test_untested_requirement_names_the_missing_id() -> None:
    findings = run_untested_requirement(
        snippet_target(_ONE_DECORATOR, requirements=_REQUIREMENTS)
    )

    assert len(findings) == 1
    assert findings[0].check == "untested_requirement"
    assert findings[0].severity == Severity.HIGH
    assert "R2" in findings[0].explanation
    assert_one_sentence(findings[0].explanation)


def test_covered_requirements_are_not_flagged_as_untested() -> None:
    source = """\
@covers("R1")
def test_first() -> None:
    assert 1 == 1

@covers("R2")
def test_second() -> None:
    assert 2 == 2
"""
    findings = run_untested_requirement(
        snippet_target(source, requirements=_REQUIREMENTS)
    )
    assert findings == []


def test_two_decorators_on_one_test_cover_both_ids() -> None:
    """The runtime attribute would keep one id. The source lists both."""
    target = snippet_target(_BOTH_DECORATORS, requirements=_REQUIREMENTS)

    assert run_untested_requirement(target) == []
    assert requirement_coverage(target) == 2 / 2


def test_alias_of_covers_is_not_recognized() -> None:
    target = snippet_target(_ALIAS, requirements=_REQUIREMENTS)

    untested = run_untested_requirement(target)
    hidden = run_hidden_requirement(target)
    assert [finding.explanation for finding in untested] == [
        "Requirement R1 has no @covers marker.",
        "Requirement R2 has no @covers marker.",
    ]
    assert any("no @covers marker" in finding.explanation for finding in hidden)
    assert requirement_coverage(target) == 0 / 2


def test_test_without_covers_is_hidden() -> None:
    findings = run_hidden_requirement(
        snippet_target(_NO_DECORATOR, requirements=_REQUIREMENTS)
    )

    assert len(findings) == 1
    assert findings[0].check == "hidden_requirement"
    assert findings[0].severity == Severity.MEDIUM
    assert "test_plain" in findings[0].explanation
    assert_one_sentence(findings[0].explanation)


def test_unknown_covers_id_is_hidden() -> None:
    source = """\
@covers("R9")
def test_secret() -> None:
    assert 1 == 1
"""
    findings = run_hidden_requirement(
        snippet_target(source, requirements=_REQUIREMENTS)
    )

    assert len(findings) == 1
    assert "R9" in findings[0].explanation
    assert_one_sentence(findings[0].explanation)


def test_ordinary_equality_is_not_a_hidden_error() -> None:
    source = """\
@covers("R1")
def test_output() -> None:
    assert slugify("Hi") == "hi"
    assert str(result) == "hi"
"""
    findings = run_hidden_requirement(
        snippet_target(source, requirements=("R1",), instruction="")
    )
    assert findings == []


def test_pytest_raises_match_absent_from_the_instruction_is_flagged() -> None:
    source = """\
@covers("R1")
def test_bad() -> None:
    with pytest.raises(ValueError, match="not a slug"):
        slugify("")
"""
    findings = run_hidden_requirement(
        snippet_target(source, requirements=("R1",), instruction="Make a slug.")
    )

    assert len(findings) == 1
    assert "not a slug" in findings[0].explanation
    assert "pytest.raises" in findings[0].explanation
    assert_one_sentence(findings[0].explanation)


def test_same_error_message_is_not_flagged_when_the_instruction_contains_it() -> None:
    source = """\
@covers("R1")
def test_bad() -> None:
    with pytest.raises(ValueError, match="not a slug"):
        slugify("")
    try:
        slugify("")
    except ValueError as exc:
        assert str(exc) == "not a slug"
"""
    findings = run_hidden_requirement(
        snippet_target(
            source,
            requirements=("R1",),
            instruction="Reject an empty phrase with not a slug.",
        )
    )
    assert findings == []


def test_exception_string_equality_absent_from_the_instruction_is_flagged() -> None:
    source = """\
@covers("R1")
def test_bad() -> None:
    try:
        slugify("")
    except ValueError as exc:
        assert str(exc) == "not a slug"
"""
    findings = run_hidden_requirement(
        snippet_target(source, requirements=("R1",), instruction="")
    )

    assert len(findings) == 1
    assert "not a slug" in findings[0].explanation
    assert_one_sentence(findings[0].explanation)


def test_coverage_is_zero_one_and_two_of_two() -> None:
    none = snippet_target(_NO_DECORATOR, requirements=_REQUIREMENTS)
    one = snippet_target(_ONE_DECORATOR, requirements=_REQUIREMENTS)
    both = snippet_target(_BOTH_DECORATORS, requirements=_REQUIREMENTS)

    assert requirement_coverage(none) == 0 / 2
    assert requirement_coverage(one) == 1 / 2
    assert requirement_coverage(both) == 2 / 2


def test_zero_requirements_uses_zero() -> None:
    target = snippet_target(_ONE_DECORATOR, requirements=())

    assert requirement_coverage(target) == 0.0
    hidden = run_hidden_requirement(target)
    assert any("R1" in finding.explanation for finding in hidden)


def test_slugify_sample_covers_both_requirements() -> None:
    task = load_task(REPO / "sample_tasks" / "slugify")
    target = target_from_task(task.root)

    assert target.requirements == ("R1", "R2")
    assert run_coverage_checks(target) == []
    assert requirement_coverage(target) == 2 / 2


def test_static_runner_does_not_run_coverage_checks() -> None:
    target = snippet_target(_NO_DECORATOR, requirements=_REQUIREMENTS)
    findings = run_static_checks(target)

    assert run_untested_requirement(target)
    assert all(finding.check != "untested_requirement" for finding in findings)
    assert all(finding.check != "hidden_requirement" for finding in findings)


def test_coverage_module_does_not_import_or_run_tests() -> None:
    source = (REPO / "auditor" / "checks" / "coverage.py").read_text(encoding="utf-8")
    assert "importlib" not in source
    assert "subprocess" not in source
    assert "exec(" not in source
