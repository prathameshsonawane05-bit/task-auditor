import pytest
from badge import badge_line
from conftest import covers


@covers("R1")
def test_spaces_around_the_name_come_off() -> None:
    assert badge_line(" Ada ") == "Hello, Ada"
    assert badge_line("B") == "Hello, B"


@covers("R2")
def test_a_blank_name_is_refused() -> None:
    with pytest.raises(ValueError, match="a badge needs a name"):
        badge_line("   ")
    with pytest.raises(ValueError, match="a badge needs a name"):
        badge_line("")


@covers("R1")
def test_the_badge_is_text() -> None:
    assert isinstance(badge_line("Ada"), str)
