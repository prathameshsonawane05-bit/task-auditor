# Working agreement

Unless you were told "you are the mentor", you are the BUILDER.

## Builder rules
1. Read docs/SPEC.md and docs/PROGRESS.md before doing anything.
2. Do ONE stage at a time, then stop and wait for the user to say "next".
3. After each stage, run the checks and show the REAL command output
   (ruff, mypy, pytest, and for frontend stages tsc and the build). Never say
   "everything passes" without the output.
4. Fix every bug and warning before committing. No skipped tests, no known
   issues left for later.
5. Commit with a clear message.
6. Append a report to docs/PROGRESS.md using exactly this template:

   ## Stage N: <title> (commit <hash>)
   What was built:
   Commands run and their real output:
   Bugs found and fixed:
   Files changed:
   Decisions and open questions:
   Next stage:

7. Before changing any rule or check, say what it got wrong and why.
8. For CLI stages, run the CLI on real sample tasks and show the output,
   including at least one error case.
9. Before committing, review your own diff for wrong imports, off-by-one
   errors, unhandled None, hardcoded paths, shared mutable state, and unused
   code. Fix what you find and re-run all checks from the top.
10. Order of work for each stage: commit the code first, then append the
    report to docs/PROGRESS.md using the real commit hash, then make a second
    small commit for the report ("docs: progress report for stage N").

## Honesty rules
- Synthetic, invented data only. Never use real company, client, or
  evaluation-platform task data, formats, or rubrics.
- Never tune labels to match the checks. Never tune against a held-out set
  that has been seen. Write a new one.
- Do not inflate results. State limitations plainly.