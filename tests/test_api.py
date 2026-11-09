"""The dashboard API stores reports in SQLite and lists them."""

from pathlib import Path

from fastapi.testclient import TestClient

from auditor.api import create_app
from auditor.report import AuditReport, ReportFinding


def test_empty_database_lists_nothing(tmp_path: Path) -> None:
    client = TestClient(create_app(tmp_path / "auditor.sqlite"))

    response = client.get("/api/tasks")

    assert response.status_code == 200
    assert response.json() == []


def test_stored_report_keeps_finding_fields(tmp_path: Path) -> None:
    client = TestClient(create_app(tmp_path / "auditor.sqlite"))
    stored = client.post("/api/tasks", json=_flawed().model_dump(mode="json"))
    empty = client.post("/api/tasks", json=_clean().model_dump(mode="json"))

    assert stored.status_code == 201
    assert empty.status_code == 201
    listing = client.get("/api/tasks")
    assert listing.status_code == 200
    rows = listing.json()
    assert [row["id"] for row in rows] == ["plant_weak_assertion_1", "slugify"]
    assert rows[0]["finding_count"] == 1
    assert rows[1]["finding_count"] == 0

    detail = client.get("/api/tasks/plant_weak_assertion_1")
    assert detail.status_code == 200
    body = detail.json()
    assert body["requirement_coverage"] == 1.0
    assert body["mutation_score"] == 0.0
    assert body["findings"] == [
        {
            "check": "weak_assertion",
            "severity": "medium",
            "location": "tests/test_box.py:4",
            "explanation": "The test does not contain an assert.",
        }
    ]

    missing = client.get("/api/tasks/missing")
    assert missing.status_code == 404


def _flawed() -> AuditReport:
    return AuditReport(
        id="plant_weak_assertion_1",
        title="Read a box label with a weak test",
        requirements=1,
        requirement_coverage=1.0,
        mutation_score=0.0,
        findings=[
            ReportFinding(
                check="weak_assertion",
                severity="medium",
                location="tests/test_box.py:4",
                explanation="The test does not contain an assert.",
            )
        ],
    )


def _clean() -> AuditReport:
    return AuditReport(
        id="slugify",
        title="Turn a phrase into a URL slug",
        requirements=2,
        requirement_coverage=1.0,
        mutation_score=1.0,
        findings=[],
    )
