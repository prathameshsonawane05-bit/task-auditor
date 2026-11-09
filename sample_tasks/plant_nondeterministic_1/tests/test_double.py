import random

from conftest import covers
from double import double


@covers("R1")
def test_double() -> None:
    assert random.random() >= 0
    assert double(3) == 6
