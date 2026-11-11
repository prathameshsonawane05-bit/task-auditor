"""JSON and Markdown reports for one audited task."""

import json
from pathlib import Path

from pydantic import BaseModel, ConfigDict, Field


class ReportFinding(BaseModel):
    """One finding as it appears in a report."""

    model_config = ConfigDict(extra="forbid")

    check: str = Field(min_length=1)
    severity: str = Field(min_length=1)
    location: str = Field(min_length=1)
    explanation: str = Field(min_length=1)


class AuditReport(BaseModel):
    """Findings, requirement coverage, and the mutation score for one task."""

    model_config = ConfigDict(extra="forbid")

    id: str = Field(min_length=1)
    title: str = Field(min_length=1)
    requirements: int = Field(ge=0)
    requirement_coverage: float
    mutation_score: float
    mutation_timed_out: int = Field(default=0, ge=0)
    findings: list[ReportFinding]


def report_json(report: AuditReport) -> str:
    """Return the report as pretty JSON."""
    payload = report.model_dump(mode="json")
    return json.dumps(payload, indent=2) + "\n"


def report_markdown(report: AuditReport) -> str:
    """Return the report as Markdown."""
    lines = [
        f"# {report.id}",
        "",
        f"title: {report.title}",
        f"requirements: {report.requirements}",
        f"requirement_coverage: {report.requirement_coverage:.3f}",
        f"mutation_score: {report.mutation_score:.3f}",
        f"mutation_timed_out: {report.mutation_timed_out}",
        "",
        "## Findings",
        "",
    ]
    if not report.findings:
        lines.append("No findings.")
    else:
        for finding in report.findings:
            lines.append(f"- check: {finding.check}")
            lines.append(f"  severity: {finding.severity}")
            lines.append(f"  location: {finding.location}")
            lines.append(f"  explanation: {finding.explanation}")
            lines.append("")
    text = "\n".join(lines).rstrip()
    return text + "\n"


def write_reports(report: AuditReport, out_dir: Path) -> tuple[Path, Path]:
    """Write `<id>.json` and `<id>.md` and return both paths."""
    out_dir.mkdir(parents=True, exist_ok=True)
    json_path = out_dir / f"{report.id}.json"
    markdown_path = out_dir / f"{report.id}.md"
    json_path.write_text(report_json(report), encoding="utf-8")
    markdown_path.write_text(report_markdown(report), encoding="utf-8")
    return json_path, markdown_path
