from conftest import covers
from double import double


@covers("R1")
def test_double() -> None:
    assert double(3) == 6


def test_another_value() -> None:
    assert double(4) == 8
