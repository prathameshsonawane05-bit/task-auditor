import pytest
from conftest import covers
from postage import postage_pence


@covers("R1")
def test_empty_and_light_parcels_cost_eighty() -> None:
    assert postage_pence(0) == 80
    assert postage_pence(99) == 80


@covers("R1")
def test_middle_band_starts_at_one_hundred() -> None:
    assert postage_pence(100) == 150
    assert postage_pence(499) == 150


@covers("R1")
def test_heavy_band_runs_through_two_thousand() -> None:
    assert postage_pence(500) == 320
    assert postage_pence(2000) == 320


@covers("R2")
def test_a_negative_reading_is_refused() -> None:
    with pytest.raises(ValueError, match="the scale cannot read a negative"):
        postage_pence(-1)


@covers("R2")
def test_past_two_thousand_does_not_fit_the_bike() -> None:
    with pytest.raises(ValueError, match="too heavy for the bike"):
        postage_pence(2001)
