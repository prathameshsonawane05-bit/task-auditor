"""Dynamic checks 8 to 10.

Task code runs in a child process, in a temp directory, with a timeout.
The auditor process does not import the task. Files are copied. sample_tasks
is not modified.

Copy rule: each top-level ``environment/*.py`` module, other than
``__init__.py``, is replaced in the temp directory by ``solution/solution.py``
under that same file name. ``tests/`` is copied to the temp root, so imports
such as ``from conftest import covers`` still resolve. For slugify,
``from slugify import slugify`` loads the reference solution, not the starter
that raises NotImplementedError. A ``pytest.ini`` written in the temp
directory keeps pytest from walking up to this project's config.

Network block: before pytest starts, the child replaces ``socket.socket`` so
that the default family, ``AF_INET``, and ``AF_INET6`` raise
``OSError("network access is blocked")``. ``connect``, ``connect_ex``, and
``socket.create_connection`` raise the same error. This is not a security
sandbox. The block still allows AF_UNIX sockets, local files, a subprocess
(the patch is not inherited), ctypes and other direct system calls, and task
code that restores or reloads ``socket.socket``.

Timeout: each child is limited to ``DYNAMIC_TIMEOUT_SECONDS`` (2 seconds).
A child that is still running is killed, and the call returns. A correct
suite that needs longer than that is reported as not passing.

Cheats rewrite module-level function bodies only. A module with no
function is not rewritten, and that cheat is not run. The constant is ``0``.
A function with no positional parameter cannot return a first argument, so
that cheat uses ``return None`` for that function. Class methods and lambdas
are not rewritten. A cheat that times out or errors did not pass, so it is
not flagged.

Severity: ``solution_fails_tests`` and ``cheat_solution_passes`` are high.
``flaky_tests`` is low, because the pass/fail result changed without a
solution change. Flaky runs are ``FLAKY_RUNS`` (3) in one temp directory, so
a file the test writes can survive from one run to the next.
"""

import ast
import json
import os
import shutil
import subprocess
import sys
import tempfile
import textwrap
from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path

from auditor.checks.model import Finding, Severity

DYNAMIC_TIMEOUT_SECONDS = 2.0
FLAKY_RUNS = 3
SOLUTION_FAILS = "solution_fails_tests"
CHEAT_PASSES = "cheat_solution_passes"
FLAKY_TESTS = "flaky_tests"

_CHEATS: tuple[tuple[str, str], ...] = (
    ("none", "that returns None"),
    ("constant", "that returns 0"),
    ("empty", "with an empty function body"),
    ("first", "that returns the first argument"),
)

_NETWORK_BLOCK = textwrap.dedent(
    """\
    import socket as _socket

    class _NoTcp(_socket.socket):
        def __init__(self, family=-1, type=-1, proto=-1, fileno=None):
            if family in (-1, _socket.AF_INET, _socket.AF_INET6):
                raise OSError("network access is blocked")
            super().__init__(family, type, proto, fileno)

        def connect(self, address):
            raise OSError("network access is blocked")

        def connect_ex(self, address):
            raise OSError("network access is blocked")

    _socket.socket = _NoTcp

    def _no_tcp(*_args, **_kwargs):
        raise OSError("network access is blocked")

    _socket.create_connection = _no_tcp
    """
)

_PYTEST_DRIVER = _NETWORK_BLOCK + textwrap.dedent(
    """\
    import json
    import sys
    from pathlib import Path

    import pytest

    class _Record:
        def __init__(self) -> None:
            self.rows = []

        def pytest_runtest_logreport(self, report):
            if report.when == "call":
                self.rows.append(
                    {"nodeid": report.nodeid, "outcome": report.outcome}
                )
            elif report.when == "setup" and report.failed:
                self.rows.append({"nodeid": report.nodeid, "outcome": "failed"})

    root = sys.argv[1]
    out = Path(sys.argv[2])
    record = _Record()
    try:
        code = pytest.main(
            [
                root,
                f"--rootdir={root}",
                "-p",
                "no:cacheprovider",
                "-q",
                "--tb=line",
            ],
            plugins=[record],
        )
        payload = {"exit_code": int(code), "tests": record.rows}
    except Exception as exc:
        payload = {"exit_code": None, "tests": record.rows, "error": type(exc).__name__}
    out.write_text(json.dumps(payload), encoding="utf-8")
    """
)

