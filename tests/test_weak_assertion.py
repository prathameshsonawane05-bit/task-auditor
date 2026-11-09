"""Snippet tests for weak_assertion."""

import pytest

from auditor.checks.model import Severity
from auditor.checks.weak_assertion import run_weak_assertion
from tests.check_support import assert_one_sentence, snippet_target

_POSITIVES: list[tuple[str, str]] = [
    (
        "def test_calls() -> None:\n    build()\n",
        "does not contain an assert",
    ),
    (
        "def test_always() -> None:\n    assert True\n",
        "assert True",
    ),
    (
        "def test_present() -> None:\n    assert build() is not None\n",
        "is not None",
    ),
    (
        "def test_kind() -> None:\n    assert isinstance(build(), int)\n",
        "isinstance",
    ),
    (
        "def test_swallows() -> None:\n"
        "    try:\n"
        "        build()\n"
        "    except Exception:\n"
        "        pass\n",
        "only passes",
    ),
]


@pytest.mark.parametrize(("source", "evidence"), _POSITIVES)
def test_weak_patterns_are_flagged(source: str, evidence: str) -> None:
    findings = run_weak_assertion(snippet_target(source))

    assert len(findings) == 1
    finding = findings[0]
    assert finding.check == "weak_assertion"
    assert finding.severity == Severity.MEDIUM
    assert evidence in finding.explanation
    assert_one_sentence(finding.explanation)


def test_real_equality_assert_is_not_flagged() -> None:
    source = "def test_add() -> None:\n    assert add(1, 1) == 2\n"
    assert run_weak_assertion(snippet_target(source)) == []


def test_real_assert_beside_assert_true_is_not_flagged() -> None:
    source = "def test_sum() -> None:\n    assert add(1, 1) == 2\n    assert True\n"
    assert run_weak_assertion(snippet_target(source)) == []


def test_reraise_is_not_flagged() -> None:
    source = (
        "def test_propagates() -> None:\n"
        "    try:\n"
        "        parse('')\n"
        "    except ValueError:\n"
        "        raise\n"
    )
    assert run_weak_assertion(snippet_target(source)) == []
