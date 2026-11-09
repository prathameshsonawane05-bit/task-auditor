from conftest import covers
from last_char import last_char


@covers("R1")
def test_last_character() -> None:
    assert last_char("ab") == "b"
    assert last_char("a") == "a"


@covers("R2")
def test_empty_string() -> None:
    assert last_char("") == ""
