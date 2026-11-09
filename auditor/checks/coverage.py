"""Coverage checks 6 and 7, read from the AST.

A requirement is covered when at least one test function has a decorator
whose name is `covers` and whose argument is that id. Every such decorator
on the function counts. `@covers("R2")` above `@covers("R1")` covers both
ids. The sample helper stores one id on `__covers__` at runtime; this check
does not call that helper and does not import the test.

The bare name `covers` is recognized, as is an attribute named `covers`
(`conftest.covers`). An alias is not. `from conftest import covers as mark`
and then `@mark("R1")` does not cover R1.

Only a non-empty string literal counts, either as a positional argument or
as the keyword `requirement_id`. A name, `@covers` with no call, and a
decorator on the class rather than the test function do not count.

`hidden_requirement` also flags an exact error message that instruction.md
does not contain. That is a keyword `match="..."` on `pytest.raises` or
`raises`, or `==` against an exception string: `str` or `repr` of an
`except ... as name` binding, that name itself, `name.args`, or `.value`
and `.args` on a `pytest.raises(...) as` name. A positional match argument
and an f-string are not read. The `except` name is taken from anywhere in
the test, including a nested function, and it is not cleared by a later
assignment. `assert result == "hello"` is ordinary output and stays with
`brittle_format`. A message is not flagged when its exact text appears in
the instruction, including as part of a longer sentence. The match string
is not evaluated as a regex. Comparison is case sensitive.

When the requirement total is 0, the percentage is 0.0. Markers in that
case still count as hidden ids, because they are not in the requirement list.
"""

import ast
from dataclasses import dataclass

from auditor.checks.model import Finding, Severity, StaticTarget
from auditor.checks.parsing import (
    dotted_name,
    iter_test_functions,
    location,
    parse_snippet,
    walk_owned,
)

UNTESTED = "untested_requirement"
HIDDEN = "hidden_requirement"


@dataclass(frozen=True, slots=True)
class _Marker:
    node: ast.AST
    requirement_id: str


def requirement_coverage(target: StaticTarget) -> float:
    """Return covered requirements divided by the total.

    A total of 0 returns 0.0. This does not divide by zero.
    """
    total = len(target.requirements)
    if total == 0:
        return 0.0
    covered = _covered_ids(target)
    hits = sum(1 for requirement_id in target.requirements if requirement_id in covered)
    return hits / total


def run_untested_requirement(target: StaticTarget) -> list[Finding]:
    """Flag each requirement id that no test marks with @covers."""
    covered = _covered_ids(target)
    findings: list[Finding] = []
    reported: set[str] = set()
    for requirement_id in target.requirements:
        if requirement_id in covered or requirement_id in reported:
            continue
        reported.add(requirement_id)
        findings.append(
            Finding(
                check=UNTESTED,
                severity=Severity.HIGH,
                location=f"requirements:{requirement_id}",
                explanation=f"Requirement {requirement_id} has no @covers marker.",
            )
        )
    return findings


def run_hidden_requirement(target: StaticTarget) -> list[Finding]:
    """Flag tests that check an unpublished id or error message."""
    known = set(target.requirements)
    findings: list[Finding] = []
    for snippet in target.tests:
        module = parse_snippet(snippet)
        if module is None:
            continue
        for func in iter_test_functions(module):
            findings.extend(
                _hidden_for_test(snippet.label, func, known, target.instruction)
            )
    return findings


def _covered_ids(target: StaticTarget) -> set[str]:
    found: set[str] = set()
    for snippet in target.tests:
        module = parse_snippet(snippet)
        if module is None:
            continue
        for func in iter_test_functions(module):
            for marker in _markers(func):
                found.add(marker.requirement_id)
    return found


def _hidden_for_test(
    label: str,
    func: ast.FunctionDef | ast.AsyncFunctionDef,
    known: set[str],
    instruction: str,
) -> list[Finding]:
    findings: list[Finding] = []
    markers = _markers(func)
    if not markers:
        findings.append(
            _hidden(
                label,
                func,
                f"{func.name} has no @covers marker.",
            )
        )
    else:
        reported: set[str] = set()
        for marker in markers:
            requirement_id = marker.requirement_id
            if requirement_id in known or requirement_id in reported:
                continue
            reported.add(requirement_id)
            findings.append(
                _hidden(
                    label,
                    marker.node,
                    f"{func.name} uses @covers({requirement_id!r}), "
                    "which is not a requirement id.",
                )
            )
    findings.extend(_error_messages(label, func, instruction))
    return findings


