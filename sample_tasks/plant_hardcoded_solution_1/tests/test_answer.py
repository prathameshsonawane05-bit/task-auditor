from answer import answer
from conftest import covers


@covers("R1")
def test_answer() -> None:
    assert answer("a") == "ok"
