from conftest import covers
from ready import ready


@covers("R1")
def test_ready() -> None:
    assert ready(2) == True  # noqa: E712
