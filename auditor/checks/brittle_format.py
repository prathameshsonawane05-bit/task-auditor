"""Flag exact == against a long string the instruction never gives.

A string is long at 40 characters. Shorter string literals are ignored.
The instruction specifies that format when it contains the exact string.
Words such as "json" or "format" do not count. If the instruction mentions
the string only as sample input, this check still treats the format as
specified and does not flag. An f-string is not a single literal, so it
is not flagged.
"""

import ast

from auditor.checks.model import Finding, Severity, StaticTarget
from auditor.checks.parsing import location, parse_snippet

CHECK = "brittle_format"
LONG_STRING_MIN_LENGTH = 40


def run_brittle_format(target: StaticTarget) -> list[Finding]:
    findings: list[Finding] = []
    for snippet in target.tests:
        module = parse_snippet(snippet)
        if module is None:
            continue
        for node in ast.walk(module):
            if not isinstance(node, ast.Compare):
                continue
            text = _long_unspecified_string(node, target.instruction)
            if text is None:
                continue
            findings.append(
                Finding(
                    check=CHECK,
                    severity=Severity.MEDIUM,
                    location=location(snippet.label, node),
                    explanation=(
                        f"{location(snippet.label, node)} uses == on a "
                        f"{len(text)}-character string that the instruction "
                        "does not specify."
                    ),
                )
            )
    return findings


def _long_unspecified_string(node: ast.Compare, instruction: str) -> str | None:
    sides = [node.left, *node.comparators]
    for index, op in enumerate(node.ops):
        if not isinstance(op, ast.Eq):
            continue
        for side in (sides[index], sides[index + 1]):
            if not isinstance(side, ast.Constant) or not isinstance(side.value, str):
                continue
            if len(side.value) < LONG_STRING_MIN_LENGTH:
                continue
            if side.value in instruction:
                continue
            return side.value
    return None
