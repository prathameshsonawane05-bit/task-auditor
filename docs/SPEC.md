You are building TaskAuditor, a tool that audits coding tasks for weak
verifiers. Input is a task folder (instruction, hidden tests, reference
solution). Output is a report of findings plus a requirement coverage
percentage and a mutation score. Work like a careful senior engineer: small
steps, verify everything, never assume code works because it looks right.

TECH STACK
- Python 3.11, Typer (CLI), FastAPI + SQLite later for the dashboard, Pydantic
  v2, PyYAML, pytest, ruff, mypy (strict)
- Frontend (late stage only): React + Vite + TypeScript, plain CSS
- Layout: /auditor (package), /tests, /sample_tasks, /scripts, /docs, /frontend

TASK FORMAT (our own invented format)
sample_tasks/<task_id>/
  task.yaml  (id, title, language: python, requirements: [{id, text}])
  instruction.md
  environment/  (starter code)
  solution/solution.py  (reference solution)
  tests/test_*.py  (pytest; each test marked @covers("R1"), with a small
                    helper "covers" decorator provided in tests/conftest.py)
Validate with clear errors that name the bad field. Python and pytest only.

CHECKS (each a registered rule returning findings: check, severity,
location, one-sentence explanation naming the evidence)
Static (AST):
1. source_inspection_test: a test uses open(), inspect.getsource, ast.parse,
   or `in <source text>` on the solution file.
2. weak_assertion: test with no assert, `assert True`, only `is not None` or
   isinstance checks, or a bare try/except pass.
3. hardcoded_solution: reference solution returns literals or if-chains on
   literals that match test expectations. Back this up by running the
   solution on perturbed inputs.
4. brittle_format: exact == against long string literals where the
   instruction gives no output format.
5. nondeterministic_test: imports or calls of random, time, datetime.now,
   network, sleep without a seed or fixture.
Coverage:
6. untested_requirement: a requirement id with no @covers marker.
7. hidden_requirement: a test with no matching requirement, or asserting an
   exact error message not present in instruction.md.
Dynamic (run in a subprocess with timeout, temp directory, no network):
8. solution_fails_tests: reference solution does not pass its own tests.
9. cheat_solution_passes: run a battery of cheats (return None, return a
   constant, empty function body, return the first argument). Flag any that
   pass.
10. flaky_tests: run the suite 3 times, flag differing results.
11. surviving_mutants: mutate the solution (flip comparison operators,
    off-by-one on constants, delete a branch, swap and/or), run the tests,
    and report mutants that survive. Compute mutation score = killed / total.
Also compute requirement coverage = covered requirements / total.
Safety: only run tasks under sample_tasks. Print a warning in the CLI that
this runs code and is not a security sandbox.

STAGES
1. Setup, task loader and validation, CLI skeleton (`auditor audit <path>`),
   tests for valid and invalid task folders.
2. Static AST checks 1 to 5, each with positive, negative, and edge-case
   tests using tiny hand-written snippets.
3. Coverage checks 6 and 7 plus the requirement coverage percentage.
4. Dynamic checks 8 to 10 (subprocess runner with timeout, temp dir, no
   network).
5. Mutation testing (check 11) with a fixed seed so results are reproducible.
6. Labeled synthetic tasks: hand-write 8 good tasks (small Python functions
   like slugify, merge_intervals, parse_duration, rate limiter). Generate
   about 30 labeled tasks by planting flaws via scripts/make_flawed.py. Each
   carries an expected_findings label (good tasks have none). Cover every
   check at least 3 times. Use only invented tasks.
7. Evaluation: test_check_quality.py prints precision and recall per check.
   Fail below 0.8. If a check misses the bar, tune the CHECK, never the
   labels, and tell me what it got wrong before changing it. Save results to
   docs/EVALUATION.md as "v1".
8. HELD-OUT: write 12 new tasks by hand in a different style, WITHOUT running
   the auditor and without reading the check code. Label them as a human
   reviewer would. Run the auditor, print the table, do not tune against
   it. Record before and after in docs/EVALUATION.md.
9. Report output: JSON and Markdown reports from the CLI, then a small
   FastAPI plus React dashboard listing tasks and findings.
10. Docs and CI: README (what it is, how to add a check, limitations),
    docs/DESIGN.md, GitHub Actions workflow.
11. Fresh-clone audit: clone into a new folder, follow only the README, fix
    anything missing, confirm git tracks no secrets or databases.

HONESTY RULES
- Synthetic, invented tasks only. Never use real company, client, or
  evaluation-platform task data, formats, or rubrics.
- Never tune labels to match checks. Never tune against a held-out set that
  has been seen. Write a new one.
- Do not inflate results. Perfect scores on data written by the same author
  as the checks are weak evidence. Say so in the docs.
- Document the limitations: heuristics, Python only, mutation testing is a
  sample, runs code and is not a sandbox.
