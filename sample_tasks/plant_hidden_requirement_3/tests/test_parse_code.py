import pytest
from conftest import covers
from parse_code import parse_code


@covers("R1")
def test_reject() -> None:
    with pytest.raises(ValueError, match="code was rejected"):
        parse_code("nope")
    assert 1 == 1
