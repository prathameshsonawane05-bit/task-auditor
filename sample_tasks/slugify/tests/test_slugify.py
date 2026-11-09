from conftest import covers
from slugify import slugify


@covers("R1")
def test_lowercases_and_replaces_separators() -> None:
    assert slugify("Hello, World!") == "hello-world"


@covers("R1")
def test_collapses_repeated_separators() -> None:
    assert slugify("a   b---c") == "a-b-c"


@covers("R2")
def test_strips_edge_hyphens() -> None:
    assert slugify("---Hello---") == "hello"
