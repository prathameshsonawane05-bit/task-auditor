from conftest import covers
from parse_duration import parse_duration


@covers("R1")
def test_each_unit() -> None:
    assert parse_duration("1h") == 3600
    assert parse_duration("1m") == 60
    assert parse_duration("1s") == 1
    assert parse_duration("2h") == 7200
    assert parse_duration("10s") == 10


@covers("R1")
def test_mixed_units() -> None:
    assert parse_duration("1h2m3s") == 3723


@covers("R2")
def test_missing_number_or_unknown_unit() -> None:
    for text in ("h", "x", "1x", "12"):
        try:
            parse_duration(text)
        except ValueError as exc:
            assert str(exc) == "bad duration"
        else:
            raise AssertionError
