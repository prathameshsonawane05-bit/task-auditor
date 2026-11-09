import random

from conftest import covers
from double import double


@covers("R1")
def test_double() -> None:
    assert random.randint(5, 5) == 5
    assert double(3) == 6
