"""Registered checks. The audit command does not run these."""

from auditor.checks.brittle_format import run_brittle_format
from auditor.checks.coverage import (
    requirement_coverage,
    run_hidden_requirement,
    run_untested_requirement,
)
from auditor.checks.hardcoded import run_hardcoded_solution
from auditor.checks.model import Finding, Rule, Severity, Snippet, StaticTarget
from auditor.checks.nondeterministic import run_nondeterministic_test
from auditor.checks.source_inspection import run_source_inspection
from auditor.checks.target import target_from_task
from auditor.checks.weak_assertion import run_weak_assertion

CHECKS: tuple[Rule, ...] = (
    Rule("source_inspection_test", Severity.HIGH, run_source_inspection),
    Rule("weak_assertion", Severity.MEDIUM, run_weak_assertion),
    Rule("hardcoded_solution", Severity.HIGH, run_hardcoded_solution),
    Rule("brittle_format", Severity.MEDIUM, run_brittle_format),
    Rule("nondeterministic_test", Severity.LOW, run_nondeterministic_test),
)

COVERAGE_CHECKS: tuple[Rule, ...] = (
    Rule("untested_requirement", Severity.HIGH, run_untested_requirement),
    Rule("hidden_requirement", Severity.MEDIUM, run_hidden_requirement),
)


def run_static_checks(target: StaticTarget) -> list[Finding]:
    """Run checks 1 to 5. This does not execute the task's pytest file."""
    findings: list[Finding] = []
    for rule in CHECKS:
        findings.extend(rule.run(target))
    return findings


def run_coverage_checks(target: StaticTarget) -> list[Finding]:
    """Run checks 6 and 7. This does not import or run the task tests."""
    findings: list[Finding] = []
    for rule in COVERAGE_CHECKS:
        findings.extend(rule.run(target))
    return findings


__all__ = [
    "CHECKS",
    "COVERAGE_CHECKS",
    "Finding",
    "Rule",
    "Severity",
    "Snippet",
    "StaticTarget",
    "requirement_coverage",
    "run_coverage_checks",
    "run_static_checks",
    "target_from_task",
]
