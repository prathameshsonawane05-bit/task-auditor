import pytest
from conftest import covers
from ticket import ticket_number


@covers("R1")
def test_the_three_tables_on_the_slip() -> None:
    assert ticket_number(1) == 9
    assert ticket_number(2) == 18
    assert ticket_number(4) == 36


@covers("R2")
def test_a_table_that_was_not_written_down() -> None:
    for table in (0, 3, 5):
        with pytest.raises(ValueError, match="that table is not on the slip"):
            ticket_number(table)
