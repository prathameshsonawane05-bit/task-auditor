"""Invented child: record a sleeping grandchild, then block."""

import pathlib
import subprocess
import time


def hold(pid_path: str) -> None:
    grandchild = subprocess.Popen(["sleep", "120"])
    pathlib.Path(pid_path).write_text(str(grandchild.pid), encoding="utf-8")
    time.sleep(60)
