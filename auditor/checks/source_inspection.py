"""Flag tests that read the reference solution instead of running it.

open() is flagged only when its path names the solution file: the file name
is solution.py, or the path has a solution directory component and a .py
suffix. open() of any other path, including a path this checker cannot
resolve to a string, is ignored.

inspect.getsource and ast.parse are flagged on every call, including
aliases such as `import inspect as ins`. A string literal on the right of
`in` is not solution source. Membership counts only when that side was read
from the solution file or from getsource. `not in` is not flagged.
pathlib.Path.read_text and os.path.join are not resolved.
"""

from __future__ import annotations

import ast
from collections.abc import Callable
from dataclasses import dataclass
from pathlib import PurePosixPath

from auditor.checks.model import Finding, Severity, StaticTarget
from auditor.checks.parsing import (
    ImportMap,
    dotted_name,
    import_map,
    location,
    parse_snippet,
)

CHECK = "source_inspection_test"
_FlagFn = Callable[[ast.AST, str], None]


@dataclass
class _Scope:
    sources: set[str]
    handles: set[str]
    constants: dict[str, str]

    def child(self) -> _Scope:
        return _Scope(set(self.sources), set(self.handles), dict(self.constants))


def run_source_inspection(target: StaticTarget) -> list[Finding]:
    findings: list[Finding] = []
    for snippet in target.tests:
        module = parse_snippet(snippet)
        if module is None:
            continue
        _scan(snippet.label, module, findings)
    return findings


def _scan(label: str, module: ast.Module, findings: list[Finding]) -> None:
    imports = import_map(module)
    seen: set[int] = set()

    def flag(node: ast.AST, explanation: str) -> None:
        marker = id(node)
        if marker in seen:
            return
        seen.add(marker)
        findings.append(
            Finding(
                check=CHECK,
                severity=Severity.HIGH,
                location=location(label, node),
                explanation=explanation,
            )
        )

    def visit(node: ast.AST, scope: _Scope) -> None:
        if isinstance(node, ast.Module):
            for stmt in node.body:
                visit(stmt, scope)
            return
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
            for deco in node.decorator_list:
                visit(deco, scope)
            local = scope.child()
            for stmt in node.body:
                visit(stmt, local)
            return
        if isinstance(node, ast.Assign):
            visit(node.value, scope)
            _bind_targets(node.targets, node.value, scope, imports)
            return
        if isinstance(node, ast.AnnAssign):
            if node.value is not None:
                visit(node.value, scope)
                _bind_targets([node.target], node.value, scope, imports)
            return
        if isinstance(node, (ast.With, ast.AsyncWith)):
            for item in node.items:
                visit(item.context_expr, scope)
                path = _open_path(item.context_expr, scope, imports)
                if (
                    path is not None
                    and _is_solution_path(path)
                    and isinstance(item.optional_vars, ast.Name)
                ):
                    scope.handles.add(item.optional_vars.id)
            for stmt in node.body:
                visit(stmt, scope)
            return
        if isinstance(node, ast.Call):
            _note_call(label, node, scope, imports, flag)
        elif isinstance(node, ast.Compare):
            _note_membership(label, node, scope, imports, flag)
        for child in ast.iter_child_nodes(node):
            visit(child, scope)

    visit(module, _Scope(set(), set(), {}))


def _bind_targets(
    targets: list[ast.expr],
    value: ast.AST,
    scope: _Scope,
    imports: ImportMap,
) -> None:
    constant = _constant_str(value, scope)
    reads = _reads_solution(value, scope, imports)
    opened = _assigned_solution_handle(value, scope, imports)
    for target in targets:
        if not isinstance(target, ast.Name):
            continue
        if constant is not None:
            scope.constants[target.id] = constant
        else:
            scope.constants.pop(target.id, None)
        if reads:
            scope.sources.add(target.id)
        else:
            scope.sources.discard(target.id)
        if opened:
            scope.handles.add(target.id)
        else:
            scope.handles.discard(target.id)


def _note_call(
    label: str,
    node: ast.Call,
    scope: _Scope,
    imports: ImportMap,
    flag: _FlagFn,
) -> None:
    path = _open_path(node, scope, imports)
    if path is not None and _is_solution_path(path):
        flag(node, f"{location(label, node)} calls open on {path!r}.")
        return
    resolved = imports.resolve(node.func)
    if resolved is None:
        return
    module, qual = resolved
    display = _call_display(node.func)
    place = location(label, node)
    if module == "inspect" and qual == "getsource":
        flag(
            node,
            f"{place} calls {display}, which reads source through inspect.getsource.",
        )
    elif module == "ast" and qual == "parse":
        flag(
            node,
            f"{place} calls {display}, which parses source text with ast.parse.",
        )


def _note_membership(
    label: str,
    node: ast.Compare,
    scope: _Scope,
    imports: ImportMap,
    flag: _FlagFn,
) -> None:
    for op, comparator in zip(node.ops, node.comparators, strict=True):
        if isinstance(op, ast.In) and _reads_solution(comparator, scope, imports):
            flag(
                node,
                f"{location(label, node)} uses membership on source text read "
                "from the solution file.",
            )
            return


def _assigned_solution_handle(
    value: ast.AST,
    scope: _Scope,
    imports: ImportMap,
) -> bool:
    path = _open_path(value, scope, imports)
    return path is not None and _is_solution_path(path)


def _open_path(node: ast.AST, scope: _Scope, imports: ImportMap) -> str | None:
    if not isinstance(node, ast.Call):
        return None
    if imports.resolve(node.func) != ("builtins", "open"):
        return None
    if node.args:
        return _constant_str(node.args[0], scope)
    for keyword in node.keywords:
        if keyword.arg == "file":
            return _constant_str(keyword.value, scope)
    return None


def _reads_solution(node: ast.AST, scope: _Scope, imports: ImportMap) -> bool:
    if isinstance(node, ast.Name) and node.id in scope.sources:
        return True
    if isinstance(node, ast.Call):
        resolved = imports.resolve(node.func)
        if resolved == ("inspect", "getsource"):
            return True
        if isinstance(node.func, ast.Attribute) and node.func.attr in {
            "read",
            "read_text",
            "read_bytes",
        }:
            receiver = node.func.value
            if isinstance(receiver, ast.Name) and receiver.id in scope.handles:
                return True
            path = _open_path(receiver, scope, imports)
            if path is not None and _is_solution_path(path):
                return True
    return False


def _constant_str(node: ast.AST, scope: _Scope) -> str | None:
    if isinstance(node, ast.Constant) and isinstance(node.value, str):
        return node.value
    if isinstance(node, ast.Name):
        return scope.constants.get(node.id)
    return None


def _call_display(func: ast.AST) -> str:
    parts = dotted_name(func)
    if parts is None:
        return "call"
    return ".".join(parts)


def _is_solution_path(value: str) -> bool:
    normalized = value.replace("\\", "/")
    if normalized.startswith("./"):
        normalized = normalized[2:]
    path = PurePosixPath(normalized)
    if path.name == "solution.py":
        return True
    return path.suffix == ".py" and "solution" in path.parts
