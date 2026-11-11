"""SQLite storage for audit reports. The database file is not source."""

import json
import sqlite3
from collections.abc import Iterator
from contextlib import contextmanager
from pathlib import Path

from auditor.report import AuditReport, ReportFinding

_SCHEMA = """
CREATE TABLE IF NOT EXISTS audits (
    task_id TEXT PRIMARY KEY,
    title TEXT NOT NULL,
    requirements INTEGER NOT NULL,
    requirement_coverage REAL NOT NULL,
    mutation_score REAL NOT NULL,
    mutation_timed_out INTEGER NOT NULL DEFAULT 0,
    findings_json TEXT NOT NULL
)
"""


def project_database_path() -> Path:
    """Return the default database path beside pyproject.toml."""
    here = Path(__file__).resolve()
    for parent in here.parents:
        if (parent / "pyproject.toml").is_file():
            return parent / "auditor.sqlite"
    return Path("auditor.sqlite")


def save_report(database: Path, report: AuditReport) -> None:
    """Insert or replace one report."""
    findings = json.dumps([item.model_dump(mode="json") for item in report.findings])
    with _connect(database) as connection:
        connection.execute(
            """
            INSERT INTO audits (
                task_id, title, requirements, requirement_coverage,
                mutation_score, mutation_timed_out, findings_json
            ) VALUES (?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(task_id) DO UPDATE SET
                title = excluded.title,
                requirements = excluded.requirements,
                requirement_coverage = excluded.requirement_coverage,
                mutation_score = excluded.mutation_score,
                mutation_timed_out = excluded.mutation_timed_out,
                findings_json = excluded.findings_json
            """,
            (
                report.id,
                report.title,
                report.requirements,
                report.requirement_coverage,
                report.mutation_score,
                report.mutation_timed_out,
                findings,
            ),
        )


def list_reports(database: Path) -> list[AuditReport]:
    """Return every stored report, ordered by task id."""
    with _connect(database) as connection:
        rows = connection.execute(
            """
            SELECT task_id, title, requirements, requirement_coverage,
                   mutation_score, mutation_timed_out, findings_json
            FROM audits
            ORDER BY task_id
            """
        ).fetchall()
    return [_report_from_row(row) for row in rows]


def get_report(database: Path, task_id: str) -> AuditReport | None:
    """Return one stored report, or None when that id is absent."""
    with _connect(database) as connection:
        row = connection.execute(
            """
            SELECT task_id, title, requirements, requirement_coverage,
                   mutation_score, mutation_timed_out, findings_json
            FROM audits
            WHERE task_id = ?
            """,
            (task_id,),
        ).fetchone()
    if row is None:
        return None
    return _report_from_row(row)


@contextmanager
def _connect(database: Path) -> Iterator[sqlite3.Connection]:
    database.parent.mkdir(parents=True, exist_ok=True)
    connection = sqlite3.connect(database)
    connection.row_factory = sqlite3.Row
    try:
        _ensure_schema(connection)
        yield connection
    except Exception:
        connection.rollback()
        raise
    else:
        connection.commit()
    finally:
        connection.close()


def _report_from_row(row: sqlite3.Row) -> AuditReport:
    loaded: object = json.loads(str(row["findings_json"]))
    if not isinstance(loaded, list):
        raise ValueError("findings_json is not a list")
    findings = [ReportFinding.model_validate(item) for item in loaded]
    return AuditReport(
        id=str(row["task_id"]),
        title=str(row["title"]),
        requirements=int(row["requirements"]),
        requirement_coverage=float(row["requirement_coverage"]),
        mutation_score=float(row["mutation_score"]),
        mutation_timed_out=int(row["mutation_timed_out"]),
        findings=findings,
    )


def _ensure_schema(connection: sqlite3.Connection) -> None:
    """Create the table, and add the timeout column to an older database."""
    connection.execute(_SCHEMA)
    columns = {str(row[1]) for row in connection.execute("PRAGMA table_info(audits)")}
    if "mutation_timed_out" not in columns:
        connection.execute(
            "ALTER TABLE audits ADD COLUMN mutation_timed_out "
            "INTEGER NOT NULL DEFAULT 0"
        )
