from conftest import covers
from keep import keep


@covers("R1")
def test_keep() -> None:
    assert keep(True) is True
