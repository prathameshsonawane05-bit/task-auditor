from conftest import covers
from echo import echo


@covers("R1")
def test_echo() -> None:
    assert echo("hi") == "hi"
