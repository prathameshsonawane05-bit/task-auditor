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

## Stage 2: static checks 1 to 5 (commit f7250cc7464e1268675712a0f02dc185ee192bdf)
What was built:
Five registered static rules in `auditor.checks`. Each finding has a check name, a severity, a location, and one sentence that names the evidence. `auditor audit` still only validates a task folder. It does not import the checks and does not print findings. `run_static_checks` runs the five rules on snippets. The invented `slugify` sample produces no findings.

The snippet tests for each check were written by the same author as the checks. Passing them is weak evidence.

Commands run and their real output:
```
.venv/bin/ruff check .
All checks passed!

.venv/bin/ruff format --check .
36 files already formatted

.venv/bin/mypy
Success: no issues found in 27 source files

.venv/bin/pytest -v
============================= test session starts ==============================
platform darwin -- Python 3.11.14, pytest-9.2.0, pluggy-1.7.0 -- /Users/shubhambaviskar/Desktop/Eval Task Auditor/.venv/bin/python3
cachedir: .pytest_cache
rootdir: /Users/shubhambaviskar/Desktop/Eval Task Auditor
configfile: pyproject.toml
testpaths: tests
collecting ... collected 65 items

tests/test_brittle_format.py::test_cutoff_is_40_characters PASSED        [  1%]
tests/test_brittle_format.py::test_long_string_equality_without_a_specified_format_is_flagged PASSED [  3%]
tests/test_brittle_format.py::test_numeric_equality_is_not_flagged PASSED [  4%]
tests/test_brittle_format.py::test_same_literal_is_not_flagged_when_the_instruction_specifies_it PASSED [  6%]
tests/test_brittle_format.py::test_short_string_equality_is_not_flagged PASSED [  7%]
tests/test_cli.py::test_audit_prints_id_title_count_and_sandbox_warning PASSED [  9%]
tests/test_cli.py::test_audit_prints_validation_error_and_exits_nonzero PASSED [ 10%]
tests/test_cli.py::test_audit_refuses_a_path_outside_sample_tasks PASSED [ 12%]
tests/test_cli.py::test_audit_command_stays_validation_only PASSED       [ 13%]
tests/test_hardcoded_solution.py::test_literal_return_is_confirmed_on_a_perturbed_input PASSED [ 15%]
tests/test_hardcoded_solution.py::test_computed_return_is_not_flagged PASSED [ 16%]
tests/test_hardcoded_solution.py::test_if_chain_on_literals_is_flagged_when_perturbation_changes PASSED [ 18%]
tests/test_hardcoded_solution.py::test_literal_return_with_no_arguments_is_flagged PASSED [ 20%]
tests/test_hardcoded_solution.py::test_subprocess_timeout_does_not_flag PASSED [ 21%]
tests/test_loader.py::test_valid_folder_loads_id_title_and_requirement_count PASSED [ 23%]
tests/test_loader.py::test_real_sample_task_loads_from_another_working_directory PASSED [ 24%]
tests/test_loader.py::test_missing_file_or_directory_names_the_path[task.yaml-task.yaml-required file is missing] PASSED [ 26%]
tests/test_loader.py::test_missing_file_or_directory_names_the_path[instruction.md-instruction.md-required file is missing] PASSED [ 27%]
tests/test_loader.py::test_missing_file_or_directory_names_the_path[solution/solution.py-solution/solution.py-required file is missing] PASSED [ 29%]
tests/test_loader.py::test_missing_file_or_directory_names_the_path[environment-environment-required directory is missing] PASSED [ 30%]
tests/test_loader.py::test_missing_file_or_directory_names_the_path[tests-tests-required directory is missing] PASSED [ 32%]
tests/test_loader.py::test_environment_file_is_rejected PASSED           [ 33%]
tests/test_loader.py::test_missing_pytest_file_names_the_pattern PASSED  [ 35%]
tests/test_loader.py::test_missing_field_names_the_field PASSED          [ 36%]
tests/test_loader.py::test_wrong_field_type_names_the_value PASSED       [ 38%]
tests/test_loader.py::test_unknown_field_names_the_value PASSED          [ 40%]
tests/test_loader.py::test_non_python_language_names_the_value PASSED    [ 41%]
tests/test_loader.py::test_empty_requirements_names_the_value PASSED     [ 43%]
tests/test_loader.py::test_duplicate_requirement_id_names_the_later_value PASSED [ 44%]
tests/test_loader.py::test_task_id_must_match_folder_name PASSED         [ 46%]
tests/test_loader.py::test_path_outside_sample_tasks_names_the_path PASSED [ 47%]
tests/test_loader.py::test_symlink_that_escapes_sample_tasks_is_refused PASSED [ 49%]
tests/test_loader.py::test_nested_path_inside_sample_tasks_is_refused PASSED [ 50%]
tests/test_loader.py::test_task_yaml_must_be_a_mapping PASSED            [ 52%]
tests/test_loader.py::test_invalid_yaml_names_the_parser_error PASSED    [ 53%]
tests/test_nondeterministic.py::test_nondeterministic_uses_are_flagged[import random\n\ndef test_roll() -> None:\n    assert random.random() >= 0\n-random.random] PASSED [ 55%]
tests/test_nondeterministic.py::test_nondeterministic_uses_are_flagged[import random\n\ndef test_imports_random() -> None:\n    assert True\n-imports random] PASSED [ 56%]
tests/test_nondeterministic.py::test_nondeterministic_uses_are_flagged[import time\n\ndef test_wait() -> None:\n    time.sleep(0)\n    assert True\n-time.sleep] PASSED [ 58%]
tests/test_nondeterministic.py::test_nondeterministic_uses_are_flagged[import time\n\ndef test_clock() -> None:\n    assert time.time() > 0\n-time.time] PASSED [ 60%]
tests/test_nondeterministic.py::test_nondeterministic_uses_are_flagged[import datetime\n\ndef test_year() -> None:\n    assert datetime.datetime.now().year > 2000\n-datetime.datetime.now] PASSED [ 61%]
tests/test_nondeterministic.py::test_nondeterministic_uses_are_flagged[import requests\n\ndef test_marker() -> None:\n    assert True\n-requests] PASSED [ 63%]
tests/test_nondeterministic.py::test_nondeterministic_uses_are_flagged[import socket\n\ndef test_open_socket() -> None:\n    assert socket.socket() is not None\n-socket] PASSED [ 64%]
tests/test_nondeterministic.py::test_nondeterministic_uses_are_flagged[import asyncio\n\ndef test_pause() -> None:\n    asyncio.sleep(0)\n-asyncio.sleep] PASSED [ 66%]
tests/test_nondeterministic.py::test_seeded_or_deterministic_code_is_not_flagged[def test_add() -> None:\n    assert 1 + 1 == 2\n] PASSED [ 67%]
tests/test_nondeterministic.py::test_seeded_or_deterministic_code_is_not_flagged[import random\n\ndef test_roll() -> None:\n    random.seed(1)\n    assert random.random() >= 0\n] PASSED [ 69%]
tests/test_nondeterministic.py::test_seeded_or_deterministic_code_is_not_flagged[import time\n\ndef test_year() -> None:\n    assert time.strftime("%Y", time.gmtime(0)) == "1970"\n] PASSED [ 70%]
tests/test_nondeterministic.py::test_random_instance_constructed_with_a_seed_is_not_flagged PASSED [ 72%]
tests/test_nondeterministic.py::test_later_unseeded_random_replaces_an_earlier_seed PASSED [ 73%]
tests/test_nondeterministic.py::test_fixture_that_freezes_time_is_not_flagged PASSED [ 75%]
tests/test_nondeterministic.py::test_unrelated_fixture_does_not_hide_datetime_now PASSED [ 76%]
tests/test_source_inspection.py::test_open_parse_and_membership_on_the_solution_are_flagged PASSED [ 78%]
tests/test_source_inspection.py::test_open_of_a_non_solution_path_is_ignored PASSED [ 80%]
tests/test_source_inspection.py::test_reassigned_path_is_not_treated_as_the_solution PASSED [ 81%]
tests/test_source_inspection.py::test_aliased_inspect_getsource_is_flagged PASSED [ 83%]
tests/test_static_checks.py::test_static_checks_are_registered PASSED    [ 84%]
tests/test_static_checks.py::test_run_static_checks_invokes_the_registry PASSED [ 86%]
tests/test_static_checks.py::test_slugify_sample_has_no_static_findings PASSED [ 87%]
tests/test_weak_assertion.py::test_weak_patterns_are_flagged[def test_calls() -> None:\n    build()\n-does not contain an assert] PASSED [ 89%]
tests/test_weak_assertion.py::test_weak_patterns_are_flagged[def test_always() -> None:\n    assert True\n-assert True] PASSED [ 90%]
tests/test_weak_assertion.py::test_weak_patterns_are_flagged[def test_present() -> None:\n    assert build() is not None\n-is not None] PASSED [ 92%]
tests/test_weak_assertion.py::test_weak_patterns_are_flagged[def test_kind() -> None:\n    assert isinstance(build(), int)\n-isinstance] PASSED [ 93%]
tests/test_weak_assertion.py::test_weak_patterns_are_flagged[def test_swallows() -> None:\n    try:\n        build()\n    except Exception:\n        pass\n-only passes] PASSED [ 95%]
tests/test_weak_assertion.py::test_real_equality_assert_is_not_flagged PASSED [ 96%]
tests/test_weak_assertion.py::test_real_assert_beside_assert_true_is_not_flagged PASSED [ 98%]
tests/test_weak_assertion.py::test_reraise_is_not_flagged PASSED         [100%]

============================== 65 passed in 0.82s ==============================
```

