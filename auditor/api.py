"""Small HTTP API that stores audit reports in SQLite."""

import os
from pathlib import Path

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, ConfigDict

from auditor.report import AuditReport
from auditor.store import get_report, list_reports, project_database_path, save_report


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
        save_report(database_path(), report)
        return report

    return app


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
