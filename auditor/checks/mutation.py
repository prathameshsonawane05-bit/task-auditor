"""Check 11, surviving mutants.

Mutants are built with ``ast``. The auditor process does not import or run
the solution. Each mutant is executed by ``run_suite_source``, the Stage 4
runner: temp directory, 2 second timeout, network block, and the same copy
rule. ``sample_tasks`` is not modified.

Operator map, one flip per comparison operator:

==  becomes !=
!=  becomes ==
<   becomes >=
<=  becomes >
>   becomes <=
>=  becomes <
is  becomes is not
is not becomes is
in  becomes not in
not in becomes in

``and`` swaps with ``or``. A numeric constant ``n`` becomes ``n + 1`` and
``n - 1``, as two mutants. Floats move by 1.0. True and False are not
mutated: a bool is an int in Python, and these are flags, not counts.
Complex numbers are not mutated. A minus sign in source is a unary operator
on a positive constant, so the constant that moves is that positive number.
A ``Constant`` whose value is already negative is still moved by one.

Delete a branch applies to ``if`` statements and ``if`` expressions. Deleting
the if branch keeps the else, or ``pass`` when there is no else. Deleting the
else branch drops ``elif`` and ``else``. ``while`` and ``for`` are not
branches here.

Every site is used when there are at most ``MUTATION_CAP`` (48). Above that
cap, ``random.Random(MUTATION_SEED)`` with seed 11 picks the subset, and the
chosen sites are ordered by source position. A mutant that does not parse
after unparsing is excluded and is not part of the total. A rewrite that
unparses to the original source, or to the same text as unparsing the
original tree, is dropped and is not counted as excluded.

A mutant is killed when the suite does not pass, including a timeout or an
error. A mutant survives when the suite passes. The score is killed / total.
A total of 0 scores 0.0.
"""

import ast
import random
from collections.abc import Callable, Iterator
from dataclasses import dataclass
from pathlib import Path

from auditor.checks.dynamic import DynamicRule, run_suite_source
from auditor.checks.model import Finding, Severity

SURVIVING_MUTANTS = "surviving_mutants"
MUTATION_SEED = 11
MUTATION_CAP = 48

_Apply = Callable[[ast.AST, dict[int, ast.AST]], None]

_FLIP: dict[type[ast.cmpop], type[ast.cmpop]] = {
    ast.Eq: ast.NotEq,
    ast.NotEq: ast.Eq,
    ast.Lt: ast.GtE,
    ast.LtE: ast.Gt,
    ast.Gt: ast.LtE,
    ast.GtE: ast.Lt,
    ast.Is: ast.IsNot,
    ast.IsNot: ast.Is,
    ast.In: ast.NotIn,
    ast.NotIn: ast.In,
}

_OP_LABEL: dict[type[ast.cmpop], str] = {
    ast.Eq: "==",
    ast.NotEq: "!=",
    ast.Lt: "<",
    ast.LtE: "<=",
    ast.Gt: ">",
    ast.GtE: ">=",
    ast.Is: "is",
    ast.IsNot: "is not",
    ast.In: "in",
    ast.NotIn: "not in",
}

_BODY_NODES = (
    ast.FunctionDef,
    ast.AsyncFunctionDef,
    ast.ClassDef,
    ast.If,
    ast.For,
    ast.AsyncFor,
    ast.While,
    ast.With,
    ast.AsyncWith,
    ast.Try,
    ast.ExceptHandler,
    ast.match_case,
)


@dataclass(frozen=True, slots=True)
class Mutant:
    """One parsed rewrite of the reference solution."""

    source: str
    line: int
    description: str


@dataclass(frozen=True, slots=True)
class MutationRun:
    """Score and survivors for one task."""

    score: float
    killed: int
    total: int
    excluded: int
    sampled: bool
    survivors: tuple[Finding, ...]


def mutation_score(killed: int, total: int) -> float:
    """Return killed / total. A total of 0 returns 0.0."""
    if total == 0:
        return 0.0
    return killed / total


