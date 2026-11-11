"""Dynamic checks 8 to 10. Snippets are invented and same-author."""

import socket
import time
from pathlib import Path

import pytest

import auditor.checks.dynamic as dynamic
from auditor.checks.dynamic import (
    DYNAMIC_CHECKS,
    DYNAMIC_TIMEOUT_SECONDS,
    SuiteResult,
    probe_tcp,
    run_cheat_solution_passes,
    run_dynamic_checks,
    run_flaky_tests,
    run_solution_fails_tests,
    run_suite,
)
from auditor.checks.model import Severity
from tests.check_support import assert_one_sentence

REPO = Path(__file__).resolve().parents[1]
SLUGIFY = REPO / "sample_tasks" / "slugify"

_STARTER = "def echo(text: str) -> str:\n    raise NotImplementedError\n"
_ECHO_SOLUTION = "def echo(text: str) -> str:\n    return text\n"
_WRONG_SOLUTION = 'def echo(text: str) -> str:\n    return "no"\n'
_ECHO_TEST = """\
from echo import echo

def test_echo() -> None:
    assert echo("hi") == "hi"
"""
_UPPER_TEST = """\
from echo import echo

def test_upper() -> None:
    assert echo("hi") == "HI"
"""
_FLAKY_TEST = """\
from pathlib import Path

def test_once() -> None:
    path = Path("runs.txt")
    seen = path.read_text(encoding="utf-8") if path.exists() else ""
    path.write_text(seen + "x", encoding="utf-8")
    assert seen == ""
"""
_HANG_TEST = """\
import time

def test_hangs() -> None:
    time.sleep(30)
"""


def _write_task(
    root: Path,
    *,
    solution: str,
    tests: str,
    test_name: str = "test_echo.py",
) -> None:
    (root / "environment").mkdir(parents=True)
    (root / "solution").mkdir(parents=True)
    (root / "tests").mkdir(parents=True)
    (root / "environment" / "echo.py").write_text(_STARTER, encoding="utf-8")
    (root / "solution" / "solution.py").write_text(solution, encoding="utf-8")
    (root / "tests" / test_name).write_text(tests, encoding="utf-8")


def _snapshot(root: Path) -> dict[str, bytes]:
    return {
        str(path.relative_to(root)): path.read_bytes()
        for path in sorted(root.rglob("*"))
        if path.is_file()
    }


def test_dynamic_checks_are_registered() -> None:
    assert [rule.name for rule in DYNAMIC_CHECKS] == [
        "solution_fails_tests",
        "cheat_solution_passes",
        "flaky_tests",
    ]
    assert [rule.severity for rule in DYNAMIC_CHECKS] == [
        Severity.HIGH,
        Severity.HIGH,
        Severity.LOW,
    ]
    assert DYNAMIC_TIMEOUT_SECONDS == 2.0


def test_slugify_imports_the_reference_solution() -> None:
    result = run_suite(SLUGIFY)

    assert result.passed
    assert result.exit_code == 0
    assert [nodeid for nodeid, _outcome in result.tests] == [
        "test_slugify.py::test_lowercases_and_replaces_separators",
        "test_slugify.py::test_collapses_repeated_separators",
        "test_slugify.py::test_strips_edge_hyphens",
    ]


def test_slugify_has_no_dynamic_findings() -> None:
    before = _snapshot(SLUGIFY)

    findings = run_dynamic_checks(SLUGIFY)

    assert findings == []
    assert _snapshot(SLUGIFY) == before


def test_wrong_solution_is_flagged_and_a_consistent_failure_is_not_flaky(
    tmp_path: Path,
) -> None:
    root = tmp_path / "wrong"
    _write_task(root, solution=_WRONG_SOLUTION, tests=_UPPER_TEST)

    findings = run_dynamic_checks(root)

    assert [finding.check for finding in findings] == ["solution_fails_tests"]
    assert findings[0].severity == Severity.HIGH
    assert "exit code 1" in findings[0].explanation
    assert_one_sentence(findings[0].explanation)


def test_first_argument_cheat_passes_and_the_others_do_not(tmp_path: Path) -> None:
    root = tmp_path / "echo"
    _write_task(root, solution=_ECHO_SOLUTION, tests=_ECHO_TEST)

    findings = run_cheat_solution_passes(root)

    assert len(findings) == 1
    assert findings[0].check == "cheat_solution_passes"
    assert findings[0].severity == Severity.HIGH
    assert "first argument" in findings[0].explanation
    assert_one_sentence(findings[0].explanation)


def test_counter_file_forces_a_flaky_result(tmp_path: Path) -> None:
    root = tmp_path / "flaky"
    _write_task(
        root,
        solution=_ECHO_SOLUTION,
        tests=_FLAKY_TEST,
        test_name="test_flaky.py",
    )

    findings = run_flaky_tests(root)

    assert len(findings) == 1
    assert findings[0].check == "flaky_tests"
    assert findings[0].severity == Severity.LOW
    assert "passed, failed, failed" in findings[0].explanation
    assert_one_sentence(findings[0].explanation)


def test_flaky_runs_share_one_temp_directory(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    root = tmp_path / "shared"
    _write_task(
        root,
        solution=_ECHO_SOLUTION,
        tests=_FLAKY_TEST,
        test_name="test_flaky.py",
    )
    copies: list[Path] = []
    runs: list[Path] = []
    real_copy = dynamic._copy_task
    real_execute = dynamic._execute

    def spy_copy(src: Path, dest: Path, solution_text: str | None) -> bool:
        copies.append(dest)
        return real_copy(src, dest, solution_text)

    def spy_execute(dest: Path) -> SuiteResult:
        runs.append(dest)
        return real_execute(dest)

    monkeypatch.setattr(dynamic, "_copy_task", spy_copy)
    monkeypatch.setattr(dynamic, "_execute", spy_execute)

    findings = run_flaky_tests(root)

    assert len(copies) == 1
    assert len(runs) == 3
    assert runs[0] == runs[1] == runs[2] == copies[0]
    assert len(findings) == 1
    assert "passed, failed, failed" in findings[0].explanation


def test_hanging_child_returns_within_the_timeout(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(
        "auditor.checks.dynamic.DYNAMIC_TIMEOUT_SECONDS",
        0.5,
    )
    root = tmp_path / "hang"
    _write_task(root, solution=_ECHO_SOLUTION, tests=_HANG_TEST)

    started = time.perf_counter()
    findings = run_solution_fails_tests(root)
    elapsed = time.perf_counter() - started

    assert findings
    assert "0.5" in findings[0].explanation
    assert_one_sentence(findings[0].explanation)
    assert elapsed >= 0.3
    assert elapsed < 5


def test_child_cannot_open_a_tcp_socket() -> None:
    server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    server.bind(("127.0.0.1", 0))
    server.listen(1)
    server.settimeout(0.5)
    port = server.getsockname()[1]
    try:
        status = probe_tcp(port)
        assert status == "network access is blocked"
        with pytest.raises(TimeoutError):
            server.accept()
    finally:
        server.close()