_TCP_PROBE = _NETWORK_BLOCK + textwrap.dedent(
    """\
    import json
    import sys
    from pathlib import Path

    port = int(sys.argv[1])
    out = Path(sys.argv[2])
    try:
        sock = _socket.socket(_socket.AF_INET, _socket.SOCK_STREAM)
        sock.settimeout(1)
        sock.connect(("127.0.0.1", port))
    except OSError as exc:
        out.write_text(json.dumps({"ok": False, "error": str(exc)}), encoding="utf-8")
    else:
        sock.close()
        out.write_text(json.dumps({"ok": True}), encoding="utf-8")
    """
)


@dataclass(frozen=True, slots=True)
class DynamicRule:
    """A registered dynamic check. It receives a task directory."""

    name: str
    severity: Severity
    run: Callable[[Path], list[Finding]]


@dataclass(frozen=True, slots=True)
class SuiteResult:
    """One pytest invocation in a temp copy of a task."""

    exit_code: int | None
    tests: tuple[tuple[str, str], ...]
    timed_out: bool

    @property
    def passed(self) -> bool:
        return self.exit_code == 0 and not self.timed_out


def run_solution_fails_tests(root: Path) -> list[Finding]:
    """Flag a reference solution that does not pass its own tests."""
    result = _run_once(root, solution_text=None)
    if result.passed:
        return []
    return [_solution_finding(result)]


def run_cheat_solution_passes(root: Path) -> list[Finding]:
    """Flag each cheat rewrite that still passes the tests."""
    source = _read_solution(root)
    if source is None:
        return []
    findings: list[Finding] = []
    for kind, label in _CHEATS:
        cheated = _cheat_source(source, kind)
        if cheated is None:
            continue
        result = _run_once(root, solution_text=cheated)
        if not result.passed:
            continue
        findings.append(
            Finding(
                check=CHEAT_PASSES,
                severity=Severity.HIGH,
                location="solution/solution.py",
                explanation=f"Cheat {label} passed the tests.",
            )
        )
    return findings


def run_flaky_tests(root: Path) -> list[Finding]:
    """Flag a suite whose pass/fail results differ across three runs."""
    runs = _run_repeated(root, FLAKY_RUNS)
    return _flaky_findings(runs)


def run_dynamic_checks(root: Path) -> list[Finding]:
    """Run checks 8 to 10. This does not import the task."""
    findings: list[Finding] = []
    for rule in DYNAMIC_CHECKS:
        findings.extend(rule.run(root))
    return findings


def probe_tcp(port: int) -> str | None:
    """Try to open a TCP socket in a blocked child.

    Returns the child error text, ``"connected"`` if it connected, or None
    if the child did not finish.
    """
    with tempfile.TemporaryDirectory(prefix="taskauditor-") as directory:
        dest = Path(directory)
        script = dest / "probe.py"
        out = dest / "result.json"
        script.write_text(_TCP_PROBE, encoding="utf-8")
        completed = _run_child([str(script), str(port), str(out)], dest)
        if completed is None or not out.is_file():
            return None
        return _probe_status(out.read_text(encoding="utf-8"))


def run_suite(root: Path) -> SuiteResult:
    """Run the task tests once against the reference solution."""
    return _run_once(root, solution_text=None)


def run_suite_source(root: Path, solution_text: str) -> SuiteResult:
    """Run the task tests against replacement solution text.

    This is the same temp directory, timeout, network block, and copy rule
    as checks 8 to 10. The text is written only in the temp directory.
    """
    return _run_once(root, solution_text)


