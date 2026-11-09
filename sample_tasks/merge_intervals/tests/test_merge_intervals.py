from conftest import covers
from merge_intervals import merge_intervals


@covers("R1")
def test_empty_and_single_stay_put() -> None:
    assert merge_intervals([]) == []
    assert merge_intervals([(4, 5)]) == [(4, 5)]


@covers("R1")
def test_overlap_and_touch_merge() -> None:
    assert merge_intervals([(1, 4), (2, 6)]) == [(1, 6)]
    assert merge_intervals([(1, 2), (2, 5)]) == [(1, 5)]


@covers("R1")
def test_contained_interval_keeps_the_outer_end() -> None:
    assert merge_intervals([(1, 10), (2, 3)]) == [(1, 10)]


@covers("R1")
def test_unsorted_input_is_ordered_first() -> None:
    assert merge_intervals([(5, 7), (1, 3)]) == [(1, 3), (5, 7)]


@covers("R2")
def test_a_gap_stays_split() -> None:
    assert merge_intervals([(1, 2), (4, 5)]) == [(1, 2), (4, 5)]


@covers("R2")
def test_third_interval_merges_with_the_last_only() -> None:
    assert merge_intervals([(1, 2), (10, 12), (11, 15)]) == [(1, 2), (10, 15)]
