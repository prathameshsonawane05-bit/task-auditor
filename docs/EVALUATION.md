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