`auditor audit sample_tasks/slugify` still only validates (exit 0):

```
warning: later stages run task code and this is not a security sandbox
id: slugify
title: Turn a phrase into a URL slug
requirements: 2
```

`auditor audit /tmp` (exit 1):

```
warning: later stages run task code and this is not a security sandbox
error: path: must be inside sample_tasks (value: '/private/tmp')
```

Bugs found and fixed:
- The first pytest collection failed with `NameError: name '_Scope' is not defined`. The return annotation on `_Scope.child` was evaluated while the class body was still running. `from __future__ import annotations` defers that annotation.
- Ruff reported unsorted imports, lines over 88 characters, and two nested `if` statements. Formatting and combining those conditions cleared them.
- A name that once held a solution path kept that binding after a later assignment to a non-constant. `open()` of the new value could still look like the solution file. A new assignment now replaces the old path, source, and handle binding.
- The same name could be both a seeded `random.Random(seed)` and a later `random.Random()`. The seeded set was checked first, so the unseeded instance was ignored. The last assignment wins.
- `_TIME_CALLS` was a module-level set. It is now a frozenset. The check registry is a tuple.

Files changed:
`auditor/checks/__init__.py`, `auditor/checks/brittle_format.py`, `auditor/checks/hardcoded.py`, `auditor/checks/model.py`, `auditor/checks/nondeterministic.py`, `auditor/checks/parsing.py`, `auditor/checks/sandbox.py`, `auditor/checks/source_inspection.py`, `auditor/checks/target.py`, `auditor/checks/weak_assertion.py`, `tests/check_support.py`, `tests/test_brittle_format.py`, `tests/test_cli.py`, `tests/test_hardcoded_solution.py`, `tests/test_nondeterministic.py`, `tests/test_source_inspection.py`, `tests/test_static_checks.py`, `tests/test_weak_assertion.py`.

