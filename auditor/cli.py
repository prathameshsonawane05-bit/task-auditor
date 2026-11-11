"""Command line interface for TaskAuditor."""

from pathlib import Path
from typing import Annotated

import typer

from auditor.errors import TaskValidationError
from auditor.loader import load_task
from auditor.report import write_reports
from auditor.run import run_audit

app = typer.Typer(add_completion=False, no_args_is_help=True)

_WARNING = "warning: this command runs task code and is not a security sandbox"


@app.callback()
def main() -> None:
    """Audit invented coding-task folders."""


@app.command()
def audit(
    path: Path,
    out: Annotated[
        Path | None,
        typer.Option("--out", help="Directory for the JSON and Markdown reports."),
    ] = None,
) -> None:
    """Run checks 1 to 11 and write JSON and Markdown reports."""
    destination = Path("reports") if out is None else out
    typer.echo(_WARNING, err=True)
    try:
        task = load_task(path)
    except TaskValidationError as exc:
        typer.echo(f"error: {exc}", err=True)
        raise typer.Exit(code=1) from None
    report = run_audit(task)
    try:
        json_path, markdown_path = write_reports(report, destination)
    except OSError as exc:
        typer.echo(f"error: out: {exc}", err=True)
        raise typer.Exit(code=1) from None
    typer.echo(f"id: {report.id}")
    typer.echo(f"title: {report.title}")
    typer.echo(f"requirements: {report.requirements}")
    typer.echo(f"requirement_coverage: {report.requirement_coverage:.3f}")
    typer.echo(f"mutation_score: {report.mutation_score:.3f}")
    typer.echo(f"mutation_timed_out: {report.mutation_timed_out}")
    typer.echo(f"findings: {len(report.findings)}")
    typer.echo(f"json: {json_path}")
    typer.echo(f"markdown: {markdown_path}")