def _markers(func: ast.FunctionDef | ast.AsyncFunctionDef) -> list[_Marker]:
    found: list[_Marker] = []
    for deco in func.decorator_list:
        if not isinstance(deco, ast.Call) or not _is_covers(deco.func):
            continue
        for arg in deco.args:
            text = _string_literal(arg)
            if text is not None:
                found.append(_Marker(deco, text))
        for keyword in deco.keywords:
            if keyword.arg != "requirement_id":
                continue
            text = _string_literal(keyword.value)
            if text is not None:
                found.append(_Marker(deco, text))
    return found


def _is_covers(func: ast.AST) -> bool:
    if isinstance(func, ast.Name):
        return func.id == "covers"
    return isinstance(func, ast.Attribute) and func.attr == "covers"


def _string_literal(node: ast.AST) -> str | None:
    if isinstance(node, ast.Constant) and isinstance(node.value, str) and node.value:
        return node.value
    return None


def _error_messages(
    label: str,
    func: ast.FunctionDef | ast.AsyncFunctionDef,
    instruction: str,
) -> list[Finding]:
    exceptions, raised = _exception_bindings(func)
    findings: list[Finding] = []
    for node in walk_owned(func):
        if isinstance(node, ast.Call) and _is_pytest_raises(node):
            message = _match_text(node)
            if message is not None and message not in instruction:
                findings.append(
                    _hidden(
                        label,
                        node,
                        f"{func.name} uses pytest.raises match {message!r}, "
                        "which instruction.md does not contain.",
                    )
                )
        elif isinstance(node, ast.Assert) and isinstance(node.test, ast.Compare):
            message = _exception_message(node.test, exceptions, raised)
            if message is not None and message not in instruction:
                findings.append(
                    _hidden(
                        label,
                        node,
                        f"{func.name} compares an exception string to {message!r}, "
                        "which instruction.md does not contain.",
                    )
                )
    return findings


def _exception_bindings(
    func: ast.FunctionDef | ast.AsyncFunctionDef,
) -> tuple[set[str], set[str]]:
    """Names bound by `except ... as` and by `pytest.raises(...) as`."""
    exceptions: set[str] = set()
    raised: set[str] = set()
    for node in ast.walk(func):
        if isinstance(node, ast.ExceptHandler) and isinstance(node.name, str):
            exceptions.add(node.name)
        elif isinstance(node, (ast.With, ast.AsyncWith)):
            for item in node.items:
                if (
                    isinstance(item.context_expr, ast.Call)
                    and _is_pytest_raises(item.context_expr)
                    and isinstance(item.optional_vars, ast.Name)
                ):
                    raised.add(item.optional_vars.id)
    return exceptions, raised


def _is_pytest_raises(node: ast.Call) -> bool:
    parts = dotted_name(node.func)
    if parts == ["raises"]:
        return True
    return parts is not None and parts[-1] == "raises" and "pytest" in parts


def _match_text(node: ast.Call) -> str | None:
    for keyword in node.keywords:
        if keyword.arg == "match":
            return _string_literal(keyword.value)
    return None


def _exception_message(
    compare: ast.Compare,
    exceptions: set[str],
    raised: set[str],
) -> str | None:
    sides = [compare.left, *compare.comparators]
    for index, op in enumerate(compare.ops):
        if not isinstance(op, ast.Eq):
            continue
        message = _paired_message(sides[index], sides[index + 1], exceptions, raised)
        if message is None:
            message = _paired_message(
                sides[index + 1], sides[index], exceptions, raised
            )
        if message is not None:
            return message
    return None


def _paired_message(
    literal_side: ast.AST,
    expr_side: ast.AST,
    exceptions: set[str],
    raised: set[str],
) -> str | None:
    text = _string_literal(literal_side)
    if text is None or not _is_exception_expr(expr_side, exceptions, raised):
        return None
    return text


def _is_exception_expr(node: ast.AST, exceptions: set[str], raised: set[str]) -> bool:
    if (
        isinstance(node, ast.Call)
        and _is_str_or_repr(node.func)
        and node.args
        and _is_exception_value(node.args[0], exceptions, raised)
    ):
        return True
    return _is_exception_value(node, exceptions, raised)


def _is_str_or_repr(func: ast.AST) -> bool:
    return isinstance(func, ast.Name) and func.id in {"str", "repr"}


def _is_exception_value(node: ast.AST, exceptions: set[str], raised: set[str]) -> bool:
    if isinstance(node, ast.Name):
        return node.id in exceptions
    if isinstance(node, ast.Attribute):
        if node.attr == "value" and isinstance(node.value, ast.Name):
            return node.value.id in raised
        if node.attr == "args":
            return _is_exception_value(node.value, exceptions, raised)
        return False
    if isinstance(node, ast.Subscript):
        return _is_exception_value(node.value, exceptions, raised)
    return False


def _hidden(label: str, node: ast.AST, explanation: str) -> Finding:
    return Finding(
        check=HIDDEN,
        severity=Severity.MEDIUM,
        location=location(label, node),
        explanation=explanation,
    )