Decisions and open questions:
- Severity is `high`, `medium`, or `low`. High means the task can pass without the behavior the instruction describes: `source_inspection_test` and `hardcoded_solution`. Medium means the assertion is too weak, or it demands an exact string the instruction never gives: `weak_assertion` and `brittle_format`. Low means the result can change without a solution change: `nondeterministic_test`.
- `open()` of a non-solution path is ignored. A solution path has the file name `solution.py`, or a `solution` directory component and a `.py` suffix. A path this checker cannot resolve to a string is ignored. `inspect.getsource` and `ast.parse` are flagged on every call, including `import inspect as ins`. Membership is flagged only for `in` when the right side was read from the solution file or from `getsource`. A string literal on the right, and `not in`, are not flagged. `pathlib.Path.read_text` and `os.path.join` are not resolved.
- A real assert anywhere in a test suppresses `weak_assertion`, including a real assert beside `assert True` and a real assert beside `except: pass`. `assert x` counts as real. `pytest.raises` does not, so a test that only uses it is reported as having no assert. `!= None` is not the `is not None` pattern. A handler counts as swallowing errors only when its body is exclusively `pass`. A handler that re-raises, with no assert and no pass-only handler, is not flagged. One finding is reported per test.
- `hardcoded_solution` does not import or exec the solution in the auditor process. A child process runs `sys.executable -I` with a 2 second timeout. The child environment is only `PATH`, when set, and `PYTHONDONTWRITEBYTECODE`. Results are written to a file. The original call must JSON-equal the test literal. The first argument is perturbed: a string gains a trailing `q`, an int or float increases by 1, and a bool flips. No arguments, or an argument of another type, is reported as no input to perturb. Timeout, crash, or a non-JSON value is not flagged. False positives still expected: a correct function whose specified result is a constant, and a correct literal lookup table. False negatives: a keyword argument, an expected value that is not a literal, a conditional expression such as `return "a" if x else "b"`, a function with no return statement, and a child that times out or crashes.
- `brittle_format` uses a cutoff of 40 characters. A 40-character string can flag. A 39-character string does not. The instruction specifies that format only when it contains the exact string. The words "json" and "format" do not count. An f-string is not flagged. A long string that appears only as sample input is treated as specified, which can hide a real format demand.
- A seed is `random.seed(...)` anywhere in the file, or `random.Random(...)` with at least one argument. `random.Random()` is not a seed. A seeded instance covers calls on that name only. One `random.seed` covers random-module calls for the whole file, even in a later line or a dead branch. `import random` is flagged only when the file has no seed, no `Random` instance, and no random call. `import time` alone is not flagged. A time fixture is `@pytest.fixture` or `@fixture` whose body mentions `freeze_time`, the attribute `now`, or the strings "now", "time.time", or "sleep". It covers `time.time`, `time.time_ns`, `time.sleep`, `asyncio.sleep`, and `datetime.now` only in tests that take that fixture as a parameter. `@pytest.mark.usefixtures` and `@freeze_time` on the test are not recognized. Network imports and calls are always flagged. The network modules are `socket`, `requests`, `httpx`, `aiohttp`, `urllib.request`, and `http.client`. There is no network-fixture escape.
- These snippet tests, and the clean result on `slugify`, were written by the same author as the checks. That is weak evidence about precision and recall.

Next stage:
Stage 3: coverage checks 6 and 7, plus the requirement coverage percentage. Waiting for "next".

## Stage 3: coverage checks 6 and 7 (commit 9c5930e856b28119cbf13c6a29240e5eb53f55f2)
What was built:
`untested_requirement` and `hidden_requirement`, registered as `COVERAGE_CHECKS`, plus `requirement_coverage`. Both checks read `@covers` from the AST. They do not import or run the task tests. Checks 1 to 5 were not modified. `CHECKS` and `run_static_checks` still run only those five rules. `auditor audit` still only validates a task folder.

A requirement is covered when at least one test has a `@covers` decorator whose string argument is that id. Every decorator on the function counts. The invented `slugify` sample reports both requirements covered, coverage `2/2`, and no coverage findings.

The snippet tests were written by the same author as the checks. Passing them is weak evidence.

