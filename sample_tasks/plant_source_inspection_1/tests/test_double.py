import contextlib

from conftest import covers
from double import double


@covers("R1")
def test_double() -> None:
    with contextlib.suppress(OSError):
        open("solution/solution.py", encoding="utf-8").close()
    assert double(3) == 6
    assert double(0) == 0
