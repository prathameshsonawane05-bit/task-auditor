# Progress log

## Stage 1: project setup, task loader and validation, and a CLI skeleton (commit 5916e9647622c1c27925e56e0073c82d3bc51dfd)
What was built:
Python 3.11 package `auditor` with a Pydantic v2 model of the invented task format, a loader that validates a task folder, and the CLI command `auditor audit <path>`. The command prints the task id, title, and requirement count. It does not run the task tests and does not implement checks 1–11. One invented sample task, `sample_tasks/slugify`, is included. Invalid cases are covered by tests: missing file or directory, missing field, wrong field type, unknown field, non-python language, empty requirements, duplicate requirement id, task id that does not match the folder name, a path outside `sample_tasks`, and a symlink that resolves outside `sample_tasks`.

Commands run and their real output:
`python3.11 -m venv .venv` failed because this Python is managed by uv and `ensurepip` refused to bootstrap pip. The environment used instead was `uv venv --python 3.11 .venv` and `uv pip install -e ".[dev]"`.

```
.venv/bin/ruff check .
All checks passed!

.venv/bin/ruff format --check .
19 files already formatted

.venv/bin/mypy
Success: no issues found in 10 source files

.venv/bin/pytest -v
============================= test session starts ==============================
platform darwin -- Python 3.11.14, pytest-9.2.0, pluggy-1.7.0 -- /Users/shubhambaviskar/Desktop/Eval Task Auditor/.venv/bin/python3
cachedir: .pytest_cache
rootdir: /Users/shubhambaviskar/Desktop/Eval Task Auditor
configfile: pyproject.toml
testpaths: tests
collecting ... collected 24 items

tests/test_cli.py::test_audit_prints_id_title_count_and_sandbox_warning PASSED [  4%]
tests/test_cli.py::test_audit_prints_validation_error_and_exits_nonzero PASSED [  8%]
tests/test_cli.py::test_audit_refuses_a_path_outside_sample_tasks PASSED [ 12%]
tests/test_loader.py::test_valid_folder_loads_id_title_and_requirement_count PASSED [ 16%]
tests/test_loader.py::test_real_sample_task_loads_from_another_working_directory PASSED [ 20%]
tests/test_loader.py::test_missing_file_or_directory_names_the_path[task.yaml-task.yaml-required file is missing] PASSED [ 25%]
tests/test_loader.py::test_missing_file_or_directory_names_the_path[instruction.md-instruction.md-required file is missing] PASSED [ 29%]
tests/test_loader.py::test_missing_file_or_directory_names_the_path[solution/solution.py-solution/solution.py-required file is missing] PASSED [ 33%]
tests/test_loader.py::test_missing_file_or_directory_names_the_path[environment-environment-required directory is missing] PASSED [ 37%]
tests/test_loader.py::test_missing_file_or_directory_names_the_path[tests-tests-required directory is missing] PASSED [ 41%]
tests/test_loader.py::test_environment_file_is_rejected PASSED           [ 45%]
tests/test_loader.py::test_missing_pytest_file_names_the_pattern PASSED  [ 50%]
tests/test_loader.py::test_missing_field_names_the_field PASSED          [ 54%]
tests/test_loader.py::test_wrong_field_type_names_the_value PASSED       [ 58%]
tests/test_loader.py::test_unknown_field_names_the_value PASSED          [ 62%]
tests/test_loader.py::test_non_python_language_names_the_value PASSED    [ 66%]
tests/test_loader.py::test_empty_requirements_names_the_value PASSED     [ 70%]
tests/test_loader.py::test_duplicate_requirement_id_names_the_later_value PASSED [ 75%]
tests/test_loader.py::test_task_id_must_match_folder_name PASSED         [ 79%]
tests/test_loader.py::test_path_outside_sample_tasks_names_the_path PASSED [ 83%]
tests/test_loader.py::test_symlink_that_escapes_sample_tasks_is_refused PASSED [ 87%]
tests/test_loader.py::test_nested_path_inside_sample_tasks_is_refused PASSED [ 91%]
tests/test_loader.py::test_task_yaml_must_be_a_mapping PASSED            [ 95%]
tests/test_loader.py::test_invalid_yaml_names_the_parser_error PASSED    [100%]

============================== 24 passed in 0.18s ==============================
```

