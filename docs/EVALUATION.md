# Evaluation

## v1

This set was written by the same author as the checks. Two tasks were edited after a first run so an extra cheat finding would disappear (`plant_hardcoded_solution_3` and `plant_solution_fails_3`). A perfect score here is weak evidence.

```
check                      tp   fp   fn  precision   recall
source_inspection_test      3    0    0      1.000    1.000
weak_assertion              3    0    0      1.000    1.000
hardcoded_solution          3    0    0      1.000    1.000
brittle_format              3    0    0      1.000    1.000
nondeterministic_test       3    0    0      1.000    1.000
untested_requirement        3    0    0      1.000    1.000
hidden_requirement          3    0    0      1.000    1.000
solution_fails_tests        3    0    0      1.000    1.000
cheat_solution_passes       3    0    0      1.000    1.000
flaky_tests                 3    0    0      1.000    1.000
surviving_mutants           3    0    0      1.000    1.000
```

No denominator was zero, so no row is `n/a`. No check was changed.

## Held-out

Twelve tasks were written by hand, in `held_out_tasks/`, and labeled before the auditor ran. v1 was not tuned against this set. No check, label, or task was changed after the table was printed. `tests/test_check_quality.py` still scores `sample_tasks` only. A finding still counts once per check per task.

```
check                      tp   fp   fn  precision   recall
source_inspection_test      1    0    0      1.000    1.000
weak_assertion              1    8    0      0.111    1.000
hardcoded_solution          1    1    0      0.500    1.000
brittle_format              1    0    0      1.000    1.000
nondeterministic_test       1    0    0      1.000    1.000
untested_requirement        1    0    0      1.000    1.000
hidden_requirement          0    0    0        n/a      n/a
solution_fails_tests        0    0    0        n/a      n/a
cheat_solution_passes       0    0    0        n/a      n/a
flaky_tests                 0    0    0        n/a      n/a
surviving_mutants           0    1    0      0.000      n/a
```

`hidden_requirement`, `solution_fails_tests`, `cheat_solution_passes`, and `flaky_tests` were neither labeled nor reported, so those rows are `n/a`. `surviving_mutants` was not labeled; the run reported it once, so precision is 0.000 and recall is `n/a`.

Extra findings:

```
weak_assertion false positives: flour_note, hall_postage, kettle_note, label_rows, late_slip, raffle_slip, stall_call, tea_tray
hardcoded_solution false positives: hall_postage
surviving_mutants false positives: stall_call
```