Commands run and their real output:
```
.venv/bin/ruff check .
All checks passed!

.venv/bin/ruff format --check .
38 files already formatted

.venv/bin/mypy
Success: no issues found in 29 source files

.venv/bin/pytest -v
============================= test session starts ==============================
platform darwin -- Python 3.11.14, pytest-9.2.0, pluggy-1.7.0 -- /Users/shubhambaviskar/Desktop/Eval Task Auditor/.venv/bin/python3
cachedir: .pytest_cache
rootdir: /Users/shubhambaviskar/Desktop/Eval Task Auditor
configfile: pyproject.toml
testpaths: tests
collecting ... collected 81 items

tests/test_brittle_format.py::test_cutoff_is_40_characters PASSED        [  1%]
tests/test_brittle_format.py::test_long_string_equality_without_a_specified_format_is_flagged PASSED [  2%]
tests/test_brittle_format.py::test_numeric_equality_is_not_flagged PASSED [  3%]
tests/test_brittle_format.py::test_same_literal_is_not_flagged_when_the_instruction_specifies_it PASSED [  4%]
tests/test_brittle_format.py::test_short_string_equality_is_not_flagged PASSED [  6%]
tests/test_cli.py::test_audit_prints_id_title_count_and_sandbox_warning PASSED [  7%]
tests/test_cli.py::test_audit_prints_validation_error_and_exits_nonzero PASSED [  8%]
tests/test_cli.py::test_audit_refuses_a_path_outside_sample_tasks PASSED [  9%]
tests/test_cli.py::test_audit_command_stays_validation_only PASSED       [ 11%]
tests/test_coverage.py::test_coverage_checks_are_registered PASSED       [ 12%]
tests/test_coverage.py::test_untested_requirement_names_the_missing_id PASSED [ 13%]
tests/test_coverage.py::test_covered_requirements_are_not_flagged_as_untested PASSED [ 14%]
tests/test_coverage.py::test_two_decorators_on_one_test_cover_both_ids PASSED [ 16%]
tests/test_coverage.py::test_alias_of_covers_is_not_recognized PASSED    [ 17%]
tests/test_coverage.py::test_test_without_covers_is_hidden PASSED        [ 18%]
tests/test_coverage.py::test_unknown_covers_id_is_hidden PASSED          [ 19%]
tests/test_coverage.py::test_ordinary_equality_is_not_a_hidden_error PASSED [ 20%]
tests/test_coverage.py::test_pytest_raises_match_absent_from_the_instruction_is_flagged PASSED [ 22%]
tests/test_coverage.py::test_same_error_message_is_not_flagged_when_the_instruction_contains_it PASSED [ 23%]
tests/test_coverage.py::test_exception_string_equality_absent_from_the_instruction_is_flagged PASSED [ 24%]
tests/test_coverage.py::test_coverage_is_zero_one_and_two_of_two PASSED  [ 25%]
tests/test_coverage.py::test_zero_requirements_uses_zero PASSED          [ 27%]
tests/test_coverage.py::test_slugify_sample_covers_both_requirements PASSED [ 28%]
tests/test_coverage.py::test_static_runner_does_not_run_coverage_checks PASSED [ 29%]
tests/test_coverage.py::test_coverage_module_does_not_import_or_run_tests PASSED [ 30%]
tests/test_hardcoded_solution.py::test_literal_return_is_confirmed_on_a_perturbed_input PASSED [ 32%]
tests/test_hardcoded_solution.py::test_computed_return_is_not_flagged PASSED [ 33%]
tests/test_hardcoded_solution.py::test_if_chain_on_literals_is_flagged_when_perturbation_changes PASSED [ 34%]
tests/test_hardcoded_solution.py::test_literal_return_with_no_arguments_is_flagged PASSED [ 35%]
tests/test_hardcoded_solution.py::test_subprocess_timeout_does_not_flag PASSED [ 37%]
tests/test_loader.py::test_valid_folder_loads_id_title_and_requirement_count PASSED [ 38%]
tests/test_loader.py::test_real_sample_task_loads_from_another_working_directory PASSED [ 39%]
tests/test_loader.py::test_missing_file_or_directory_names_the_path[task.yaml-task.yaml-required file is missing] PASSED [ 40%]
tests/test_loader.py::test_missing_file_or_directory_names_the_path[instruction.md-instruction.md-required file is missing] PASSED [ 41%]
tests/test_loader.py::test_missing_file_or_directory_names_the_path[solution/solution.py-solution/solution.py-required file is missing] PASSED [ 43%]
tests/test_loader.py::test_missing_file_or_directory_names_the_path[environment-environment-required directory is missing] PASSED [ 44%]
tests/test_loader.py::test_missing_file_or_directory_names_the_path[tests-tests-required directory is missing] PASSED [ 45%]
tests/test_loader.py::test_environment_file_is_rejected PASSED           [ 46%]
tests/test_loader.py::test_missing_pytest_file_names_the_pattern PASSED  [ 48%]
tests/test_loader.py::test_missing_field_names_the_field PASSED          [ 49%]
tests/test_loader.py::test_wrong_field_type_names_the_value PASSED       [ 50%]
tests/test_loader.py::test_unknown_field_names_the_value PASSED          [ 51%]
tests/test_loader.py::test_non_python_language_names_the_value PASSED    [ 53%]
tests/test_loader.py::test_empty_requirements_names_the_value PASSED     [ 54%]
tests/test_loader.py::test_duplicate_requirement_id_names_the_later_value PASSED [ 55%]
tests/test_loader.py::test_task_id_must_match_folder_name PASSED         [ 56%]
tests/test_loader.py::test_path_outside_sample_tasks_names_the_path PASSED [ 58%]
tests/test_loader.py::test_symlink_that_escapes_sample_tasks_is_refused PASSED [ 59%]
tests/test_loader.py::test_nested_path_inside_sample_tasks_is_refused PASSED [ 60%]
tests/test_loader.py::test_task_yaml_must_be_a_mapping PASSED            [ 61%]
tests/test_loader.py::test_invalid_yaml_names_the_parser_error PASSED    [ 62%]
tests/test_nondeterministic.py::test_nondeterministic_uses_are_flagged[import random\n\ndef test_roll() -> None:\n    assert random.random() >= 0\n-random.random] PASSED [ 64%]
tests/test_nondeterministic.py::test_nondeterministic_uses_are_flagged[import random\n\ndef test_imports_random() -> None:\n    assert True\n-imports random] PASSED [ 65%]
tests/test_nondeterministic.py::test_nondeterministic_uses_are_flagged[import time\n\ndef test_wait() -> None:\n    time.sleep(0)\n    assert True\n-time.sleep] PASSED [ 66%]
tests/test_nondeterministic.py::test_nondeterministic_uses_are_flagged[import time\n\ndef test_clock() -> None:\n    assert time.time() > 0\n-time.time] PASSED [ 67%]
tests/test_nondeterministic.py::test_nondeterministic_uses_are_flagged[import datetime\n\ndef test_year() -> None:\n    assert datetime.datetime.now().year > 2000\n-datetime.datetime.now] PASSED [ 69%]
tests/test_nondeterministic.py::test_nondeterministic_uses_are_flagged[import requests\n\ndef test_marker() -> None:\n    assert True\n-requests] PASSED [ 70%]
tests/test_nondeterministic.py::test_nondeterministic_uses_are_flagged[import socket\n\ndef test_open_socket() -> None:\n    assert socket.socket() is not None\n-socket] PASSED [ 71%]
tests/test_nondeterministic.py::test_nondeterministic_uses_are_flagged[import asyncio\n\ndef test_pause() -> None:\n    asyncio.sleep(0)\n-asyncio.sleep] PASSED [ 72%]
tests/test_nondeterministic.py::test_seeded_or_deterministic_code_is_not_flagged[def test_add() -> None:\n    assert 1 + 1 == 2\n] PASSED [ 74%]
tests/test_nondeterministic.py::test_seeded_or_deterministic_code_is_not_flagged[import random\n\ndef test_roll() -> None:\n    random.seed(1)\n    assert random.random() >= 0\n] PASSED [ 75%]
tests/test_nondeterministic.py::test_seeded_or_deterministic_code_is_not_flagged[import time\n\ndef test_year() -> None:\n    assert time.strftime("%Y", time.gmtime(0)) == "1970"\n] PASSED [ 76%]
tests/test_nondeterministic.py::test_random_instance_constructed_with_a_seed_is_not_flagged PASSED [ 77%]
tests/test_nondeterministic.py::test_later_unseeded_random_replaces_an_earlier_seed PASSED [ 79%]
tests/test_nondeterministic.py::test_fixture_that_freezes_time_is_not_flagged PASSED [ 80%]
tests/test_nondeterministic.py::test_unrelated_fixture_does_not_hide_datetime_now PASSED [ 81%]
tests/test_source_inspection.py::test_open_parse_and_membership_on_the_solution_are_flagged PASSED [ 82%]
tests/test_source_inspection.py::test_open_of_a_non_solution_path_is_ignored PASSED [ 83%]
tests/test_source_inspection.py::test_reassigned_path_is_not_treated_as_the_solution PASSED [ 85%]
tests/test_source_inspection.py::test_aliased_inspect_getsource_is_flagged PASSED [ 86%]
tests/test_static_checks.py::test_static_checks_are_registered PASSED    [ 87%]
tests/test_static_checks.py::test_run_static_checks_invokes_the_registry PASSED [ 88%]
tests/test_static_checks.py::test_slugify_sample_has_no_static_findings PASSED [ 90%]
tests/test_weak_assertion.py::test_weak_patterns_are_flagged[def test_calls() -> None:\n    build()\n-does not contain an assert] PASSED [ 91%]
tests/test_weak_assertion.py::test_weak_patterns_are_flagged[def test_always() -> None:\n    assert True\n-assert True] PASSED [ 92%]
tests/test_weak_assertion.py::test_weak_patterns_are_flagged[def test_present() -> None:\n    assert build() is not None\n-is not None] PASSED [ 93%]
tests/test_weak_assertion.py::test_weak_patterns_are_flagged[def test_kind() -> None:\n    assert isinstance(build(), int)\n-isinstance] PASSED [ 95%]
tests/test_weak_assertion.py::test_weak_patterns_are_flagged[def test_swallows() -> None:\n    try:\n        build()\n    except Exception:\n        pass\n-only passes] PASSED [ 96%]
tests/test_weak_assertion.py::test_real_equality_assert_is_not_flagged PASSED [ 97%]
tests/test_weak_assertion.py::test_real_assert_beside_assert_true_is_not_flagged PASSED [ 98%]
tests/test_weak_assertion.py::test_reraise_is_not_flagged PASSED         [100%]

============================== 81 passed in 0.85s ==============================
```

