from conftest import covers
from shout import shout


@covers("R1")
def test_shout() -> None:
    assert shout("ab") == "AB"
