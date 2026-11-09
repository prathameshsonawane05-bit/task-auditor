"""Flag a reference solution that returns literals matching the tests.

A function qualifies when every return it owns is a literal (including a
bare return) and it does not yield. An if-chain qualifies when each branch
returns a literal. The match is confirmed by calling the function in a
subprocess. The original call must return the test's literal. A perturbed
call is reported in the same sentence whether or not its result changes.

False positives that this still flags:
- a correct solution whose specified result is a constant
- a correct literal table, such as an if-chain that maps a few codes

False negatives:
- the expected value is a variable, not a literal
- the test passes arguments by keyword
- a return of a conditional expression, such as `return "a" if x else "b"`
- a function with no return statement
- the child times out, crashes, or returns a value that is not JSON
- the solution prints in a way that does not matter, because results are
  written to a file, but a hang or an import error hides the finding

Perturbation changes the first argument: strings gain a trailing "q",
numbers increase by 1, and booleans flip. There is no perturbation when
the call has no arguments or the argument is not one of those types.
"""

import ast
from collections.abc import Sequence
from dataclasses import dataclass

from auditor.checks.model import Finding, Severity, Snippet, StaticTarget
from auditor.checks.parsing import (
    iter_test_functions,
    location,
    parse_snippet,
    walk_owned,
)
from auditor.checks.sandbox import CallResult, run_calls

CHECK = "hardcoded_solution"
_MISSING = object()


@dataclass(frozen=True, slots=True)
class _Expectation:
    func_name: str
    args: tuple[object, ...]
    expected: object
    line: int


def run_hardcoded_solution(target: StaticTarget) -> list[Finding]:
    solution = target.solution
    if solution is None:
        return []
    solution_module = parse_snippet(solution)
    if solution_module is None:
        return []
    literal_funcs = {
        node.name: node
        for node in solution_module.body
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef))
        and _returns_only_literals(node)
    }
    if not literal_funcs:
        return []
    findings: list[Finding] = []
    for snippet in target.tests:
        module = parse_snippet(snippet)
        if module is None:
            continue
        for expectation in _expectations(module):
            func = literal_funcs.get(expectation.func_name)
            if func is None:
                continue
            finding = _confirm(solution, snippet.label, func, expectation)
            if finding is not None:
                findings.append(finding)
    return findings


def _returns_only_literals(fn: ast.FunctionDef | ast.AsyncFunctionDef) -> bool:
    owned = list(walk_owned(fn))
    if any(isinstance(node, (ast.Yield, ast.YieldFrom)) for node in owned):
        return False
    returns = [node for node in owned if isinstance(node, ast.Return)]
    if not returns:
        return False
    return all(
        node.value is None or isinstance(node.value, ast.Constant) for node in returns
    )


def _expectations(module: ast.Module) -> list[_Expectation]:
    found: list[_Expectation] = []
    for fn in iter_test_functions(module):
        for node in walk_owned(fn):
            if not isinstance(node, ast.Assert) or not isinstance(
                node.test, ast.Compare
            ):
                continue
            compare = node.test
            if len(compare.ops) != 1 or not isinstance(compare.ops[0], ast.Eq):
                continue
            if len(compare.comparators) != 1:
                continue
            pair = _call_and_literal(compare.left, compare.comparators[0])
            if pair is None:
                continue
            call, expected = pair
            name = _func_name(call.func)
            args = _call_args(call)
            if name is None or args is None:
                continue
            found.append(_Expectation(name, args, expected, node.lineno))
    return found


def _call_and_literal(
    left: ast.AST,
    right: ast.AST,
) -> tuple[ast.Call, object] | None:
    if isinstance(left, ast.Call):
        expected = _literal(right)
        if expected is not _MISSING:
            return left, expected
    if isinstance(right, ast.Call):
        expected = _literal(left)
        if expected is not _MISSING:
            return right, expected
    return None


def _func_name(func: ast.AST) -> str | None:
    if isinstance(func, ast.Name):
        return func.id
    if isinstance(func, ast.Attribute) and isinstance(func.value, ast.Name):
        return func.attr
    return None


def _call_args(call: ast.Call) -> tuple[object, ...] | None:
    if call.keywords or any(isinstance(arg, ast.Starred) for arg in call.args):
        return None
    values: list[object] = []
    for arg in call.args:
        value = _literal(arg)
        if value is _MISSING:
            return None
        values.append(value)
    return tuple(values)


def _literal(node: ast.AST) -> object:
    if isinstance(node, ast.Constant) and isinstance(
        node.value, (str, int, float, bool)
    ):
        return node.value
    if isinstance(node, ast.Constant) and node.value is None:
        return None
    return _MISSING


def _confirm(
    solution: Snippet,
    test_label: str,
    func: ast.FunctionDef | ast.AsyncFunctionDef,
    expectation: _Expectation,
) -> Finding | None:
    calls: list[list[object]] = [list(expectation.args)]
    perturbed = _perturb_args(expectation.args)
    if perturbed is not None:
        calls.append(perturbed)
    results = run_calls(solution.source, expectation.func_name, calls)
    if results is None or len(results) != len(calls) or not results[0].ok:
        return None
    if results[0].value != expectation.expected:
        return None
    return Finding(
        check=CHECK,
        severity=Severity.HIGH,
        location=location(solution.label, func),
        explanation=_sentence(
            solution.label,
            test_label,
            func.lineno,
            expectation,
            results[0].value,
            perturbed,
            None if perturbed is None else results[1],
        ),
    )


def _sentence(
    solution_label: str,
    test_label: str,
    func_line: int,
    expectation: _Expectation,
    original: object,
    perturbed: list[object] | None,
    perturbed_result: CallResult | None,
) -> str:
    original_call = _render_call(expectation.func_name, expectation.args)
    base = (
        f"{solution_label}:{func_line} returns {original!r} for {original_call}, "
        f"matching {test_label}:{expectation.line}"
    )
    if perturbed is None or perturbed_result is None:
        return f"{base}, and there was no input to perturb."
    perturbed_call = _render_call(expectation.func_name, perturbed)
    if perturbed_result.ok:
        return f"{base}, and {perturbed_call} returned {perturbed_result.value!r}."
    return f"{base}, and {perturbed_call} raised {perturbed_result.error}."


def _render_call(func_name: str, args: Sequence[object]) -> str:
    rendered = ", ".join(repr(arg) for arg in args)
    return f"{func_name}({rendered})"


def _perturb_args(args: tuple[object, ...]) -> list[object] | None:
    if not args:
        return None
    new_value, ok = _perturb_value(args[0])
    if not ok:
        return None
    return [new_value, *args[1:]]


def _perturb_value(value: object) -> tuple[object, bool]:
    if isinstance(value, bool):
        return (not value, True)
    if isinstance(value, str):
        return (f"{value}q", True)
    if isinstance(value, int):
        return (value + 1, True)
    if isinstance(value, float):
        return (value + 1.0, True)
    return (None, False)