def build_mutants(
    source: str,
    *,
    seed: int = MUTATION_SEED,
    cap: int = MUTATION_CAP,
) -> tuple[tuple[Mutant, ...], int, bool]:
    """Return mutants, how many were excluded, and whether the cap sampled."""
    try:
        tree = ast.parse(source)
        baseline = ast.unparse(tree)
    except (SyntaxError, ValueError):
        return (), 0, False
    ordinals = list(range(_site_count(tree)))
    sampled = len(ordinals) > cap
    if sampled:
        picked = random.Random(seed).sample(ordinals, cap)
        ordinals = sorted(picked)
    mutants: list[Mutant] = []
    excluded = 0
    for ordinal in ordinals:
        built = _build_one(source, ordinal)
        if built is None:
            excluded += 1
            continue
        text, line, description = built
        if text in (source, baseline):
            continue
        try:
            ast.parse(text)
        except SyntaxError:
            excluded += 1
            continue
        mutants.append(Mutant(text, line, description))
    return tuple(mutants), excluded, sampled


def measure_mutations(root: Path) -> MutationRun:
    """Run every selected mutant through the Stage 4 suite runner."""
    solution = _read_solution(root)
    if solution is None:
        return MutationRun(0.0, 0, 0, 0, False, ())
    mutants, excluded, sampled = build_mutants(solution)
    survivors: list[Finding] = []
    killed = 0
    for mutant in mutants:
        result = run_suite_source(root, mutant.source)
        if result.passed:
            survivors.append(_survivor(mutant))
        else:
            killed += 1
    total = len(mutants)
    return MutationRun(
        mutation_score(killed, total),
        killed,
        total,
        excluded,
        sampled,
        tuple(survivors),
    )


def run_surviving_mutants(root: Path) -> list[Finding]:
    """Flag each mutant that still passes the tests."""
    return list(measure_mutations(root).survivors)


MUTATION_CHECKS: tuple[DynamicRule, ...] = (
    DynamicRule(SURVIVING_MUTANTS, Severity.HIGH, run_surviving_mutants),
)


def _survivor(mutant: Mutant) -> Finding:
    location = f"solution/solution.py:{mutant.line}"
    return Finding(
        check=SURVIVING_MUTANTS,
        severity=Severity.HIGH,
        location=location,
        explanation=f"Mutant survived at {location} by {mutant.description}.",
    )


def _read_solution(root: Path) -> str | None:
    path = root / "solution" / "solution.py"
    if not path.is_file():
        return None
    try:
        return path.read_text(encoding="utf-8")
    except (OSError, UnicodeError):
        return None


def _build_one(source: str, ordinal: int) -> tuple[str, int, str] | None:
    tree = ast.parse(source)
    parents = _parent_map(tree)
    seen = 0
    for node in _preorder(tree):
        for description, apply in _sites(node):
            if seen == ordinal:
                line = _line(node)
                apply(node, parents)
                text = _render(tree)
                if text is None:
                    return None
                return text, line, description
            seen += 1
    return None


def _site_count(tree: ast.AST) -> int:
    return sum(1 for node in _preorder(tree) for _site in _sites(node))


def _sites(node: ast.AST) -> Iterator[tuple[str, _Apply]]:
    if isinstance(node, ast.Compare):
        yield from _compare_sites(node)
    elif isinstance(node, ast.Constant):
        yield from _constant_sites(node)
    elif isinstance(node, ast.If):
        yield from _if_sites(node)
    elif isinstance(node, ast.IfExp):
        yield from _ifexp_sites(node)
    elif isinstance(node, ast.BoolOp):
        yield from _bool_sites(node)


def _compare_sites(node: ast.Compare) -> Iterator[tuple[str, _Apply]]:
    for index, op in enumerate(node.ops):
        flipped = _FLIP.get(type(op))
        if flipped is None:
            continue
        old = _OP_LABEL.get(type(op), "comparison")
        new = _OP_LABEL.get(flipped, "comparison")
        yield f"flipping {old} to {new}", _bind_flip(index, flipped)


def _constant_sites(node: ast.Constant) -> Iterator[tuple[str, _Apply]]:
    value = node.value
    if isinstance(value, bool):
        return
    if isinstance(value, float):
        yield from _number_pair(value, 1.0)
        return
    if isinstance(value, int):
        yield from _number_pair(value, 1)


