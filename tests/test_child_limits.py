"""Resource limits for the pytest child and the check-3 call child."""

import os
import signal
import subprocess
import time
from pathlib import Path

import pytest

from auditor.checks.child import CHILD_ADDRESS_LIMIT_BYTES
from auditor.checks.dynamic import run_suite
from auditor.checks.sandbox import run_calls

FIXTURES = Path(__file__).parent / "fixtures"
_STARTER = "def echo(text: str) -> str:\n    raise NotImplementedError\n"
_SOLUTION = "def echo(text: str) -> str:\n    return text\n"


def test_timeout_kills_sleeping_grandchild(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr("auditor.checks.sandbox.SUBPROCESS_TIMEOUT_SECONDS", 1.5)
    monkeypatch.setattr("auditor.checks.dynamic.DYNAMIC_TIMEOUT_SECONDS", 1.5)
    fixture = (FIXTURES / "sleeping_grandchild.py").read_text(encoding="utf-8")
    call_pid = tmp_path / "call.pid"
    suite_pid = tmp_path / "suite.pid"
    try:
        assert run_calls(fixture, "hold", [[str(call_pid)]]) is None
        _assert_dead(call_pid)
        root = tmp_path / "sleeper"
        _write_task(root, tests=_suite_test(fixture, suite_pid))
        result = run_suite(root)
        assert result.timed_out
        _assert_dead(suite_pid)
    finally:
        _reap_file(call_pid)
        _reap_file(suite_pid)


def test_child_reports_soft_address_limit(tmp_path: Path) -> None:
    fixture = (FIXTURES / "report_address_limit.py").read_text(encoding="utf-8")
    results = run_calls(fixture, "soft_address_limit", [[]])
    assert results is not None
    assert len(results) == 1
    assert results[0].ok
    assert results[0].value == CHILD_ADDRESS_LIMIT_BYTES

    root = tmp_path / "limit"
    _write_task(
        root,
        tests=(
            "import resource\n"
            "\n"
            "def test_soft_address_limit() -> None:\n"
            "    soft, _hard = resource.getrlimit(resource.RLIMIT_AS)\n"
            f"    assert soft == {CHILD_ADDRESS_LIMIT_BYTES}\n"
        ),
    )
    result = run_suite(root)
    assert result.passed


def _suite_test(fixture: str, pid_path: Path) -> str:
    return fixture + (
        f"\ndef test_leave_a_grandchild() -> None:\n    hold({str(pid_path)!r})\n"
    )


def _write_task(root: Path, *, tests: str) -> None:
    (root / "environment").mkdir(parents=True)
    (root / "solution").mkdir(parents=True)
    (root / "tests").mkdir(parents=True)
    (root / "environment" / "echo.py").write_text(_STARTER, encoding="utf-8")
    (root / "solution" / "solution.py").write_text(_SOLUTION, encoding="utf-8")
    (root / "tests" / "test_child.py").write_text(tests, encoding="utf-8")


def _assert_dead(path: Path) -> None:
    assert path.is_file()
    pid = int(path.read_text(encoding="utf-8"))
    try:
        assert not _running(pid)
    finally:
        _reap(pid)


def _reap_file(path: Path) -> None:
    if path.is_file():
        _reap(int(path.read_text(encoding="utf-8")))


def _reap(pid: int) -> None:
    if not _running(pid):
        return
    try:
        os.kill(pid, signal.SIGKILL)
    except ProcessLookupError:
        return
    deadline = time.monotonic() + 2
    while _running(pid) and time.monotonic() < deadline:
        time.sleep(0.05)


def _running(pid: int) -> bool:
    try:
        os.kill(pid, 0)
    except ProcessLookupError:
        return False
    except PermissionError:
        return True
    result = subprocess.run(
        ["ps", "-o", "state=", "-p", str(pid)],
        check=False,
        capture_output=True,
        text=True,
    )
    state = result.stdout.strip()
    return state != "" and not state.startswith("Z")
