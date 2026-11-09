"""Command line interface for TaskAuditor."""

from pathlib import Path

import typer

from auditor.errors import TaskValidationError
from auditor.loader import load_task

app = typer.Typer(add_completion=False, no_args_is_help=True)

_WARNING = "warning: later stages run task code and this is not a security sandbox"


@app.callback()
def main() -> None:
    """Validate invented coding-task folders."""


@app.command()
def audit(path: Path) -> None:
    """Validate a task folder under sample_tasks. Does not run its tests."""
    typer.echo(_WARNING, err=True)
    try:
        task = load_task(path)
    except TaskValidationError as exc:
        typer.echo(f"error: {exc}", err=True)
        raise typer.Exit(code=1) from None
    typer.echo(f"id: {task.id}")
    typer.echo(f"title: {task.title}")
    typer.echo(f"requirements: {len(task.requirements)}")
