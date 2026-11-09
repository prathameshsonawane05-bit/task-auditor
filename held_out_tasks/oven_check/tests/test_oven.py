from conftest import covers
from oven import oven_ready


@covers("R1")
def test_both_ends_of_the_window_are_ready() -> None:
    assert oven_ready(180) is True
    assert oven_ready(200) is True
    assert oven_ready(181) is True
    assert oven_ready(199) is True


@covers("R1")
def test_either_side_of_the_window_waits() -> None:
    assert oven_ready(179) is False
    assert oven_ready(201) is False
    assert oven_ready(100) is False
    assert oven_ready(250) is False
