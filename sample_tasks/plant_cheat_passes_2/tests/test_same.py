from conftest import covers
from same import same


@covers("R1")
def test_same() -> None:
    assert same(4) == 4
