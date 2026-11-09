from pathlib import Path

from conftest import covers
from scale import scale


@covers("R1")
def test_once() -> None:
    path = Path("passes.txt")
    seen = ""
    if path.exists():
        seen = path.read_text(encoding="utf-8")
    path.write_text(seen + "x", encoding="utf-8")
    assert seen == ""
    assert scale(3) == 30
