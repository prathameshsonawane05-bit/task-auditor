# Design

TaskAuditor checks an invented task folder and writes findings, a requirement-coverage fraction, and a mutation score. The numbers from the labeled runs are in [EVALUATION.md](EVALUATION.md), under the headings v1 and Held-out. Those tables are the record. This page does not repeat them.

## Task folder

A task is one directory directly inside `sample_tasks/<task_id>/`:

```text
task.yaml
instruction.md
environment/
solution/solution.py
tests/test_*.py
tests/conftest.py
```

`task.yaml` has `id`, `title`, `language: python`, and `requirements`, a list of `{id, text}`. The folder name matches `id`. Each test that covers a published requirement uses `@covers("R1")`. The helper is `covers` in `tests/conftest.py`. The loader rejects a missing file, a bad field, a language other than Python, and any path that is not directly inside `sample_tasks`.

`expected_findings.yaml` may sit beside the task. It is a YAML list of check names. A clean task has `[]`. The loader ignores the file. The checks do not read it. The quality test does.

`held_out_tasks/` uses the same folder shape. The audit command does not accept it. The held-out count was a separate run, recorded in EVALUATION.md, and the tasks were not changed afterward.

## Four registries

Checks return `Finding` values: `check`, `severity`, `location`, and a one-sentence `explanation`.

| Registry | Where | Input | What calls it |
| --- | --- | --- | --- |
| `CHECKS` | `auditor/checks/__init__.py` | `StaticTarget` | `run_static_checks` |
| `COVERAGE_CHECKS` | `auditor/checks/__init__.py` | `StaticTarget` | `run_coverage_checks` |
| `DYNAMIC_CHECKS` | `auditor/checks/dynamic.py` | task directory | `run_dynamic_checks` |
| `MUTATION_CHECKS` | `auditor/checks/mutation.py` | task directory | `run_surviving_mutants` |

`CHECKS` is checks 1 to 5: `source_inspection_test`, `weak_assertion`, `hardcoded_solution`, `brittle_format`, `nondeterministic_test`. They read source. They do not run pytest.

`COVERAGE_CHECKS` is checks 6 and 7: `untested_requirement` and `hidden_requirement`. `requirement_coverage` is covered requirement ids divided by the total. A total of 0 yields 0.0. That fraction is not itself a finding.

`DYNAMIC_CHECKS` is checks 8 to 10: `solution_fails_tests`, `cheat_solution_passes`, `flaky_tests`.

`MUTATION_CHECKS` is check 11, `surviving_mutants`. `auditor/run.py` calls `measure_mutations` once and adds the survivors to the report. It does not also call `run_surviving_mutants`, and it does not append check 11 to `DYNAMIC_CHECKS`. The score is killed divided by total. A total of 0 scores 0.0 and produces no finding by itself.

`auditor audit` loads the task, calls `run_audit`, and writes `<id>.json` and `<id>.md`.

## Temp-directory runner

Checks 8 to 11 run task code in a child process. The auditor process does not import the task. `sample_tasks` is not modified.

The copy rule replaces each top-level `environment/*.py` module, other than `__init__.py`, with the text of `solution/solution.py`, using the environment file's name. `tests/` is copied to the temp root. A `pytest.ini` in that temp root stops pytest from walking up to this project's config. The child is `sys.executable -I`, with a working directory of the temp root, and an environment that keeps `PATH` when it is set and sets `PYTHONDONTWRITEBYTECODE=1`. The timeout is 2 seconds. A timeout, a crash, or a missing results file is not a pass.

Before pytest starts, the child replaces `socket.socket` so the default family, `AF_INET`, and `AF_INET6` raise `OSError("network access is blocked")`. `connect`, `connect_ex`, and `socket.create_connection` raise the same error. This is not a security sandbox. The block does not stop `AF_UNIX` sockets, local files, a subprocess, ctypes and other direct system calls, or task code that restores or reloads `socket.socket`.

Cheats rewrite module-level functions only: return `None`, return `0`, an empty body, and return the first argument. A module with no function skips the cheats. A timeout or an error is not a passing cheat. Flaky runs the suite three times in one temp directory.

Mutation builds mutants with `ast` and runs each one through the same runner. The operator map swaps `==` with `!=`, `<` with `>=`, `<=` with `>`, `>` with `<=`, `>=` with `<`, `is` with `is not`, `in` with `not in`, and `and` with `or`. Numeric constants move by 1, floats by 1.0. `True` and `False` are not mutated. `while` and `for` are not branches. Deleting a branch applies to `if` statements and `if` expressions. A mutant that still passes is a survivor. A timeout counts as killed. When there are more than 48 sites, seed 11 chooses the subset. Sites at or under 48 are all used.

## Precision and recall

`tests/test_check_quality.py` scores checks 1 to 11 on every directory in `sample_tasks`. A finding counts once per check per task. The label is the set of names in `expected_findings.yaml`.

- A true positive is a check that fires on a task whose label lists it.
- A false positive is a check that fires on a task whose label does not list it.
- A false negative is a label the check does not fire for.
- Precision is `tp / (tp + fp)`. Recall is `tp / (tp + fn)`.
- A denominator of 0 prints `n/a`. On `sample_tasks`, `n/a` and any value below 0.8 fail the test.

The held-out count used the same definitions on `held_out_tasks` only. The 0.8 bar was not applied there, and nothing was tuned to that table.

Read both results in [EVALUATION.md](EVALUATION.md). v1 is the `sample_tasks` table. Held-out is the later table.
