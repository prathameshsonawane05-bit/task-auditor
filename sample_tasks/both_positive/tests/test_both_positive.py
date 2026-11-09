from both_positive import both_positive
from conftest import covers


@covers("R1")
def test_both_above_zero() -> None:
    assert both_positive(1, 1) is True


@covers("R1")
def test_zero_or_negative_is_false() -> None:
    assert both_positive(0, 1) is False
    assert both_positive(1, 0) is False
    assert both_positive(-1, 1) is False
    assert both_positive(1, -1) is False
