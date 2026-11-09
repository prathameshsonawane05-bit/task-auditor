from conftest import covers
from double import double


@covers("R9")
@covers("R1")
def test_double() -> None:
    assert double(3) == 6
