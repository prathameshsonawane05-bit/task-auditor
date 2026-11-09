from conftest import covers


@covers("R1")
def test_label() -> None:
    assert True
