"""Start a task child with a wall-clock limit and a process-group kill.

This is not a security sandbox. The helper discards the child's stdout and
stderr, starts a new session, and on timeout kills that process group. The
driver also sets a soft address-space limit. Those controls do not stop
AF_UNIX sockets, local files, ctypes, or task code that restores
``socket.socket``.
"""

import os
import signal
import subprocess
import sys
from pathlib import Path

# 512 GiB. A 512 MiB cap cannot be installed on this Mac: a fresh
# interpreter already uses about 422 GiB of virtual address space, so
# setrlimit rejects 512 MiB before pytest or the task is imported.
CHILD_ADDRESS_LIMIT_BYTES = 512 * 1024 * 1024 * 1024


def address_limit_source() -> str:
    """Python that sets the soft address limit before other imports."""
    limit = CHILD_ADDRESS_LIMIT_BYTES
    return (
        "import resource as _resource\n"
        "_resource.setrlimit(\n"
        "    _resource.RLIMIT_AS,\n"
        f"    ({limit}, {limit}),\n"
        ")\n"
    )


def run_limited_child(
    args: list[str],
    *,
    cwd: Path,
    env: dict[str, str],
    timeout: float,
) -> subprocess.CompletedProcess[bytes] | None:
    """Run ``python -I`` in a new session.

    stdout and stderr are discarded. On timeout the process group is
    killed and this waits until the direct child is gone. None means the
    wall-clock limit fired.
    """
    command = [sys.executable, "-I", *args]
    process: subprocess.Popen[bytes] = subprocess.Popen(
        command,
        cwd=cwd,
        env=env,
        stdin=subprocess.DEVNULL,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
        start_new_session=True,
    )
    try:
        code = process.wait(timeout=timeout)
    except subprocess.TimeoutExpired:
        _kill_group(process)
        return None
    return subprocess.CompletedProcess(command, code)


def _kill_group(process: subprocess.Popen[bytes]) -> None:
    if process.poll() is None:
        try:
            os.killpg(process.pid, signal.SIGKILL)
        except ProcessLookupError:
            process.kill()
    process.wait()
