"""Findings and the inputs static checks read."""

from collections.abc import Callable
from dataclasses import dataclass
from enum import StrEnum

from pydantic import BaseModel, ConfigDict, Field


class Severity(StrEnum):
    """How a finding weakens the verifier.

    high: the test reads solution source, the reference solution matches a
    test by returning literals, or a requirement id has no @covers marker.
    The task can pass without the behavior the instruction describes.
    medium: the assertion is too weak to reject a wrong solution, it
    demands an exact string the instruction never gives, or a test checks
    an id or error message the task does not publish.
    low: the test can change result without a change to the solution.
    """

    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"


class Finding(BaseModel):
    """One problem reported by a registered check."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    check: str = Field(min_length=1)
    severity: Severity
    location: str = Field(min_length=1)
    explanation: str = Field(min_length=1)


@dataclass(frozen=True, slots=True)
class Snippet:
    """Source text plus the location prefix used in findings."""

    label: str
    source: str


@dataclass(frozen=True, slots=True)
class StaticTarget:
    """Snippets a static check can see. auditor.run builds this from the task."""

    tests: tuple[Snippet, ...]
    solution: Snippet | None = None
    instruction: str = ""
    requirements: tuple[str, ...] = ()


CheckFn = Callable[[StaticTarget], list[Finding]]


@dataclass(frozen=True, slots=True)
class Rule:
    """A registered static check."""

    name: str
    severity: Severity
    run: CheckFn