`auditor audit sample_tasks/slugify` still only validates (exit 0):

```
warning: later stages run task code and this is not a security sandbox
id: slugify
title: Turn a phrase into a URL slug
requirements: 2
```

`auditor audit /tmp` (exit 1):

```
warning: later stages run task code and this is not a security sandbox
error: path: must be inside sample_tasks (value: '/private/tmp')
```

Bugs found and fixed:
None. The first ruff, mypy, and pytest run passed. Review did not find a defect in the checker. Limitations that were already in the code were written into the module docstring before the commit.

Files changed:
`auditor/checks/__init__.py`, `auditor/checks/model.py`, `auditor/checks/target.py`, `auditor/checks/coverage.py`, `tests/check_support.py`, `tests/test_cli.py`, `tests/test_coverage.py`.

Decisions and open questions:
- `untested_requirement` is high: the suite can pass while that requirement's behavior is absent. `hidden_requirement` is medium: the test checks an id or an error string the task does not publish. Ordinary `assert result == "text"` stays with `brittle_format`.
- The recognized name is `covers`, including an attribute such as `conftest.covers`. `from conftest import covers as mark` is not recognized, so `@mark("R1")` covers nothing. A non-empty string literal counts as a positional argument or as the keyword `requirement_id`. A bare `@covers`, a non-literal argument, and a decorator on the class are not markers. `@covers("R2")` above `@covers("R1")` covers both ids. The sample helper would keep only the last id on `__covers__`.
- An exact error message is a keyword `match` on `pytest.raises` or `raises`, or `==` with `str` or `repr` of an `except ... as` name, that name itself, `.args`, or `.value` on a `pytest.raises(...) as` name. A positional match and an f-string are not read. The `except` name applies to the whole test, including a nested function, and a later assignment does not clear it. The match text is not evaluated as a regex. A message is not flagged when its exact text appears in `instruction.md`, including inside a longer sentence. Comparison is case sensitive.
- Requirement coverage is covered requirements divided by the total. Tests assert `0/2`, `1/2`, and `2/2`. A total of 0 returns `0.0` and does not divide by zero. Markers on a target with no requirements are hidden ids, because those ids are not in the requirement list. A missing or unreadable `task.yaml` contributes no ids, so that target's percentage is `0.0`. Duplicate ids in the tuple each count toward the total; the finding names an uncovered id once. The loader still rejects duplicate ids in a real task.
- `StaticTarget` gained `requirements`, defaulting to `()`. Checks 1 to 5 do not read it. `target_from_task` now reads requirement ids from `task.yaml` and still does not import tests.
- These snippet tests, and the clean `slugify` result, were written by the same author as the checks. That is weak evidence about precision and recall.

