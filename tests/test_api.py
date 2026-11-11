"""The dashboard API stores reports in SQLite and lists them."""

import json
import sqlite3
from pathlib import Path

from fastapi.testclient import TestClient

from auditor.api import create_app
from auditor.report import AuditReport, ReportFinding


def test_empty_database_lists_nothing(tmp_path: Path) -> None:
    client = _client(tmp_path / "auditor.sqlite")

    response = client.get("/api/tasks")

    assert response.status_code == 200
    assert response.json() == []


def test_stored_report_keeps_finding_fields(tmp_path: Path) -> None:
    client = _client(tmp_path / "auditor.sqlite")
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
    assert body["mutation_timed_out"] == 0
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


def test_stored_timeout_count_is_returned(tmp_path: Path) -> None:
    client = _client(tmp_path / "auditor.sqlite")
    payload = _clean().model_dump(mode="json")
    payload["mutation_timed_out"] = 4

    stored = client.post("/api/tasks", json=payload)
    detail = client.get("/api/tasks/slugify")

    assert stored.status_code == 201
    assert stored.json()["mutation_timed_out"] == 4
    assert detail.status_code == 200
    assert detail.json()["mutation_timed_out"] == 4


def test_old_schema_keeps_rows_and_reads_zero_timeouts(tmp_path: Path) -> None:
    database = tmp_path / "auditor.sqlite"
    connection = sqlite3.connect(database)
    connection.execute(
        """
        CREATE TABLE audits (
            task_id TEXT PRIMARY KEY,
            title TEXT NOT NULL,
            requirements INTEGER NOT NULL,
            requirement_coverage REAL NOT NULL,
            mutation_score REAL NOT NULL,
            findings_json TEXT NOT NULL
        )
        """
    )
    connection.execute(
        "INSERT INTO audits VALUES (?, ?, ?, ?, ?, ?)",
        ("slugify", "Turn a phrase into a URL slug", 2, 1.0, 1.0, "[]"),
    )
    connection.commit()
    connection.close()

    client = _client(database)
    listing = client.get("/api/tasks")
    detail = client.get("/api/tasks/slugify")

    assert listing.status_code == 200
    assert [row["id"] for row in listing.json()] == ["slugify"]
    assert detail.status_code == 200
    assert detail.json()["mutation_score"] == 1.0
    assert detail.json()["mutation_timed_out"] == 0
    assert detail.json()["title"] == "Turn a phrase into a URL slug"


def test_ipv6_loopback_is_accepted(tmp_path: Path) -> None:
    client = _client(tmp_path / "auditor.sqlite", host="::1")

    response = client.get("/api/tasks")

    assert response.status_code == 200
    assert response.json() == []


def test_remote_client_is_refused(tmp_path: Path) -> None:
    client = _client(tmp_path / "auditor.sqlite", host="10.0.0.1")

    response = client.get("/api/tasks")

    assert response.status_code == 403
    assert response.json()["detail"] == "local clients only"


def test_rejects_scores_outside_the_unit_interval(tmp_path: Path) -> None:
    client = _client(tmp_path / "auditor.sqlite")
    for field in ("requirement_coverage", "mutation_score"):
        for value in (-0.1, 1.1):
            payload = _clean().model_dump(mode="json")
            payload[field] = value
            response = client.post("/api/tasks", json=payload)
            assert response.status_code == 422, (field, value)
        for value in (float("nan"), float("inf"), float("-inf")):
            payload = _clean().model_dump(mode="json")
            payload[field] = value
            response = client.post(
                "/api/tasks",
                content=json.dumps(payload),
                headers={"content-type": "application/json"},
            )
            assert response.status_code == 422, (field, value)
    assert client.get("/api/tasks").json() == []


def test_rejects_a_severity_outside_the_three_levels(tmp_path: Path) -> None:
    client = _client(tmp_path / "auditor.sqlite")
    payload = _flawed().model_dump(mode="json")
    findings = payload["findings"]
    assert isinstance(findings, list)
    finding = findings[0]
    assert isinstance(finding, dict)
    finding["severity"] = "critical"

    response = client.post("/api/tasks", json=payload)

    assert response.status_code == 422
    assert client.get("/api/tasks/plant_weak_assertion_1").status_code == 404


def test_rejects_oversized_reports(tmp_path: Path) -> None:
    client = _client(tmp_path / "auditor.sqlite")
    long = "x" * 1001
    finding = _flawed().findings[0].model_dump(mode="json")

    too_many = _flawed().model_dump(mode="json")
    too_many["findings"] = [finding for _ in range(101)]
    too_many_requirements = _clean().model_dump(mode="json")
    too_many_requirements["requirements"] = 101
    long_id = _clean().model_dump(mode="json")
    long_id["id"] = long
    long_title = _clean().model_dump(mode="json")
    long_title["title"] = long
    long_check = _flawed().model_dump(mode="json")
    long_location = _flawed().model_dump(mode="json")
    long_explanation = _flawed().model_dump(mode="json")
    _finding(long_check)["check"] = long
    _finding(long_location)["location"] = long
    _finding(long_explanation)["explanation"] = long

    for payload in (
        too_many,
        too_many_requirements,
        long_id,
        long_title,
        long_check,
        long_location,
        long_explanation,
    ):
        response = client.post("/api/tasks", json=payload)
        assert response.status_code == 422

    boundary = _clean().model_dump(mode="json")
    boundary["id"] = "s" * 1000
    boundary["title"] = "t" * 1000
    boundary["requirements"] = 100
    one = dict(finding)
    one["check"] = "c" * 1000
    one["location"] = "l" * 1000
    one["explanation"] = "e" * 1000
    boundary["findings"] = [one for _ in range(100)]
    stored = client.post("/api/tasks", json=boundary)
    assert stored.status_code == 201
    assert client.get("/api/tasks").json()[0]["finding_count"] == 100


def _client(database: Path, host: str = "127.0.0.1") -> TestClient:
    return TestClient(create_app(database), client=(host, 50000))


def _finding(payload: dict[str, object]) -> dict[str, object]:
    findings = payload["findings"]
    assert isinstance(findings, list)
    finding = findings[0]
    assert isinstance(finding, dict)
    return finding


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
