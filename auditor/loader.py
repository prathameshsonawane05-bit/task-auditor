"""Load and validate an invented task folder."""

from collections.abc import Sequence
from pathlib import Path

import yaml
from pydantic import ValidationError

from auditor.errors import TaskValidationError
from auditor.models import LoadedTask, Requirement, TaskSpec

_REQUIRED_FILES = (
    "task.yaml",
    "instruction.md",
    "solution/solution.py",
)


def default_sample_root() -> Path:
    """Return this repository's sample_tasks directory."""
    here = Path(__file__).resolve()
    for parent in here.parents:
        has_project = (parent / "pyproject.toml").is_file()
        has_package = (parent / "auditor" / "__init__.py").is_file()
        if has_project and has_package:
            return parent / "sample_tasks"
    raise TaskValidationError(
        field="sample_tasks",
        message="could not locate the project sample_tasks directory",
        value=str(here),
    )


def load_task(path: Path, *, sample_root: Path | None = None) -> LoadedTask:
    """Load a task folder under sample_tasks or raise TaskValidationError."""
    root = default_sample_root() if sample_root is None else sample_root
    task_dir = _require_task_dir(path, root)
    _require_layout(task_dir)
    spec = _parse_task_yaml(task_dir / "task.yaml")
    _reject_duplicate_requirement_ids(spec.requirements)
    _reject_folder_id_mismatch(spec.id, task_dir.name)
    return LoadedTask(
        id=spec.id,
        title=spec.title,
        language=spec.language,
        requirements=tuple(spec.requirements),
        root=task_dir,
    )


def _require_task_dir(path: Path, sample_root: Path) -> Path:
    root = sample_root.resolve()
    if not root.is_dir():
        raise TaskValidationError(
            field="sample_tasks",
            message="sample_tasks directory is missing",
            value=str(root),
        )
    try:
        candidate = path.resolve()
    except OSError as exc:
        raise TaskValidationError(
            field="path",
            message="could not be resolved",
            value=str(path),
        ) from exc
    if not _is_inside(candidate, root):
        raise TaskValidationError(
            field="path",
            message="must be inside sample_tasks",
            value=str(candidate),
        )
    if candidate.parent != root:
        raise TaskValidationError(
            field="path",
            message="must be a direct child of sample_tasks",
            value=str(candidate),
        )
    if not candidate.is_dir():
        raise TaskValidationError(
            field="path",
            message="task path is not a directory",
            value=str(candidate),
        )
    return candidate


def _is_inside(path: Path, parent: Path) -> bool:
    try:
        path.relative_to(parent)
    except ValueError:
        return False
    return True


def _require_layout(task_dir: Path) -> None:
    for relative in _REQUIRED_FILES:
        _require_file(task_dir, relative)
    _require_directory(task_dir, "environment")
    _require_directory(task_dir, "tests")
    tests_dir = task_dir / "tests"
    has_pytest_file = any(item.is_file() for item in tests_dir.glob("test_*.py"))
    if not has_pytest_file:
        raise TaskValidationError(
            field="tests/test_*.py",
            message="required file is missing",
            value=None,
        )


def _require_file(task_dir: Path, relative: str) -> None:
    candidate = task_dir / relative
    if candidate.is_file():
        return
    if candidate.exists():
        raise TaskValidationError(
            field=relative,
            message="expected a file",
            value=str(candidate.resolve()),
        )
    raise TaskValidationError(
        field=relative,
        message="required file is missing",
        value=None,
    )


def _require_directory(task_dir: Path, relative: str) -> None:
    candidate = task_dir / relative
    if candidate.is_dir():
        return
    if candidate.exists():
        raise TaskValidationError(
            field=relative,
            message="expected a directory",
            value=str(candidate.resolve()),
        )
    raise TaskValidationError(
        field=relative,
        message="required directory is missing",
        value=None,
    )


def _parse_task_yaml(path: Path) -> TaskSpec:
    try:
        raw_text = path.read_text(encoding="utf-8")
    except (OSError, UnicodeError) as exc:
        raise TaskValidationError(
            field="task.yaml",
            message="could not be read",
            value=str(exc),
        ) from exc
    try:
        loaded: object = yaml.safe_load(raw_text)
    except yaml.YAMLError as exc:
        raise TaskValidationError(
            field="task.yaml",
            message="invalid YAML",
            value=str(exc),
        ) from exc
    try:
        return TaskSpec.model_validate(_string_keyed_mapping(loaded))
    except ValidationError as exc:
        raise _from_pydantic(exc) from exc


def _string_keyed_mapping(loaded: object) -> dict[str, object]:
    if not isinstance(loaded, dict):
        raise TaskValidationError(
            field="task.yaml",
            message="expected a mapping",
            value=loaded,
        )
    mapping: dict[str, object] = {}
    for key, value in loaded.items():
        if not isinstance(key, str):
            raise TaskValidationError(
                field="task.yaml",
                message="field names must be strings",
                value=key,
            )
        mapping[key] = value
    return mapping


def _from_pydantic(exc: ValidationError) -> TaskValidationError:
    details = exc.errors()
    if not details:
        return TaskValidationError(
            field="task.yaml",
            message="invalid task metadata",
            value=None,
        )
    err = details[0]
    kind = err["type"]
    field = _format_loc(err["loc"])
    value: object = None if kind == "missing" else err.get("input")
    return TaskValidationError(
        field=field,
        message=_message_for(field, kind),
        value=value,
    )


def _format_loc(loc: tuple[object, ...]) -> str:
    if not loc:
        return "task.yaml"
    rendered: list[str] = []
    for part in loc:
        if isinstance(part, int):
            if not rendered:
                rendered.append(f"[{part}]")
            else:
                rendered[-1] = f"{rendered[-1]}[{part}]"
        else:
            rendered.append(str(part))
    return ".".join(rendered)


def _message_for(field: str, kind: str) -> str:
    if kind == "missing":
        return "required field is missing"
    if kind == "extra_forbidden":
        return "unknown field"
    if field == "language":
        return "must be 'python'"
    if kind in {"too_short", "string_too_short"}:
        return "must not be empty"
    if kind == "string_type":
        return "expected a string"
    if kind == "list_type":
        return "expected a list"
    if kind in {"dict_type", "model_type", "model_attributes_type"}:
        return "expected a mapping"
    return "invalid value"


def _reject_duplicate_requirement_ids(requirements: Sequence[Requirement]) -> None:
    seen: set[str] = set()
    for index, requirement in enumerate(requirements):
        if requirement.id in seen:
            raise TaskValidationError(
                field=f"requirements[{index}].id",
                message="duplicate requirement id",
                value=requirement.id,
            )
        seen.add(requirement.id)


def _reject_folder_id_mismatch(task_id: str, folder_name: str) -> None:
    if task_id != folder_name:
        raise TaskValidationError(
            field="id",
            message=f"does not match folder name {folder_name!r}",
            value=task_id,
        )
