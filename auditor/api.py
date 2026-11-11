"""Small HTTP API that stores audit reports in SQLite.

The API has no accounts. It accepts only clients on 127.0.0.1 and ::1.
"""

import math
import os
from collections.abc import Awaitable, Callable
from pathlib import Path

from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, ConfigDict
from starlette.responses import JSONResponse, Response

from auditor.report import AuditReport
from auditor.store import get_report, list_reports, project_database_path, save_report

_LOCAL_HOSTS = frozenset({"127.0.0.1", "::1"})
_SEVERITIES = frozenset({"high", "medium", "low"})
_MAX_TEXT = 1000
_MAX_COUNT = 100


class TaskSummary(BaseModel):
    """One row in the dashboard list."""

    model_config = ConfigDict(extra="forbid")

    id: str
    title: str
    requirements: int
    requirement_coverage: float
    mutation_score: float
    finding_count: int


def create_app(database: Path | None = None) -> FastAPI:
    """Build the API. A None database uses AUDITOR_DB or the project file."""
    app = FastAPI(title="TaskAuditor")
    app.state.database = database
    app.add_middleware(
        CORSMiddleware,
        allow_origins=[
            "http://127.0.0.1:5173",
            "http://localhost:5173",
        ],
        allow_methods=["GET", "POST"],
        allow_headers=["Content-Type"],
    )

    @app.middleware("http")
    async def local_clients_only(
        request: Request,
        call_next: Callable[[Request], Awaitable[Response]],
    ) -> Response:
        client = request.client
        host = client.host if client is not None else ""
        if host not in _LOCAL_HOSTS:
            return JSONResponse(
                status_code=403,
                content={"detail": "local clients only"},
            )
        return await call_next(request)

    def database_path() -> Path:
        chosen: Path | None = app.state.database
        if chosen is not None:
            return chosen
        env = os.environ.get("AUDITOR_DB")
        if env:
            return Path(env)
        return project_database_path()

    @app.get("/api/tasks", response_model=list[TaskSummary])
    def read_tasks() -> list[TaskSummary]:
        return [_summary(report) for report in list_reports(database_path())]

    @app.get("/api/tasks/{task_id}", response_model=AuditReport)
    def read_task(task_id: str) -> AuditReport:
        report = get_report(database_path(), task_id)
        if report is None:
            raise HTTPException(status_code=404, detail=f"task not stored: {task_id}")
        return report

    @app.post("/api/tasks", response_model=AuditReport, status_code=201)
    def store_task(report: AuditReport) -> AuditReport:
        reason = stored_report_error(report)
        if reason is not None:
            raise HTTPException(status_code=422, detail=reason)
        save_report(database_path(), report)
        return report

    return app


def stored_report_error(report: AuditReport) -> str | None:
    """Return why this report must not be stored, or None when it may."""
    if report.requirements > _MAX_COUNT:
        return "requirements must be at most 100"
    if len(report.findings) > _MAX_COUNT:
        return "findings must be at most 100"
    if len(report.id) > _MAX_TEXT or len(report.title) > _MAX_TEXT:
        return "id and title must be at most 1000 characters"
    if not _unit_interval(report.requirement_coverage):
        return "requirement_coverage must be from 0 to 1"
    if not _unit_interval(report.mutation_score):
        return "mutation_score must be from 0 to 1"
    for finding in report.findings:
        if finding.severity not in _SEVERITIES:
            return "severity must be high, medium, or low"
        if (
            len(finding.check) > _MAX_TEXT
            or len(finding.location) > _MAX_TEXT
            or len(finding.explanation) > _MAX_TEXT
        ):
            return "finding text must be at most 1000 characters"
    return None


def _unit_interval(value: float) -> bool:
    return math.isfinite(value) and 0.0 <= value <= 1.0


def _summary(report: AuditReport) -> TaskSummary:
    return TaskSummary(
        id=report.id,
        title=report.title,
        requirements=report.requirements,
        requirement_coverage=report.requirement_coverage,
        mutation_score=report.mutation_score,
        finding_count=len(report.findings),
    )


app = create_app()
