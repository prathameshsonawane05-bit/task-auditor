from conftest import covers
from widen import widen


@covers("R1")
def test_shift() -> None:
    assert widen(2) >= 6
