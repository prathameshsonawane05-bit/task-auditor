from conftest import covers
from scale import scale


@covers("R1")
def test_positive_zero_and_negative() -> None:
    assert scale(3) == 30
    assert scale(0) == 0
    assert scale(-1) == -10
