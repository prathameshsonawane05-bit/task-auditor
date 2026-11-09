import inspect

import pytest
from conftest import covers
from flour import flour_grams


@covers("R1")
def test_each_cup_is_a_hundred_and_twenty_grams() -> None:
    assert flour_grams(0) == 0
    assert flour_grams(1) == 120
    assert flour_grams(3) == 360


@covers("R2")
def test_a_negative_cup_count_is_refused() -> None:
    with pytest.raises(ValueError, match="a cup count cannot be negative"):
        flour_grams(-1)


@covers("R1")
def test_the_written_function_mentions_the_cup_weight() -> None:
    text = inspect.getsource(flour_grams)
    assert "120" in text
