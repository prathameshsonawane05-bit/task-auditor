from datetime import datetime

import pytest
from conftest import covers
from kettle import kettle_seconds


@covers("R1")
def test_two_mugs_while_the_clock_moves() -> None:
    seen = datetime.now()
    assert kettle_seconds(2) == 240
    assert seen.year >= 2020


@covers("R1")
def test_one_mug_and_three_mugs() -> None:
    assert kettle_seconds(1) == 120
    assert kettle_seconds(3) == 360


@covers("R2")
def test_fewer_than_one_mug_is_refused() -> None:
    with pytest.raises(ValueError, match="brew at least one mug"):
        kettle_seconds(0)
    with pytest.raises(ValueError, match="brew at least one mug"):
        kettle_seconds(-3)