DYNAMIC_CHECKS: tuple[DynamicRule, ...] = (
    DynamicRule(SOLUTION_FAILS, Severity.HIGH, run_solution_fails_tests),
    DynamicRule(CHEAT_PASSES, Severity.HIGH, run_cheat_solution_passes),
    DynamicRule(FLAKY_TESTS, Severity.LOW, run_flaky_tests),
)


def _solution_finding(result: SuiteResult) -> Finding:
    if result.timed_out:
        text = (
            "Reference solution did not finish within "
            f"{DYNAMIC_TIMEOUT_SECONDS} seconds."
        )
    elif result.exit_code is not None:
        text = (
            "Reference solution failed its tests with pytest "
            f"exit code {result.exit_code}."
        )
    else:
        text = "Reference solution failed its tests and produced no pytest result."
    return Finding(
        check=SOLUTION_FAILS,
        severity=Severity.HIGH,
        location="solution/solution.py",
        explanation=text,
    )


def _flaky_findings(runs: list[SuiteResult]) -> list[Finding]:
    if len(runs) != FLAKY_RUNS:
        return []
    nodeids: list[str] = []
    for run in runs:
        for nodeid, _outcome in run.tests:
            if nodeid not in nodeids:
                nodeids.append(nodeid)
    findings: list[Finding] = []
    for nodeid in nodeids:
        outcomes = [_outcome_for(run, nodeid) for run in runs]
        if len(set(outcomes)) == 1:
            continue
        listed = ", ".join(outcomes)
        findings.append(
            Finding(
                check=FLAKY_TESTS,
                severity=Severity.LOW,
                location=nodeid,
                explanation=(
                    f"{nodeid} outcomes across {FLAKY_RUNS} runs were {listed}."
                ),
            )
        )
    if findings:
        return findings
    codes = [_run_label(run) for run in runs]
    if len(set(codes)) == 1:
        return []
    listed = ", ".join(codes)
    return [
        Finding(
            check=FLAKY_TESTS,
            severity=Severity.LOW,
            location="tests",
            explanation=f"Pytest results across {FLAKY_RUNS} runs were {listed}.",
        )
    ]


def _outcome_for(run: SuiteResult, nodeid: str) -> str:
    if run.timed_out:
        return "timeout"
    for candidate, outcome in run.tests:
        if candidate == nodeid:
            return outcome
    return "missing"


def _run_label(run: SuiteResult) -> str:
    if run.timed_out:
        return "timeout"
    if run.exit_code is None:
        return "no result"
    return f"exit {run.exit_code}"


def _run_once(root: Path, solution_text: str | None) -> SuiteResult:
    with tempfile.TemporaryDirectory(prefix="taskauditor-") as directory:
        dest = Path(directory)
        copied = _copy_task(root, dest, solution_text)
        if not copied:
            return SuiteResult(None, (), False)
        return _execute(dest)


def _run_repeated(root: Path, count: int) -> list[SuiteResult]:
    with tempfile.TemporaryDirectory(prefix="taskauditor-") as directory:
        dest = Path(directory)
        if not _copy_task(root, dest, None):
            return [SuiteResult(None, (), False) for _ in range(count)]
        return [_execute(dest) for _ in range(count)]


def _execute(dest: Path) -> SuiteResult:
    script = dest / "_auditor_driver.py"
    out = dest / "_auditor_result.json"
    script.write_text(_PYTEST_DRIVER, encoding="utf-8")
    completed = _run_child([str(script), str(dest), str(out)], dest)
    if completed is None:
        return SuiteResult(None, (), True)
    if not out.is_file():
        return SuiteResult(None, (), False)
    loaded = _load_suite(out.read_text(encoding="utf-8"))
    if loaded is None:
        return SuiteResult(None, (), False)
    return loaded


