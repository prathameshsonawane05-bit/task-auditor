"""Precision and recall for checks 1 to 11 on the labeled sample tasks.

A finding counts once per check per task. The labels live in
expected_findings.yaml. This test reads those labels. The checks do not.
"""

from dataclasses import dataclass, field
from pathlib import Path

import yaml

from auditor.checks import (
    CHECKS,
    COVERAGE_CHECKS,
    DYNAMIC_CHECKS,
    MUTATION_CHECKS,
    run_coverage_checks,
    run_dynamic_checks,
    run_static_checks,
    run_surviving_mutants,
    target_from_task,
)

REPO = Path(__file__).resolve().parents[1]
SAMPLE = REPO / "sample_tasks"
BAR = 0.8

CHECK_NAMES: tuple[str, ...] = (
    *(rule.name for rule in CHECKS),
    *(rule.name for rule in COVERAGE_CHECKS),
    *(rule.name for rule in DYNAMIC_CHECKS),
    *(rule.name for rule in MUTATION_CHECKS),
)


@dataclass
class CheckScore:
    """Counts for one check across every sample task."""

    check: str
    tp: int = 0
    fp: int = 0
    fn: int = 0
    false_positives: list[str] = field(default_factory=list)
    false_negatives: list[str] = field(default_factory=list)

    def precision(self) -> float | None:
        """Return tp / (tp + fp). A zero denominator is missing."""
        return _ratio(self.tp, self.tp + self.fp)

    def recall(self) -> float | None:
        """Return tp / (tp + fn). A zero denominator is missing."""
        return _ratio(self.tp, self.tp + self.fn)


def test_zero_denominator_is_below_the_bar() -> None:
    assert _ratio(0, 0) is None
    assert _meets_bar(None) is False
    assert _meets_bar(0.8) is True
    assert _meets_bar(0.79) is False


def test_check_quality_meets_the_bar() -> None:
    scores = _score_sample_tasks()
    table = _format_table(scores)
    print(table)
    failures = [score for score in scores if not _score_meets_bar(score)]
    assert not failures, _failure_text(scores, table)


def _score_sample_tasks() -> tuple[CheckScore, ...]:
    scores = {name: CheckScore(name) for name in CHECK_NAMES}
    for root in sorted(path for path in SAMPLE.iterdir() if path.is_dir()):
        expected = _expected(root)
        fired = _fired(root)
        for name, score in scores.items():
            if name in fired and name in expected:
                score.tp += 1
            elif name in fired:
                score.fp += 1
                score.false_positives.append(root.name)
            elif name in expected:
                score.fn += 1
                score.false_negatives.append(root.name)
    return tuple(scores[name] for name in CHECK_NAMES)


def _fired(root: Path) -> set[str]:
    target = target_from_task(root)
    findings = run_static_checks(target)
    findings.extend(run_coverage_checks(target))
    findings.extend(run_dynamic_checks(root))
    findings.extend(run_surviving_mutants(root))
    return {finding.check for finding in findings}


def _expected(root: Path) -> set[str]:
    loaded: object = yaml.safe_load(
        (root / "expected_findings.yaml").read_text(encoding="utf-8")
    )
    if loaded is None:
        return set()
    if not isinstance(loaded, list):
        raise AssertionError(f"{root.name} label is not a list")
    names: set[str] = set()
    for item in loaded:
        if not isinstance(item, str):
            raise AssertionError(f"{root.name} label has a non-string")
        names.add(item)
    return names


def _ratio(numerator: int, denominator: int) -> float | None:
    if denominator == 0:
        return None
    return numerator / denominator


def _meets_bar(value: float | None) -> bool:
    return value is not None and value >= BAR


def _score_meets_bar(score: CheckScore) -> bool:
    return _meets_bar(score.precision()) and _meets_bar(score.recall())


def _failure_text(scores: tuple[CheckScore, ...], table: str) -> str:
    lines = [table]
    for score in scores:
        if score.false_positives:
            names = ", ".join(score.false_positives)
            lines.append(f"{score.check} false positives: {names}")
        if score.false_negatives:
            names = ", ".join(score.false_negatives)
            lines.append(f"{score.check} false negatives: {names}")
    return "\n".join(lines)


def _format_table(scores: tuple[CheckScore, ...]) -> str:
    header = (
        f"{'check':<24} {'tp':>4} {'fp':>4} {'fn':>4} {'precision':>10} {'recall':>8}"
    )
    lines = [header]
    for score in scores:
        lines.append(
            f"{score.check:<24} {score.tp:>4} {score.fp:>4} {score.fn:>4} "
            f"{_format_ratio(score.precision()):>10} {_format_ratio(score.recall()):>8}"
        )
    return "\n".join(lines)


def _format_ratio(value: float | None) -> str:
    if value is None:
        return "n/a"
    return f"{value:.3f}"
