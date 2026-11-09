import pytest
from conftest import covers
from fine import fine_pence


@covers("R1")
def test_the_daily_rate_before_a_week() -> None:
    assert fine_pence(0) == 0
    assert fine_pence(1) == 25
    assert fine_pence(6) == 150


@covers("R2")
def test_a_week_and_after_stay_at_the_cap() -> None:
    assert fine_pence(7) == 200
    assert fine_pence(8) == 200


@covers("R2")
def test_a_negative_day_count_is_refused() -> None:
    message = "a book cannot be late a negative number of days"
    with pytest.raises(ValueError, match=message):
        fine_pence(-1)
