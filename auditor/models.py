"""Pydantic models for the invented task format."""

from dataclasses import dataclass
from pathlib import Path
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field


class Requirement(BaseModel):
    """One requirement a task claims to test."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    id: str = Field(min_length=1)
    text: str = Field(min_length=1)


class TaskSpec(BaseModel):
    """Metadata from task.yaml. File layout is checked separately."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    id: str = Field(min_length=1)
    title: str = Field(min_length=1)
    language: Literal["python"]
    requirements: list[Requirement] = Field(min_length=1)


@dataclass(frozen=True, slots=True)
class LoadedTask:
    """A task folder that passed validation."""

    id: str
    title: str
    language: Literal["python"]
    requirements: tuple[Requirement, ...]
    root: Path
