"""Marker that ties a hall test to one requirement id."""

from collections.abc import Callable
from typing import TypeVar

F = TypeVar("F", bound=Callable[..., object])


def covers(requirement_id: str) -> Callable[[F], F]:
    """Attach a requirement id to a test function."""

    def decorator(func: F) -> F:
        func.__covers__ = requirement_id
        return func

    return decorator
