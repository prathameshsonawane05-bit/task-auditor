from conftest import covers
from pad import pad


@covers("R1")
def test_shift() -> None:
    assert pad(1) > 10
