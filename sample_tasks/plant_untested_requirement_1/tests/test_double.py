from conftest import covers
from double import double


@covers("R1")
def test_double() -> None:
    assert double(3) == 6
    assert double(0) == 0
    assert double(-2) == -4
