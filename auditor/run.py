"""Run checks 1 to 11 once and build a report.

Check 11 is measured once. Its survivors are the findings. This does not
change how any check decides.
"""

from auditor.checks import (
    measure_mutations,
    requirement_coverage,
    run_coverage_checks,
    run_dynamic_checks,
    run_static_checks,
    target_from_task,
)
from auditor.checks.model import Finding
from auditor.models import LoadedTask
from auditor.report import AuditReport, ReportFinding


def run_audit(task: LoadedTask) -> AuditReport:
    """Audit one loaded task folder."""
    target = target_from_task(task.root)
    findings: list[Finding] = []
    findings.extend(run_static_checks(target))
    findings.extend(run_coverage_checks(target))
    findings.extend(run_dynamic_checks(task.root))
    mutation = measure_mutations(task.root)
    findings.extend(mutation.survivors)
    return AuditReport(
        id=task.id,
        title=task.title,
        requirements=len(task.requirements),
        requirement_coverage=requirement_coverage(target),
        mutation_score=mutation.score,
        findings=[_report_finding(finding) for finding in findings],
    )


def _report_finding(finding: Finding) -> ReportFinding:
    return ReportFinding(
        check=finding.check,
        severity=finding.severity.value,
        location=finding.location,
        explanation=finding.explanation,
    )
