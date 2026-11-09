# TaskAuditor

TaskAuditor audits invented coding tasks for weak verifiers. A task is a folder with an instruction, pytest tests, and a reference solution. An audit reports findings, a requirement-coverage fraction, and a mutation score.

The tasks in this repository are synthetic. They are not taken from a company, a client, or an evaluation platform.

## Run an audit

Python 3.11 is required.

```sh
python3.11 -m venv .venv
.venv/bin/python -m pip install -e ".[dev]"
.venv/bin/auditor audit sample_tasks/slugify --out reports
```

The command prints a warning, then writes `reports/slugify.json` and `reports/slugify.md`. Each report has the findings, the requirement coverage, and the mutation score. A finding has `check`, `severity`, `location`, and `explanation`.

The path must be a task folder directly inside `sample_tasks`. Any other path is refused before the checks run. `reports/` is gitignored.

The dashboard stores reports you choose to keep. It does not run the audit.

```sh
.venv/bin/uvicorn auditor.api:app --host 127.0.0.1 --port 8000
```

```sh
cd frontend
npm ci
npm run dev
```

Post a report JSON to `http://127.0.0.1:8000/api/tasks`. The page at `http://127.0.0.1:5173` lists what is stored. An empty database shows "No tasks stored." The database file is `auditor.sqlite` in the project directory, or the path in `AUDITOR_DB`. Do not commit it. Vite proxies `/api` to port 8000. Set `AUDITOR_API` when the API is on another origin.

## Add a check

A check returns findings. Each finding has four fields:

- `check`: the registered name.
- `severity`: `high`, `medium`, or `low`. High means the task can pass without the behavior the instruction describes. Medium means a weak assertion, an unspecified format, or a hidden requirement. Low means the result can change without a solution change.
- `location`: a path, usually with a line, that points at the evidence.
- `explanation`: one sentence. It names the evidence, does not contain a line break, ends with a period, and does not contain `". "`.

Put the check in one registry:

- Checks that read source join `CHECKS` in `auditor/checks/__init__.py`. The function takes a `StaticTarget`. `run_static_checks` runs that tuple. These are checks 1 to 5.
- Requirement-marker checks join `COVERAGE_CHECKS` in the same file. The function also takes a `StaticTarget`. `run_coverage_checks` runs that tuple. These are checks 6 and 7.
- Checks that run pytest join `DYNAMIC_CHECKS` in `auditor/checks/dynamic.py`. The function takes the task directory. `run_dynamic_checks` runs that tuple. These are checks 8 to 10.
- The mutation check joins `MUTATION_CHECKS` in `auditor/checks/mutation.py`. The function takes the task directory. `auditor/run.py` calls `measure_mutations` once and uses the survivors. It does not loop over `MUTATION_CHECKS`, so a second mutation check is not run until that call is updated. Do not add the mutation check to `DYNAMIC_CHECKS`.

A new check needs three tests, using a tiny hand-written snippet or a temp task folder:

- A positive case, where the check fires and the finding has all four fields. Use `assert_one_sentence` from `tests/check_support.py` for a static explanation.
- A negative case, where the same check stays silent.
- An edge case that is nearby but must not be mistaken for the positive case.

Also assert that the name and severity are in the registry the check joined. The check must not read `expected_findings.yaml`.

## Limitations

- Python and pytest only. The checks are heuristics.
- The child process is not a security sandbox. The network block replaces `socket.socket` so the default family, `AF_INET`, and `AF_INET6` raise `OSError`, and it does the same for `connect`, `connect_ex`, and `socket.create_connection`. That block does not stop `AF_UNIX` sockets, local files, a subprocess (the patch is not inherited), ctypes and other direct system calls, or task code that restores or reloads `socket.socket`.
- The copy rule writes `solution.py` over every environment module. Each top-level `environment/*.py` file other than `__init__.py` is replaced, in a temp directory, by `solution/solution.py` under that same file name.
- Mutation uses the fixed operator map (`==` with `!=`, `<` with `>=`, `<=` with `>`, `>` with `<=`, `>=` with `<`, `is` with `is not`, `in` with `not in`, and `and` with `or`), skips `True` and `False`, and does not treat `while` or `for` as branches. A timeout counts as killed. The cap is 48 and the seed is 11.
- v1 is 1.000 on tasks written by the same author as the checks, and two of those tasks were edited after a first run. That score is weak evidence.
- The held-out table was not tuned. `weak_assertion` precision is 0.111 because a test whose only check is `pytest.raises` counts as no assert. `hardcoded_solution` flagged `hall_postage`, a real postage table that returns literal band prices. `surviving_mutants` flagged `stall_call` because `price_pence < 0` can become `price_pence < -1` and the refusal test still passes. Rows printed `n/a` were not measured.

Both tables are in [docs/EVALUATION.md](docs/EVALUATION.md). The design of the folders, registries, runner, and scores is in [docs/DESIGN.md](docs/DESIGN.md).
