from box import Box
from conftest import covers


@covers("R1")
def test_label() -> None:
    Box().label("hi")
