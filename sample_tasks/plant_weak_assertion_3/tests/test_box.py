from box import Box
from conftest import covers


@covers("R1")
def test_label() -> None:
    assert Box().label("hi") is not None