Next stage:
Stage 4: dynamic checks 8 to 10, in a subprocess with a timeout, a temp directory, and no network. Waiting for "next".

## Stage 4: dynamic checks 8 to 10 (commit c065cc10e2414a585da2ea8a792f95ab4c125091)
What was built:
`solution_fails_tests`, `cheat_solution_passes`, and `flaky_tests`, registered as `DYNAMIC_CHECKS`. Task code runs only in a child process, in a temp directory, with a 2 second timeout. The auditor process does not import the task. Files are copied. `sample_tasks` is not modified. Checks 1 to 7 were not modified, and their registries are unchanged. `auditor audit` still only validates a task folder. The existing sandbox warning is unchanged.

Copy rule: each top-level `environment/*.py` module, other than `__init__.py`, is replaced in the temp directory by `solution/solution.py` under that same file name. `tests/` is copied to the temp root. For slugify, `from slugify import slugify` loads the reference solution, not the starter that raises `NotImplementedError`.

The tests were written by the same author as the checks. Passing them is weak evidence.

Commands run and their real output:
```
.venv/bin/ruff check .
All checks passed!

.venv/bin/ruff format --check .
40 files already formatted

.venv/bin/mypy
Success: no issues found in 31 source files

.venv/bin/pytest -v
============================= test session starts ==============================
platform darwin -- Python 3.11.14, pytest-9.2.0, pluggy-1.7.0 -- /Users/shubhambaviskar/Desktop/Eval Task Auditor/.venv/bin/python3
cachedir: .pytest_cache
rootdir: /Users/shubhambaviskar/Desktop/Eval Task Auditor
configfile: pyproject.toml
testpaths: tests
collecting ... collected 89 items

tests/test_brittle_format.py::test_cutoff_is_40_characters PASSED        [  1%]
tests/test_brittle_format.py::test_long_string_equality_without_a_specified_format_is_flagged PASSED [  2%]
tests/test_brittle_format.py::test_numeric_equality_is_not_flagged PASSED [  3%]
tests/test_brittle_format.py::test_same_literal_is_not_flagged_when_the_instruction_specifies_it PASSED [  4%]
tests/test_brittle_format.py::test_short_string_equality_is_not_flagged PASSED [  5%]
tests/test_cli.py::test_audit_prints_id_title_count_and_sandbox_warning PASSED [  6%]
tests/test_cli.py::test_audit_prints_validation_error_and_exits_nonzero PASSED [  7%]
tests/test_cli.py::test_audit_refuses_a_path_outside_sample_tasks PASSED [  8%]
tests/test_cli.py::test_audit_command_stays_validation_only PASSED       [ 10%]
tests/test_coverage.py::test_coverage_checks_are_registered PASSED       [ 11%]
tests/test_coverage.py::test_untested_requirement_names_the_missing_id PASSED [ 12%]
tests/test_coverage.py::test_covered_requirements_are_not_flagged_as_untested PASSED [ 13%]
tests/test_coverage.py::test_two_decorators_on_one_test_cover_both_ids PASSED [ 14%]
tests/test_coverage.py::test_alias_of_covers_is_not_recognized PASSED    [ 15%]
tests/test_coverage.py::test_test_without_covers_is_hidden PASSED        [ 16%]
tests/test_coverage.py::test_unknown_covers_id_is_hidden PASSED          [ 17%]
tests/test_coverage.py::test_ordinary_equality_is_not_a_hidden_error PASSED [ 19%]
tests/test_coverage.py::test_pytest_raises_match_absent_from_the_instruction_is_flagged PASSED [ 20%]
tests/test_coverage.py::test_same_error_message_is_not_flagged_when_the_instruction_contains_it PASSED [ 21%]
tests/test_coverage.py::test_exception_string_equality_absent_from_the_instruction_is_flagged PASSED [ 22%]
tests/test_coverage.py::test_coverage_is_zero_one_and_two_of_two PASSED  [ 23%]
tests/test_coverage.py::test_zero_requirements_uses_zero PASSED          [ 24%]
tests/test_coverage.py::test_slugify_sample_covers_both_requirements PASSED [ 25%]
tests/test_coverage.py::test_static_runner_does_not_run_coverage_checks PASSED [ 26%]
tests/test_coverage.py::test_coverage_module_does_not_import_or_run_tests PASSED [ 28%]
tests/test_dynamic.py::test_dynamic_checks_are_registered PASSED         [ 29%]
tests/test_dynamic.py::test_slugify_imports_the_reference_solution PASSED [ 30%]
tests/test_dynamic.py::test_slugify_has_no_dynamic_findings PASSED       [ 31%]
tests/test_dynamic.py::test_wrong_solution_is_flagged_and_a_consistent_failure_is_not_flaky PASSED [ 32%]
tests/test_dynamic.py::test_first_argument_cheat_passes_and_the_others_do_not PASSED [ 33%]
tests/test_dynamic.py::test_counter_file_forces_a_flaky_result PASSED    [ 34%]
tests/test_dynamic.py::test_hanging_child_returns_within_the_timeout PASSED [ 35%]
tests/test_dynamic.py::test_child_cannot_open_a_tcp_socket PASSED        [ 37%]
tests/test_hardcoded_solution.py::test_literal_return_is_confirmed_on_a_perturbed_input PASSED [ 38%]
tests/test_hardcoded_solution.py::test_computed_return_is_not_flagged PASSED [ 39%]
tests/test_hardcoded_solution.py::test_if_chain_on_literals_is_flagged_when_perturbation_changes PASSED [ 40%]
tests/test_hardcoded_solution.py::test_literal_return_with_no_arguments_is_flagged PASSED [ 41%]
tests/test_hardcoded_solution.py::test_subprocess_timeout_does_not_flag PASSED [ 42%]
tests/test_loader.py::test_valid_folder_loads_id_title_and_requirement_count PASSED [ 43%]
tests/test_loader.py::test_real_sample_task_loads_from_another_working_directory PASSED [ 44%]
tests/test_loader.py::test_missing_file_or_directory_names_the_path[task.yaml-task.yaml-required file is missing] PASSED [ 46%]
tests/test_loader.py::test_missing_file_or_directory_names_the_path[instruction.md-instruction.md-required file is missing] PASSED [ 47%]
tests/test_loader.py::test_missing_file_or_directory_names_the_path[solution/solution.py-solution/solution.py-required file is missing] PASSED [ 48%]
tests/test_loader.py::test_missing_file_or_directory_names_the_path[environment-environment-required directory is missing] PASSED [ 49%]
tests/test_loader.py::test_missing_file_or_directory_names_the_path[tests-tests-required directory is missing] PASSED [ 50%]
tests/test_loader.py::test_environment_file_is_rejected PASSED           [ 51%]
tests/test_loader.py::test_missing_pytest_file_names_the_pattern PASSED  [ 52%]
tests/test_loader.py::test_missing_field_names_the_field PASSED          [ 53%]
tests/test_loader.py::test_wrong_field_type_names_the_value PASSED       [ 55%]
tests/test_loader.py::test_unknown_field_names_the_value PASSED          [ 56%]
tests/test_loader.py::test_non_python_language_names_the_value PASSED    [ 57%]
tests/test_loader.py::test_empty_requirements_names_the_value PASSED     [ 58%]
tests/test_loader.py::test_duplicate_requirement_id_names_the_later_value PASSED [ 59%]
tests/test_loader.py::test_task_id_must_match_folder_name PASSED         [ 60%]
tests/test_loader.py::test_path_outside_sample_tasks_names_the_path PASSED [ 61%]
tests/test_loader.py::test_symlink_that_escapes_sample_tasks_is_refused PASSED [ 62%]
tests/test_loader.py::test_nested_path_inside_sample_tasks_is_refused PASSED [ 64%]
tests/test_loader.py::test_task_yaml_must_be_a_mapping PASSED            [ 65%]
tests/test_loader.py::test_invalid_yaml_names_the_parser_error PASSED    [ 66%]
tests/test_nondeterministic.py::test_nondeterministic_uses_are_flagged[import random\n\ndef test_roll() -> None:\n    assert random.random() >= 0\n-random.random] PASSED [ 67%]
tests/test_nondeterministic.py::test_nondeterministic_uses_are_flagged[import random\n\ndef test_imports_random() -> None:\n    assert True\n-imports random] PASSED [ 68%]
tests/test_nondeterministic.py::test_nondeterministic_uses_are_flagged[import time\n\ndef test_wait() -> None:\n    time.sleep(0)\n    assert True\n-time.sleep] PASSED [ 69%]
tests/test_nondeterministic.py::test_nondeterministic_uses_are_flagged[import time\n\ndef test_clock() -> None:\n    assert time.time() > 0\n-time.time] PASSED [ 70%]
tests/test_nondeterministic.py::test_nondeterministic_uses_are_flagged[import datetime\n\ndef test_year() -> None:\n    assert datetime.datetime.now().year > 2000\n-datetime.datetime.now] PASSED [ 71%]
tests/test_nondeterministic.py::test_nondeterministic_uses_are_flagged[import requests\n\ndef test_marker() -> None:\n    assert True\n-requests] PASSED [ 73%]
tests/test_nondeterministic.py::test_nondeterministic_uses_are_flagged[import socket\n\ndef test_open_socket() -> None:\n    assert socket.socket() is not None\n-socket] PASSED [ 74%]
tests/test_nondeterministic.py::test_nondeterministic_uses_are_flagged[import asyncio\n\ndef test_pause() -> None:\n    asyncio.sleep(0)\n-asyncio.sleep] PASSED [ 75%]
tests/test_nondeterministic.py::test_seeded_or_deterministic_code_is_not_flagged[def test_add() -> None:\n    assert 1 + 1 == 2\n] PASSED [ 76%]
tests/test_nondeterministic.py::test_seeded_or_deterministic_code_is_not_flagged[import random\n\ndef test_roll() -> None:\n    random.seed(1)\n    assert random.random() >= 0\n] PASSED [ 77%]
tests/test_nondeterministic.py::test_seeded_or_deterministic_code_is_not_flagged[import time\n\ndef test_year() -> None:\n    assert time.strftime("%Y", time.gmtime(0)) == "1970"\n] PASSED [ 78%]
tests/test_nondeterministic.py::test_random_instance_constructed_with_a_seed_is_not_flagged PASSED [ 79%]
tests/test_nondeterministic.py::test_later_unseeded_random_replaces_an_earlier_seed PASSED [ 80%]
tests/test_nondeterministic.py::test_fixture_that_freezes_time_is_not_flagged PASSED [ 82%]
tests/test_nondeterministic.py::test_unrelated_fixture_does_not_hide_datetime_now PASSED [ 83%]
tests/test_source_inspection.py::test_open_parse_and_membership_on_the_solution_are_flagged PASSED [ 84%]
tests/test_source_inspection.py::test_open_of_a_non_solution_path_is_ignored PASSED [ 85%]
tests/test_source_inspection.py::test_reassigned_path_is_not_treated_as_the_solution PASSED [ 86%]
tests/test_source_inspection.py::test_aliased_inspect_getsource_is_flagged PASSED [ 87%]
tests/test_static_checks.py::test_static_checks_are_registered PASSED    [ 88%]
tests/test_static_checks.py::test_run_static_checks_invokes_the_registry PASSED [ 89%]
tests/test_static_checks.py::test_slugify_sample_has_no_static_findings PASSED [ 91%]
tests/test_weak_assertion.py::test_weak_patterns_are_flagged[def test_calls() -> None:\n    build()\n-does not contain an assert] PASSED [ 92%]
tests/test_weak_assertion.py::test_weak_patterns_are_flagged[def test_always() -> None:\n    assert True\n-assert True] PASSED [ 93%]
tests/test_weak_assertion.py::test_weak_patterns_are_flagged[def test_present() -> None:\n    assert build() is not None\n-is not None] PASSED [ 94%]
tests/test_weak_assertion.py::test_weak_patterns_are_flagged[def test_kind() -> None:\n    assert isinstance(build(), int)\n-isinstance] PASSED [ 95%]
tests/test_weak_assertion.py::test_weak_patterns_are_flagged[def test_swallows() -> None:\n    try:\n        build()\n    except Exception:\n        pass\n-only passes] PASSED [ 96%]
tests/test_weak_assertion.py::test_real_equality_assert_is_not_flagged PASSED [ 97%]
tests/test_weak_assertion.py::test_real_assert_beside_assert_true_is_not_flagged PASSED [ 98%]
tests/test_weak_assertion.py::test_reraise_is_not_flagged PASSED         [100%]

============================== 89 passed in 6.54s ==============================
```

