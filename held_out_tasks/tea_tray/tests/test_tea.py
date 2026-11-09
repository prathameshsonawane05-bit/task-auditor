import pytest
from conftest import covers
from tea import sugar_spoons


@covers("R1")
def test_sweet_tea_doubles_the_spoons() -> None:
    assert sugar_spoons("sweet", 0) == 0
    assert sugar_spoons("sweet", 2) == 4
    assert sugar_spoons("sweet", 3) == 6


@covers("R1")
def test_plain_tea_leaves_the_spoons_alone() -> None:
    assert sugar_spoons("plain", 0) == 0
    assert sugar_spoons("plain", 2) == 2
    assert sugar_spoons("plain", 5) == 5


@covers("R1")
def test_another_drink_is_refused() -> None:
    with pytest.raises(ValueError, match="tea is sweet or plain"):
        sugar_spoons("milky", 1)
    with pytest.raises(ValueError, match="tea is sweet or plain"):
        sugar_spoons("Sweet", 1)
