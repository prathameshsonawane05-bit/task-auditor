"""Flag tests that can change result without a solution change.

A seed is `random.seed(...)` anywhere in the file, or `random.Random(...)`
with at least one argument. `random.Random()` with no argument is not a
seed. A seeded instance covers method calls on that name only. A global
`random.seed` covers calls on the random module. One seed anywhere in the
file counts for the whole file.

A time fixture is a `@pytest.fixture` (or a bare `@fixture`) whose body
mentions `freeze_time`, the attribute `now`, or the strings "now",
"time.time", or "sleep". It covers `time.time`, `time.time_ns`,
`time.sleep`, `asyncio.sleep`, and `datetime.now` only in tests that take
the fixture as a parameter. `@pytest.mark.usefixtures` and a `@freeze_time`
decorator on the test are not recognized.

`import time` by itself is not flagged, so `time.strftime` stays quiet.
Network imports and calls are always flagged. This stage does not treat a
monkeypatch of requests or socket as a fixture. Network modules are
socket, requests, httpx, aiohttp, urllib.request, and http.client.
"""

import ast

from auditor.checks.model import Finding, Severity, StaticTarget
from auditor.checks.parsing import (
    ImportMap,
    dotted_name,
    import_map,
    iter_test_functions,
    location,
    parse_snippet,
    walk_owned,
)

CHECK = "nondeterministic_test"
_NETWORK_PREFIXES = (
    "socket",
    "requests",
    "httpx",
    "aiohttp",
    "urllib.request",
    "http.client",
)
_TIME_CALLS = frozenset({"time", "time_ns", "sleep"})


def run_nondeterministic_test(target: StaticTarget) -> list[Finding]:
    findings: list[Finding] = []
    for snippet in target.tests:
        module = parse_snippet(snippet)
        if module is None:
            continue
        findings.extend(_scan(snippet.label, module))
    return findings


def _scan(label: str, module: ast.Module) -> list[Finding]:
    imports = import_map(module)
    seeded, unseeded = _random_instances(module, imports)
    global_seed = _has_random_seed(module, imports)
    freezing = {name for name, func in _fixtures(module).items() if _freezes_time(func)}
    findings: list[Finding] = []
    random_call = False
    for func in iter_test_functions(module):
        suppress_time = bool(_param_names(func) & freezing)
        for node in walk_owned(func):
            if not isinstance(node, ast.Call):
                continue
            if _note_call(
                label,
                node,
                imports,
                seeded,
                unseeded,
                global_seed,
                suppress_time,
                findings,
            ):
                random_call = True
    if not global_seed and not seeded and not unseeded and not random_call:
        findings.extend(_random_import_findings(label, module))
    findings.extend(_network_import_findings(label, module))
    return findings


def _note_call(
    label: str,
    node: ast.Call,
    imports: ImportMap,
    seeded: set[str],
    unseeded: set[str],
    global_seed: bool,
    suppress_time: bool,
    findings: list[Finding],
) -> bool:
    """Record a call finding. Return True when it is an unseeded random call."""
    if _is_seeded_instance_call(node, seeded):
        return False
    if _is_unseeded_instance_call(node, unseeded):
        display = _call_display(node.func)
        _add(findings, label, node, f"calls {display} on an unseeded random.Random")
        return True
    resolved = imports.resolve(node.func)
    if resolved is None:
        return False
    module, qual = resolved
    display = _call_display(node.func)
    if _is_global_random_call(module, qual):
        if not global_seed:
            _add(findings, label, node, f"calls {display} with no seed")
            return True
        return False
    if not suppress_time and _is_time_call(module, qual):
        _add(findings, label, node, f"calls {display} with no time fixture")
        return False
    if _is_network(module, qual):
        _add(findings, label, node, f"calls {display}, which can use the network")
    return False


def _fixtures(
    module: ast.Module,
) -> dict[str, ast.FunctionDef | ast.AsyncFunctionDef]:
    found: dict[str, ast.FunctionDef | ast.AsyncFunctionDef] = {}
    for node in module.body:
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)) and _is_fixture(
            node
        ):
            found[node.name] = node
    return found


def _is_fixture(func: ast.FunctionDef | ast.AsyncFunctionDef) -> bool:
    for deco in func.decorator_list:
        target = deco.func if isinstance(deco, ast.Call) else deco
        parts = dotted_name(target)
        if parts is not None and parts[-1] == "fixture":
            return True
    return False