`run_dynamic_checks` on `sample_tasks/slugify`:

```
no dynamic findings
```

`run_dynamic_checks` on an invented temp task whose solution returns `"no"` while the test expects `echo("hi") == "HI"`. The folder was not under `sample_tasks` and was deleted afterward.

```
solution_fails_tests [high] solution/solution.py
Reference solution failed its tests with pytest exit code 1.
```

`auditor audit sample_tasks/slugify` (exit 0):

```
warning: later stages run task code and this is not a security sandbox
id: slugify
title: Turn a phrase into a URL slug
requirements: 2
```

`auditor audit /tmp` (exit 1):

```
warning: later stages run task code and this is not a security sandbox
error: path: must be inside sample_tasks (value: '/private/tmp')
```

Bugs found and fixed:
- The first wrong-solution fixture expected `echo("hi") == "hi"` while the reference returned `"no"`. `solution_fails_tests` fired, and the first-argument cheat also passed, because the tests accepted the input unchanged. The fixture now expects `"HI"`, which none of the four cheats produce. A consistent failure is only `solution_fails_tests`.
- A module with no function would have been unparsed and run again. If the tests passed, every cheat would have been flagged even though no body changed. A cheat that rewrites nothing is skipped.

Files changed:
`auditor/checks/__init__.py`, `auditor/checks/dynamic.py`, `tests/test_cli.py`, `tests/test_dynamic.py`.

