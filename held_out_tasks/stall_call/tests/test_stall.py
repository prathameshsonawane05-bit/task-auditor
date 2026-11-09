import pytest
from conftest import covers
from stall import stall_summary


@covers("R1")
def test_the_call_names_the_jars_and_the_price() -> None:
    assert stall_summary(4, 80) == (
        "We set out 4 jars and asked 80 pence for each one."
    )
    assert stall_summary(12, 150) == (
        "We set out 12 jars and asked 150 pence for each one."
    )
    assert stall_summary(0, 0) == ("We set out 0 jars and asked 0 pence for each one.")


@covers("R2")
def test_a_negative_count_or_price_is_refused() -> None:
    message = "counts and prices cannot be negative"
    with pytest.raises(ValueError, match=message):
        stall_summary(-1, 80)
    with pytest.raises(ValueError, match=message):
        stall_summary(4, -5)
