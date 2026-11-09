from pathlib import Path

from conftest import covers
from triple import triple


@covers("R1")
def test_once() -> None:
    path = Path("ticks.txt")
    seen = ""
    if path.exists():
        seen = path.read_text(encoding="utf-8")
    path.write_text(seen + "x", encoding="utf-8")
    assert seen == ""
    assert triple(2) == 6
