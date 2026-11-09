from banner import banner
from conftest import covers


@covers("R1")
def test_banner() -> None:
    assert banner("") == "zzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzz"
