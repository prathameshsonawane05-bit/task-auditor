"""Pytest helpers for this invented task."""

from collections.abc import Callable
from typing import TypeVar

F = TypeVar("F", bound=Callable[..., object])


def covers(requirement_id: str) -> Callable[[F], F]:
    """Mark a test as covering one requirement id."""

    def decorator(func: F) -> F:
        func.__covers__ = requirement_id
        return func

    return decorator
