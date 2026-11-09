from conftest import covers
from rate_limiter import RateLimiter


def _decisions(limit: int, calls: int) -> list[bool]:
    gate = RateLimiter(limit)
    return [gate.allow() for _ in range(calls)]


@covers("R1")
def test_two_calls_then_a_block() -> None:
    assert _decisions(2, 3) == [True, True, False]


@covers("R1")
def test_one_call_then_a_block() -> None:
    assert _decisions(1, 2) == [True, False]


@covers("R2")
def test_zero_limit_blocks_the_first_call() -> None:
    assert _decisions(0, 1) == [False]
