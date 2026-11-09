import pytest
from conftest import covers
from rows import pack_rows


@covers("R1")
def test_a_short_final_row_keeps_the_given_order() -> None:
    labels = ["c", "a", "b", "d", "e"]
    assert pack_rows(labels, 2) == [["c", "a"], ["b", "d"], ["e"]]


@covers("R1")
def test_an_exact_fit_does_not_add_an_empty_row() -> None:
    assert pack_rows(["ann", "bo"], 2) == [["ann", "bo"]]
    assert pack_rows(["ann"], 1) == [["ann"]]


@covers("R1")
def test_no_labels_is_an_empty_layout() -> None:
    assert pack_rows([], 3) == []


@covers("R2")
def test_a_width_below_one_is_refused() -> None:
    message = "a row needs at least one slot"
    for width in (0, -2):
        with pytest.raises(ValueError, match=message):
            pack_rows(["ann"], width)