def _number_pair(value: int | float, step: int | float) -> Iterator[tuple[str, _Apply]]:
    raised = value + step
    lowered = value - step
    yield f"changing constant {value} to {raised}", _bind_number(raised)
    yield f"changing constant {value} to {lowered}", _bind_number(lowered)


def _line(node: ast.AST) -> int:
    line = getattr(node, "lineno", None)
    if isinstance(line, int):
        return line
    return 1


def _if_sites(node: ast.If) -> Iterator[tuple[str, _Apply]]:
    yield "deleting the if branch", _delete_if_branch
    if node.orelse:
        yield "deleting the else branch", _delete_else_branch


def _ifexp_sites(_node: ast.IfExp) -> Iterator[tuple[str, _Apply]]:
    yield "deleting the if-expression body", _delete_ifexp_body
    yield "deleting the if-expression else", _delete_ifexp_else


def _bool_sites(node: ast.BoolOp) -> Iterator[tuple[str, _Apply]]:
    if isinstance(node.op, ast.And):
        yield "swapping and for or", _swap_and
    elif isinstance(node.op, ast.Or):
        yield "swapping or for and", _swap_or


def _bind_flip(index: int, op_type: type[ast.cmpop]) -> _Apply:
    def apply(node: ast.AST, _parents: dict[int, ast.AST]) -> None:
        if isinstance(node, ast.Compare):
            node.ops[index] = op_type()

    return apply


def _bind_number(new: int | float) -> _Apply:
    def apply(node: ast.AST, _parents: dict[int, ast.AST]) -> None:
        if isinstance(node, ast.Constant):
            node.value = new

    return apply


def _delete_if_branch(node: ast.AST, parents: dict[int, ast.AST]) -> None:
    if not isinstance(node, ast.If):
        return
    parent = parents.get(id(node))
    if parent is None:
        return
    if node.orelse:
        _replace(parent, node, list(node.orelse))
    else:
        _replace(parent, node, [ast.Pass()])


def _delete_else_branch(node: ast.AST, _parents: dict[int, ast.AST]) -> None:
    if isinstance(node, ast.If):
        node.orelse = []


def _delete_ifexp_body(node: ast.AST, parents: dict[int, ast.AST]) -> None:
    if not isinstance(node, ast.IfExp):
        return
    parent = parents.get(id(node))
    if parent is not None:
        _replace(parent, node, node.orelse)


def _delete_ifexp_else(node: ast.AST, parents: dict[int, ast.AST]) -> None:
    if not isinstance(node, ast.IfExp):
        return
    parent = parents.get(id(node))
    if parent is not None:
        _replace(parent, node, node.body)


def _swap_and(node: ast.AST, _parents: dict[int, ast.AST]) -> None:
    if isinstance(node, ast.BoolOp):
        node.op = ast.Or()


def _swap_or(node: ast.AST, _parents: dict[int, ast.AST]) -> None:
    if isinstance(node, ast.BoolOp):
        node.op = ast.And()


def _replace(parent: ast.AST, old: ast.AST, new: ast.AST | list[ast.stmt]) -> None:
    for field, value in ast.iter_fields(parent):
        if value is old:
            if not isinstance(new, list):
                setattr(parent, field, new)
            return
        if isinstance(value, list):
            for index, item in enumerate(value):
                if item is old:
                    if isinstance(new, list):
                        value[index : index + 1] = new
                    else:
                        value[index] = new
                    return


def _render(tree: ast.AST) -> str | None:
    _fill_empty_bodies(tree)
    try:
        text = ast.unparse(tree)
        ast.parse(text)
    except (SyntaxError, ValueError, TypeError):
        return None
    return text


def _fill_empty_bodies(tree: ast.AST) -> None:
    for node in ast.walk(tree):
        body = getattr(node, "body", None)
        if isinstance(body, list) and not body and isinstance(node, _BODY_NODES):
            body.append(ast.Pass())


def _parent_map(tree: ast.AST) -> dict[int, ast.AST]:
    parents: dict[int, ast.AST] = {}
    for node in _preorder(tree):
        for child in ast.iter_child_nodes(node):
            parents[id(child)] = node
    return parents


def _preorder(node: ast.AST) -> Iterator[ast.AST]:
    yield node
    for child in ast.iter_child_nodes(node):
        yield from _preorder(child)
