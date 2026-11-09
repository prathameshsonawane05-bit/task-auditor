from banner import banner
from conftest import covers


@covers("R1")
def test_banner() -> None:
    assert banner("") == "0123456789012345678901234567890123456789"
