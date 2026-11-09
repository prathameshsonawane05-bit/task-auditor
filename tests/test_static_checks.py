"""Registry and sample-task checks. The audit command stays validation-only."""

from pathlib import Path

from auditor.checks import CHECKS, Severity, run_static_checks, target_from_task
from auditor.loader import load_task
from tests.check_support import snippet_target

REPO = Path(__file__).resolve().parents[1]


def test_static_checks_are_registered() -> None:
    assert [rule.name for rule in CHECKS] == [
        "source_inspection_test",
        "weak_assertion",
        "hardcoded_solution",
        "brittle_format",
        "nondeterministic_test",
    ]
    assert [rule.severity for rule in CHECKS] == [
        Severity.HIGH,
        Severity.MEDIUM,
        Severity.HIGH,
        Severity.MEDIUM,
        Severity.LOW,
    ]


def test_run_static_checks_invokes_the_registry() -> None:
    source = "def test_reads() -> None:\n    open('solution.py')\n"
    findings = run_static_checks(snippet_target(source))
    assert any(finding.check == "source_inspection_test" for finding in findings)


def test_slugify_sample_has_no_static_findings() -> None:
    task = load_task(REPO / "sample_tasks" / "slugify")
    assert run_static_checks(target_from_task(task.root)) == []
