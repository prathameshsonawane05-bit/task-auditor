"""Flag tests whose asserts cannot reject a wrong solution.

A real assert anywhere in the test suppresses the finding. That includes a
real assert beside `assert True`, and a real assert beside `except: pass`.
`pytest.raises` is not treated as an assert, so a test that only uses it is
flagged as having no assert. `assert x` (truthiness) is treated as a real
assert. `!= None` is not the `is not None` pattern.

A try/except that re-raises is not a bare pass. A test with no assert is
not flagged when its handler re-raises. Only a handler whose body is just
`pass` counts as swallowing errors.
"""

import ast

from auditor.checks.model import Finding, Severity, StaticTarget
from auditor.checks.parsing import (
    iter_test_functions,
    location,
    parse_snippet,
    walk_owned,
)

CHECK = "weak_assertion"
_ASSERT_TRUE = "assert True"
_IS_NOT_NONE = "is not None"
_ISINSTANCE = "isinstance"
_ORDER = (_ASSERT_TRUE, _IS_NOT_NONE, _ISINSTANCE)


def run_weak_assertion(target: StaticTarget) -> list[Finding]:
    findings: list[Finding] = []
    for snippet in target.tests:
        module = parse_snippet(snippet)
        if module is None:
            continue
        for fn in iter_test_functions(module):
            finding = _judge(snippet.label, fn)
            if finding is not None:
                findings.append(finding)
    return findings


def _judge(
    label: str,
    fn: ast.FunctionDef | ast.AsyncFunctionDef,
) -> Finding | None:
    real = False
    kinds: set[str] = set()
    weak_node: ast.AST | None = None
    pass_handler: ast.ExceptHandler | None = None
    reraises = False
    saw_assert = False
    for node in walk_owned(fn):
        if isinstance(node, ast.Assert):
            saw_assert = True
            weak = _weak_kinds(node.test)
            if weak is None:
                real = True
            else:
                kinds.update(weak)
                if weak_node is None:
                    weak_node = node
        elif isinstance(node, (ast.Try, ast.TryStar)):
            for handler in node.handlers:
                if _handler_only_passes(handler) and pass_handler is None:
                    pass_handler = handler
                if any(isinstance(child, ast.Raise) for child in ast.walk(handler)):
                    reraises = True
    if real:
        return None
    if pass_handler is not None:
        if pass_handler.type is None:
            detail = "a bare except that only passes"
        else:
            detail = f"except {ast.unparse(pass_handler.type)} that only passes"
        return _finding(
            label, pass_handler, f"{fn.name} swallows errors with {detail}."
        )
    if not saw_assert:
        if reraises:
            return None
        return _finding(label, fn, f"{fn.name} does not contain an assert.")
    if weak_node is None:
        return None
    return _finding(label, weak_node, f"{fn.name} only uses {_join(kinds)}.")


def _weak_kinds(node: ast.AST) -> set[str] | None:
    if isinstance(node, ast.BoolOp) and isinstance(node.op, (ast.And, ast.Or)):
        kinds: set[str] = set()
        for value in node.values:
            part = _weak_kinds(value)
            if part is None:
                return None
            kinds.update(part)
        return kinds
    if isinstance(node, ast.Constant) and node.value is True:
        return {_ASSERT_TRUE}
    if _is_is_not_none(node):
        return {_IS_NOT_NONE}
    if isinstance(node, ast.Call) and _is_isinstance(node):
        return {_ISINSTANCE}
    return None


def _is_is_not_none(node: ast.AST) -> bool:
    if not isinstance(node, ast.Compare):
        return False
    if len(node.ops) != 1 or not isinstance(node.ops[0], ast.IsNot):
        return False
    if len(node.comparators) != 1:
        return False
    left_none = isinstance(node.left, ast.Constant) and node.left.value is None
    right = node.comparators[0]
    right_none = isinstance(right, ast.Constant) and right.value is None
    return left_none or right_none


def _is_isinstance(node: ast.Call) -> bool:
    return isinstance(node.func, ast.Name) and node.func.id == "isinstance"


def _handler_only_passes(handler: ast.ExceptHandler) -> bool:
    return bool(handler.body) and all(
        isinstance(stmt, ast.Pass) for stmt in handler.body
    )


def _join(kinds: set[str]) -> str:
    present = [kind for kind in _ORDER if kind in kinds]
    if not present:
        return "a weak check"
    if len(present) == 1:
        return present[0]
    return " and ".join(present)


def _finding(label: str, node: ast.AST, explanation: str) -> Finding:
    return Finding(
        check=CHECK,
        severity=Severity.MEDIUM,
        location=location(label, node),
        explanation=explanation,
    )