def _run_child(args: list[str], cwd: Path) -> subprocess.CompletedProcess[bytes] | None:
    try:
        return subprocess.run(
            [sys.executable, "-I", *args],
            cwd=cwd,
            env=_child_env(),
            timeout=DYNAMIC_TIMEOUT_SECONDS,
            capture_output=True,
            check=False,
            stdin=subprocess.DEVNULL,
        )
    except subprocess.TimeoutExpired:
        return None


def _child_env() -> dict[str, str]:
    """Environment for the child. Parent variables other than PATH are not copied."""
    env = {"PYTHONDONTWRITEBYTECODE": "1"}
    path = os.environ.get("PATH")
    if path is not None:
        env["PATH"] = path
    return env


def _copy_task(src: Path, dest: Path, solution_text: str | None) -> bool:
    tests = src / "tests"
    if not tests.is_dir():
        return False
    for path in tests.rglob("*"):
        if not path.is_file():
            continue
        if "__pycache__" in path.parts or path.suffix == ".pyc":
            continue
        relative = path.relative_to(tests)
        target = dest / relative
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(path, target)
    (dest / "pytest.ini").write_text("[pytest]\naddopts =\n", encoding="utf-8")
    text = solution_text if solution_text is not None else _read_solution(src)
    if text is None:
        return False
    environment = src / "environment"
    if not environment.is_dir():
        return False
    wrote = False
    for starter in sorted(environment.glob("*.py")):
        if starter.name == "__init__.py":
            continue
        (dest / starter.name).write_text(text, encoding="utf-8")
        wrote = True
    return wrote


def _read_solution(root: Path) -> str | None:
    path = root / "solution" / "solution.py"
    if not path.is_file():
        return None
    try:
        return path.read_text(encoding="utf-8")
    except (OSError, UnicodeError):
        return None


def _cheat_source(source: str, kind: str) -> str | None:
    try:
        tree = ast.parse(source)
    except SyntaxError:
        return None
    changed = False
    for stmt in tree.body:
        if isinstance(stmt, (ast.FunctionDef, ast.AsyncFunctionDef)):
            stmt.body = _cheat_body(stmt, kind)
            changed = True
    if not changed:
        return None
    return ast.unparse(tree)


def _cheat_body(
    fn: ast.FunctionDef | ast.AsyncFunctionDef,
    kind: str,
) -> list[ast.stmt]:
    if kind == "none":
        return [ast.Return(value=ast.Constant(value=None))]
    if kind == "constant":
        return [ast.Return(value=ast.Constant(value=0))]
    if kind == "empty":
        return [ast.Pass()]
    name = _first_positional(fn)
    if name is None:
        return [ast.Return(value=ast.Constant(value=None))]
    return [ast.Return(value=ast.Name(id=name, ctx=ast.Load()))]


def _first_positional(fn: ast.FunctionDef | ast.AsyncFunctionDef) -> str | None:
    params = [*fn.args.posonlyargs, *fn.args.args]
    if not params:
        return None
    return params[0].arg


def _load_suite(text: str) -> SuiteResult | None:
    try:
        loaded: object = json.loads(text)
    except json.JSONDecodeError:
        return None
    if not isinstance(loaded, dict):
        return None
    code = loaded.get("exit_code")
    tests = loaded.get("tests")
    if isinstance(code, bool) or (code is not None and not isinstance(code, int)):
        return None
    if not isinstance(tests, list):
        return None
    rows: list[tuple[str, str]] = []
    for item in tests:
        if not isinstance(item, dict):
            return None
        nodeid = item.get("nodeid")
        outcome = item.get("outcome")
        if not isinstance(nodeid, str) or not isinstance(outcome, str):
            return None
        rows.append((nodeid, outcome))
    exit_code = code if isinstance(code, int) else None
    return SuiteResult(exit_code, tuple(rows), False)


def _probe_status(text: str) -> str | None:
    try:
        loaded: object = json.loads(text)
    except json.JSONDecodeError:
        return None
    if not isinstance(loaded, dict):
        return None
    if loaded.get("ok") is True:
        return "connected"
    error = loaded.get("error")
    if isinstance(error, str):
        return error
    return None
