"""Run reference-solution calls in a child process.

The auditor process writes the solution to a temp file and starts a second
Python. It does not import or exec that file itself.
"""

import json
import os
import subprocess
import sys
import tempfile
import textwrap
from collections.abc import Sequence
from dataclasses import dataclass
from pathlib import Path

SUBPROCESS_TIMEOUT_SECONDS = 2.0

DRIVER_SOURCE = textwrap.dedent(
    """\
    import json
    import sys
    from pathlib import Path

    work, func_name, calls_path, results_path = sys.argv[1:5]
    sys.path.insert(0, work)
    module = __import__("solution")
    func = getattr(module, func_name)
    calls = json.loads(Path(calls_path).read_text(encoding="utf-8"))
    results: list[dict[str, object]] = []
    for args in calls:
        try:
            value = func(*args)
            json.dumps(value)
        except Exception as exc:
            results.append({"ok": False, "error": type(exc).__name__})
            continue
        results.append({"ok": True, "value": value})
    Path(results_path).write_text(json.dumps(results), encoding="utf-8")
    """
)


@dataclass(frozen=True, slots=True)
class CallResult:
    """One child-process call, or the exception type it raised."""

    ok: bool
    value: object = None
    error: str | None = None


def run_calls(
    solution_source: str,
    func_name: str,
    calls: Sequence[Sequence[object]],
) -> list[CallResult] | None:
    """Call a solution function on each argument list.

    Returns None when the child times out, crashes, or writes nothing the
    parent can read. That means the check could not confirm the call.
    """
    if not func_name.isidentifier():
        return None
    try:
        encoded = json.dumps([list(args) for args in calls])
    except TypeError:
        return None
    with tempfile.TemporaryDirectory(prefix="taskauditor-") as directory:
        root = Path(directory)
        (root / "solution.py").write_text(solution_source, encoding="utf-8")
        (root / "driver.py").write_text(DRIVER_SOURCE, encoding="utf-8")
        calls_path = root / "calls.json"
        results_path = root / "results.json"
        calls_path.write_text(encoded, encoding="utf-8")
        try:
            subprocess.run(
                [
                    sys.executable,
                    "-I",
                    str(root / "driver.py"),
                    str(root),
                    func_name,
                    str(calls_path),
                    str(results_path),
                ],
                cwd=root,
                env=_child_env(),
                timeout=SUBPROCESS_TIMEOUT_SECONDS,
                capture_output=True,
                check=False,
            )
        except subprocess.TimeoutExpired:
            return None
        if not results_path.is_file():
            return None
        return _load_results(results_path.read_text(encoding="utf-8"))


def _child_env() -> dict[str, str]:
    """Environment for the child. Parent variables are not copied."""
    env = {"PYTHONDONTWRITEBYTECODE": "1"}
    path = os.environ.get("PATH")
    if path is not None:
        env["PATH"] = path
    return env


def _load_results(text: str) -> list[CallResult] | None:
    try:
        loaded: object = json.loads(text)
    except json.JSONDecodeError:
        return None
    if not isinstance(loaded, list):
        return None
    results: list[CallResult] = []
    for item in loaded:
        parsed = _load_result(item)
        if parsed is None:
            return None
        results.append(parsed)
    return results


def _load_result(item: object) -> CallResult | None:
    if not isinstance(item, dict):
        return None
    ok = item.get("ok")
    if ok is True:
        return CallResult(ok=True, value=item.get("value"))
    if ok is False:
        error = item.get("error")
        return CallResult(ok=False, error=error if isinstance(error, str) else "error")
    return None
