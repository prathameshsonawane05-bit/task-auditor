from conftest import covers
from jars import jar_total


@covers("R1")
def test_only_the_named_jar_is_added() -> None:
    lines = [("Oats", 4), ("beans", 2), ("oats", 3), ("yeast", 5), ("oats", -1)]
    assert jar_total(lines, "oats") == 2


@covers("R1")
def test_a_removal_can_be_the_whole_total() -> None:
    assert jar_total([("oats", -2)], "oats") == -2


@covers("R2")
def test_a_missing_jar_or_an_empty_list_is_zero() -> None:
    lines = [("beans", 2), ("yeast", 5)]
    assert jar_total(lines, "rice") == 0
    assert jar_total([], "oats") == 0