Decisions and open questions:
- Each child is limited to `DYNAMIC_TIMEOUT_SECONDS`, which is 2 seconds. `subprocess.run` kills the child when that expires, and the call returns. A hang test with the limit patched to 0.5 seconds returned in under 5 seconds. A correct suite that needs longer than 2 seconds is reported as not passing.
- `solution_fails_tests` and `cheat_solution_passes` are high. `flaky_tests` is low, because the pass/fail result changed without a solution change. Flaky runs the suite 3 times in one temp directory. The unit test forces the difference with a counter file (`passed, failed, failed`). It does not use a random chance.
- The cheats are return None, return 0, an empty function body, and return the first argument. They rewrite module-level functions only. Class methods and lambdas are not rewritten. A function with no positional parameter uses `return None` for the first-argument cheat. A cheat that times out or errors did not pass, so it is not flagged. slugify flags none of them. A separate invented echo task flags only the first-argument cheat.
- Network block: before pytest starts, the child replaces `socket.socket` so the default family, `AF_INET`, and `AF_INET6` raise `OSError("network access is blocked")`. `connect`, `connect_ex`, and `socket.create_connection` raise the same error. A test listens on `127.0.0.1` and the child cannot connect. This is not a security sandbox. The block still allows `AF_UNIX` sockets, local files, a subprocess (the patch is not inherited), ctypes and other direct system calls, and task code that restores or reloads `socket.socket`. The CLI warning stays: later stages run task code and this is not a security sandbox.
- The child environment copies `PATH` and sets `PYTHONDONTWRITEBYTECODE`. Other parent variables are not copied. A `pytest.ini` in the temp directory keeps pytest from using this project's config.
- These tests, and the clean slugify result, were written by the same author as the checks. That is weak evidence about precision and recall.

Next stage:
Stage 5: mutation testing, check 11, with a fixed seed. Waiting for "next".
