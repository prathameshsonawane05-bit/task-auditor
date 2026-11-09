"""Report text, without running the checks."""

from auditor.report import AuditReport, ReportFinding, report_json, report_markdown


def test_markdown_lists_each_finding_field_and_both_scores() -> None:
    report = AuditReport(
        id="box",
        title="Read a box label",
        requirements=1,
        requirement_coverage=1.0,
        mutation_score=0.5,
        findings=[
            ReportFinding(
                check="weak_assertion",
                severity="medium",
                location="tests/test_box.py:4",
                explanation="The test does not contain an assert.",
            )
        ],
    )

    text = report_markdown(report)
    payload = report_json(report)

    assert "requirement_coverage: 1.000" in text
    assert "mutation_score: 0.500" in text
    assert "check: weak_assertion" in text
    assert "severity: medium" in text
    assert "location: tests/test_box.py:4" in text
    assert "explanation: The test does not contain an assert." in text
    assert '"requirement_coverage": 1.0' in payload
    assert '"mutation_score": 0.5' in payload
    assert '"check": "weak_assertion"' in payload


def test_markdown_says_when_a_task_has_no_findings() -> None:
    report = AuditReport(
        id="slugify",
        title="Turn a phrase into a URL slug",
        requirements=2,
        requirement_coverage=1.0,
        mutation_score=1.0,
        findings=[],
    )

    text = report_markdown(report)

    assert "No findings." in text
    assert "requirement_coverage: 1.000" in text
    assert "mutation_score: 1.000" in text
