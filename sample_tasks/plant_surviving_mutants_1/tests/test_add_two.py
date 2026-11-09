from add_two import add_two
from conftest import covers


@covers("R1")
def test_shift() -> None:
    assert add_two(3) > 4
