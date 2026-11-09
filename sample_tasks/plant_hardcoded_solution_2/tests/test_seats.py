from conftest import covers
from seats import seats


@covers("R1")
def test_seats() -> None:
    assert seats(2) == 5
