from bump import bump
from conftest import covers


@covers("R1")
def test_bump() -> None:
    assert bump(4) == 5
