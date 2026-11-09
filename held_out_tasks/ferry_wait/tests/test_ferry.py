from conftest import covers
from ferry import wait_minutes


@covers("R1")
def test_a_later_boat_is_the_wait() -> None:
    assert wait_minutes(50, [60]) == 10
    assert wait_minutes(50, [10, 60]) == 10


@covers("R1")
def test_a_boat_at_this_minute_is_zero() -> None:
    assert wait_minutes(60, [60]) == 0
    assert wait_minutes(0, [0, 15]) == 0


@covers("R2")
def test_a_spent_sheet_means_tomorrow() -> None:
    assert wait_minutes(70, [10, 60]) == -1
    assert wait_minutes(10, []) == -1