`auditor audit sample_tasks/slugify` (exit 0):

```
warning: later stages run task code and this is not a security sandbox
id: slugify
title: Turn a phrase into a URL slug
requirements: 2
```

`auditor audit sample_tasks/bad-language` (exit 1). This folder was created only for the demo, with `language: javascript`, and deleted afterward. It is not in the commit.

```
warning: later stages run task code and this is not a security sandbox
error: language: must be 'python' (value: 'javascript')
```

`auditor audit /tmp` (exit 1):

```
warning: later stages run task code and this is not a security sandbox
error: path: must be inside sample_tasks (value: '/private/tmp')
```

Bugs found and fixed:
- Typer 0.28 turns an app with a single command into that command. `auditor audit sample_tasks/slugify` was parsed as unexpected extra arguments, and the program name itself was `audit`. A group callback keeps `audit` as a subcommand.
- `from click.testing import Result` failed because Typer 0.28 vendors Click and does not install the `click` package. Tests import `Result` from `typer.testing`.
- mypy reported `tests/task_factory.py` as both `task_factory` and `tests.task_factory`. Adding `tests/__init__.py` makes `tests` one package.
- Ruff B010 rejected `setattr` in the sample `covers` helper. The decorator now assigns `__covers__` directly.
- Ruff format required the sandbox warning to be one line.
- A path that existed but had the wrong type was reported as missing. A file where a directory is required now says `expected a directory` and includes the resolved path. The same applies to a directory where a file is required.
- The language message was attached to every Pydantic `literal_error`. It is now used only for the `language` field.

Files changed:
`.gitignore`, `AGENTS.md`, `pyproject.toml`, `auditor/__init__.py`, `auditor/__main__.py`, `auditor/cli.py`, `auditor/errors.py`, `auditor/loader.py`, `auditor/models.py`, `tests/__init__.py`, `tests/task_factory.py`, `tests/test_cli.py`, `tests/test_loader.py`, `sample_tasks/slugify/task.yaml`, `sample_tasks/slugify/instruction.md`, `sample_tasks/slugify/environment/slugify.py`, `sample_tasks/slugify/solution/solution.py`, `sample_tasks/slugify/tests/conftest.py`, `sample_tasks/slugify/tests/test_slugify.py`, `scripts/.gitkeep`, `docs/SPEC.md`, `docs/MENTOR.md`, `docs/PROGRESS.md`.

Decisions and open questions:
- Validation errors are `{field}: {message} (value: {value!r})`. A missing field or file uses value `None`. Only the first problem is reported.
- `sample_tasks` is found by walking parents of the installed package until both `pyproject.toml` and `auditor/__init__.py` exist. It is not taken from the current directory. Tests can pass another root.
- After `Path.resolve()`, the task directory must be a direct child of `sample_tasks`. A symlink that points outside is refused. A file inside an accepted task can still be a symlink to the outside. This stage does not inspect those links. The CLI warning stands: later stages run task code, and this is not a security sandbox.
- The warning and validation errors go to stderr. The id, title, and requirement count go to stdout. Failure exits 1.
- Runtime dependencies are Typer, Pydantic v2, and PyYAML. pytest, ruff, mypy, and types-PyYAML are dev extras. The YAML stubs are there so strict mypy can import `yaml`.
- Unknown fields are rejected. Duplicate requirement ids are reported at the later index, for example `requirements[2].id`.
- The sample includes `tests/conftest.py` with `@covers("R1")`, and the decorator stores the id on `__covers__`. Stage 1 does not reject a task that omits `conftest.py`. Empty `instruction.md` is accepted. Whether stage 3 should require `conftest.py`, and whether `__covers__` is the attribute name to keep, is open.
- No checks from the spec are implemented. The command does not run pytest on the task.

Next stage:
Stage 2: static AST checks 1 to 5, each with positive, negative, and edge-case tests on tiny hand-written snippets. Waiting for "next".
