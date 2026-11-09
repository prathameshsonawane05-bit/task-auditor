"""AST helpers shared by the static checks."""

import ast
from collections.abc import Iterator

from auditor.checks.model import Snippet


def parse_snippet(snippet: Snippet) -> ast.Module | None:
    """Parse a snippet. A syntax error produces no findings."""
    try:
        return ast.parse(snippet.source, filename=snippet.label)
    except SyntaxError:
        return None


def location(label: str, node: ast.AST) -> str:
    line = getattr(node, "lineno", None)
    if not isinstance(line, int):
        line = 1
    return f"{label}:{line}"


def iter_test_functions(
    module: ast.Module,
) -> Iterator[ast.FunctionDef | ast.AsyncFunctionDef]:
    """Yield module-level tests and test methods on module-level classes."""
    for node in module.body:
        if isinstance(node, ast.ClassDef):
            members: list[ast.stmt] = list(node.body)
        elif isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            members = [node]
        else:
            continue
        for member in members:
            if isinstance(
                member, (ast.FunctionDef, ast.AsyncFunctionDef)
            ) and member.name.startswith("test_"):
                yield member


def walk_owned(node: ast.AST) -> Iterator[ast.AST]:
    """Walk a function body without entering nested functions or classes."""
    yield node
    for child in ast.iter_child_nodes(node):
        if isinstance(child, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
            continue
        if isinstance(child, ast.Lambda):
            continue
        yield from walk_owned(child)


def dotted_name(node: ast.AST) -> list[str] | None:
    parts: list[str] = []
    current = node
    while isinstance(current, ast.Attribute):
        parts.append(current.attr)
        current = current.value
    if not isinstance(current, ast.Name):
        return None
    parts.append(current.id)
    parts.reverse()
    return parts


class ImportMap:
    """Local names introduced by import statements in one module."""

    def __init__(self) -> None:
        self.modules: dict[str, str] = {}
        self.imported: dict[str, tuple[str, str]] = {}

    def resolve(self, func: ast.AST) -> tuple[str, str] | None:
        if isinstance(func, ast.Name):
            imported = self.imported.get(func.id)
            if imported is not None:
                return imported
            if func.id in {"open", "isinstance"}:
                return ("builtins", func.id)
            return None
        parts = dotted_name(func)
        if parts is None or len(parts) < 2:
            return None
        head = parts[0]
        qual = ".".join(parts[1:])
        module = self.modules.get(head)
        if module is not None:
            return module, qual
        imported = self.imported.get(head)
        if imported is None:
            return None
        base_module, base_qual = imported
        full = f"{base_qual}.{qual}" if qual else base_qual
        return base_module, full


def import_map(module: ast.Module) -> ImportMap:
    mapping = ImportMap()
    for node in module.body:
        if isinstance(node, ast.Import):
            for alias in node.names:
                if alias.asname:
                    mapping.modules[alias.asname] = alias.name
                else:
                    root = alias.name.split(".", maxsplit=1)[0]
                    mapping.modules[root] = root
        elif isinstance(node, ast.ImportFrom) and node.module:
            for alias in node.names:
                if alias.name == "*":
                    continue
                local = alias.asname or alias.name
                mapping.imported[local] = (node.module, alias.name)
    return mapping