def _freezes_time(func: ast.FunctionDef | ast.AsyncFunctionDef) -> bool:
    for node in ast.walk(func):
        if isinstance(node, ast.Name) and node.id == "freeze_time":
            return True
        if isinstance(node, ast.Attribute) and node.attr in {"now", "freeze_time"}:
            return True
        if isinstance(node, ast.Constant) and node.value in {
            "now",
            "time.time",
            "sleep",
        }:
            return True
    return False


def _param_names(func: ast.FunctionDef | ast.AsyncFunctionDef) -> set[str]:
    args = func.args
    names = {arg.arg for arg in args.args}
    names.update(arg.arg for arg in args.posonlyargs)
    names.update(arg.arg for arg in args.kwonlyargs)
    return names


def _random_instances(
    module: ast.Module, imports: ImportMap
) -> tuple[set[str], set[str]]:
    """Last assignment of a name wins, so a name is never both seeded and not."""
    latest: dict[str, bool] = {}
    for node in ast.walk(module):
        value: ast.expr | None
        targets: list[ast.expr]
        if isinstance(node, ast.Assign):
            value = node.value
            targets = list(node.targets)
        elif isinstance(node, ast.AnnAssign):
            value = node.value
            targets = [node.target]
        else:
            continue
        if not isinstance(value, ast.Call):
            continue
        if imports.resolve(value.func) != ("random", "Random"):
            continue
        is_seeded = bool(value.args or value.keywords)
        for target in targets:
            if isinstance(target, ast.Name):
                latest[target.id] = is_seeded
    seeded = {name for name, is_seeded in latest.items() if is_seeded}
    unseeded = {name for name, is_seeded in latest.items() if not is_seeded}
    return seeded, unseeded


def _has_random_seed(module: ast.Module, imports: ImportMap) -> bool:
    for node in ast.walk(module):
        if isinstance(node, ast.Call) and imports.resolve(node.func) == (
            "random",
            "seed",
        ):
            return True
    return False


def _is_seeded_instance_call(node: ast.Call, seeded: set[str]) -> bool:
    return (
        isinstance(node.func, ast.Attribute)
        and isinstance(node.func.value, ast.Name)
        and node.func.value.id in seeded
    )


def _is_unseeded_instance_call(node: ast.Call, unseeded: set[str]) -> bool:
    return (
        isinstance(node.func, ast.Attribute)
        and isinstance(node.func.value, ast.Name)
        and node.func.value.id in unseeded
    )


def _is_global_random_call(module: str, qual: str) -> bool:
    return module == "random" and qual not in {"seed", "Random"}


def _is_time_call(module: str, qual: str) -> bool:
    if module == "time" and qual in _TIME_CALLS:
        return True
    if module == "asyncio" and qual == "sleep":
        return True
    return module == "datetime" and qual.split(".")[-1] == "now"


def _is_network(module: str, qual: str) -> bool:
    full = f"{module}.{qual}" if qual else module
    return any(
        full == prefix or full.startswith(f"{prefix}.") for prefix in _NETWORK_PREFIXES
    )


def _random_import_findings(label: str, module: ast.Module) -> list[Finding]:
    findings: list[Finding] = []
    for node in module.body:
        if isinstance(node, ast.Import):
            for alias in node.names:
                if alias.name.split(".", maxsplit=1)[0] == "random":
                    _add(findings, label, node, "imports random with no seed")
        elif isinstance(node, ast.ImportFrom) and node.module == "random":
            names = ", ".join(alias.name for alias in node.names)
            _add(findings, label, node, f"imports random.{names} with no seed")
    return findings


def _network_import_findings(label: str, module: ast.Module) -> list[Finding]:
    findings: list[Finding] = []
    for node in module.body:
        if isinstance(node, ast.Import):
            for alias in node.names:
                if _is_network(alias.name, ""):
                    _add(
                        findings,
                        label,
                        node,
                        f"imports {alias.name}, which can use the network",
                    )
        elif isinstance(node, ast.ImportFrom):
            imported = node.module
            if imported is not None and _is_network(imported, ""):
                _add(
                    findings,
                    label,
                    node,
                    f"imports {imported}, which can use the network",
                )
    return findings


def _call_display(func: ast.AST) -> str:
    parts = dotted_name(func)
    if parts is None:
        return "call"
    return ".".join(parts)


def _add(findings: list[Finding], label: str, node: ast.AST, detail: str) -> None:
    findings.append(
        Finding(
            check=CHECK,
            severity=Severity.LOW,
            location=location(label, node),
            explanation=f"{location(label, node)} {detail}.",
        )
    )
