"""Write 33 invented flawed tasks, one planted flaw each.

The label in expected_findings.yaml is the flaw this script plants.
This script does not import the auditor and does not run the checks.
Good tasks are hand-written and are left alone.
"""

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SAMPLE = ROOT / "sample_tasks"

GOOD_TASKS = (
    "slugify",
    "merge_intervals",
    "parse_duration",
    "rate_limiter",
    "double",
    "both_positive",
    "last_char",
    "scale",
)

CHECKS = (
    "source_inspection_test",
    "weak_assertion",
    "hardcoded_solution",
    "brittle_format",
    "nondeterministic_test",
    "untested_requirement",
    "hidden_requirement",
    "solution_fails_tests",
    "cheat_solution_passes",
    "flaky_tests",
    "surviving_mutants",
)

CONFTEST = '''"""Pytest helpers for this invented task."""

from collections.abc import Callable
from typing import TypeVar

F = TypeVar("F", bound=Callable[..., object])


def covers(requirement_id: str) -> Callable[[F], F]:
    """Mark a test as covering one requirement id."""

    def decorator(func: F) -> F:
        func.__covers__ = requirement_id
        return func

    return decorator
'''

TRAILERS = (
    "abcdefghijabcdefghijabcdefghijabcdefghij",
    "0123456789012345678901234567890123456789",
    "zzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzz",
)


def main() -> None:
    """Regenerate the planted tasks under sample_tasks."""
    plants = list(_plants())
    if len(plants) != 33:
        raise SystemExit(f"expected 33 plants, got {len(plants)}")
    counts = {check: 0 for check in CHECKS}
    ids: set[str] = set()
    for plant in plants:
        if plant.task_id in ids or plant.task_id in GOOD_TASKS:
            raise SystemExit(f"duplicate task id {plant.task_id}")
        ids.add(plant.task_id)
        counts[plant.check] += 1
        _write(plant)
    for check, count in counts.items():
        if count != 3:
            raise SystemExit(f"{check} has {count} plants, expected 3")
        print(f"{check} {count}")
    print(f"total {len(plants)}")


class _Plant:
    def __init__(
        self,
        task_id: str,
        check: str,
        title: str,
        requirements: tuple[tuple[str, str], ...],
        instruction: str,
        module: str,
        solution: str,
        tests: str,
    ) -> None:
        self.task_id = task_id
        self.check = check
        self.title = title
        self.requirements = requirements
        self.instruction = instruction
        self.module = module
        self.solution = solution
        self.tests = tests


def _plants() -> list[_Plant]:
    plants: list[_Plant] = []
    plants.extend(_source_plants())
    plants.extend(_weak_plants())
    plants.extend(_hardcoded_plants())
    plants.extend(_brittle_plants())
    plants.extend(_random_plants())
    plants.extend(_untested_plants())
    plants.extend(_hidden_plants())
    plants.extend(_wrong_plants())
    plants.extend(_cheat_plants())
    plants.extend(_flaky_plants())
    plants.extend(_mutant_plants())
    return plants


def _source_plants() -> list[_Plant]:
    paths = (
        "solution/solution.py",
        "solution.py",
        "./solution/solution.py",
    )
    plants: list[_Plant] = []
    for index, path in enumerate(paths, start=1):
        plants.append(
            _fn(
                f"plant_source_inspection_{index}",
                "source_inspection_test",
                "Double an integer, but the test opens the solution",
                "def double(n: int) -> int:\n    return n * 2\n",
                _open_test(path),
                module="double",
            )
        )
    return plants


def _open_test(path: str) -> str:
    return f"""import contextlib

from conftest import covers
from double import double


@covers("R1")
def test_double() -> None:
    with contextlib.suppress(OSError):
        open({json.dumps(path)}, encoding="utf-8").close()
    assert double(3) == 6
    assert double(0) == 0
"""


def _weak_plants() -> list[_Plant]:
    solution = (
        "class Box:\n    def label(self, name: str) -> str:\n        return name\n"
    )
    bodies = (
        (
            ("from box import Box", "from conftest import covers"),
            '    Box().label("hi")\n',
        ),
        (("from conftest import covers",), "    assert True\n"),
        (
            ("from box import Box", "from conftest import covers"),
            '    assert Box().label("hi") is not None\n',
        ),
    )
    plants: list[_Plant] = []
    for index, (imports, body) in enumerate(bodies, start=1):
        tests = (
            _preamble(*imports) + '@covers("R1")\ndef test_label() -> None:\n' + body
        )
        plants.append(
            _fn(
                f"plant_weak_assertion_{index}",
                "weak_assertion",
                "Read a box label with a weak test",
                solution,
                tests,
                module="box",
            )
        )
    return plants


def _hardcoded_plants() -> list[_Plant]:
    specs = (
        (
            'def answer(name: str) -> str:\n    return "ok"\n',
            "answer",
            'def test_answer() -> None:\n    assert answer("a") == "ok"\n',
            ("from answer import answer", "from conftest import covers"),
        ),
        (
            "def seats(party: int) -> int:\n    return 5\n",
            "seats",
            "def test_seats() -> None:\n    assert seats(2) == 5\n",
            ("from conftest import covers", "from seats import seats"),
        ),
        (
            "def ready(code: int) -> bool:\n    return True\n",
            "ready",
            "def test_ready() -> None:\n    assert ready(2) == True  # noqa: E712\n",
            ("from conftest import covers", "from ready import ready"),
        ),
    )
    plants: list[_Plant] = []
    for index, (solution, module, test_body, imports) in enumerate(specs, start=1):
        tests = _covered(imports, test_body)
        plants.append(
            _fn(
                f"plant_hardcoded_solution_{index}",
                "hardcoded_solution",
                "Return a literal for every input",
                solution,
                tests,
                module=module,
            )
        )
    return plants


def _brittle_plants() -> list[_Plant]:
    plants: list[_Plant] = []
    for index, trailer in enumerate(TRAILERS, start=1):
        chunk = trailer[:10]
        solution = (
            "def banner(name: str) -> str:\n"
            f"    parts = [{json.dumps(chunk)}, {json.dumps(chunk)}, "
            f"{json.dumps(chunk)}, {json.dumps(chunk)}]\n"
            '    return name + "".join(parts)\n'
        )
        tests = _preamble(
            "from banner import banner",
            "from conftest import covers",
        ) + (
            '@covers("R1")\n'
            "def test_banner() -> None:\n"
            f'    assert banner("") == {json.dumps(trailer)}\n'
        )
        plants.append(
            _fn(
                f"plant_brittle_format_{index}",
                "brittle_format",
                "Append a fixed trailer",
                solution,
                tests,
                module="banner",
                instruction=(
                    "Write banner(name) so that it appends a fixed trailer.\n"
                    "The trailer text is not written in this instruction.\n"
                ),
            )
        )
    return plants


def _random_plants() -> list[_Plant]:
    calls = (
        "random.random() >= 0",
        "random.randint(5, 5) == 5",
        'random.choice(["red"]) == "red"',
    )
    plants: list[_Plant] = []
    for index, call in enumerate(calls, start=1):
        tests = (
            "import random\n"
            "\n"
            "from conftest import covers\n"
            "from double import double\n"
            "\n"
            "\n"
            '@covers("R1")\n'
            "def test_double() -> None:\n"
            f"    assert {call}\n"
            "    assert double(3) == 6\n"
        )
        plants.append(
            _fn(
                f"plant_nondeterministic_{index}",
                "nondeterministic_test",
                "Double an integer, but the test calls random",
                "def double(n: int) -> int:\n    return n * 2\n",
                tests,
                module="double",
            )
        )
    return plants


def _untested_plants() -> list[_Plant]:
    plants: list[_Plant] = []
    extras = ("R2", "R3", "R4")
    for index, extra in enumerate(extras, start=1):
        plants.append(
            _fn(
                f"plant_untested_requirement_{index}",
                "untested_requirement",
                "Double an integer",
                "def double(n: int) -> int:\n    return n * 2\n",
                _covered_double(),
                module="double",
                requirements=(
                    ("R1", "Return the integer multiplied by two."),
                    (extra, "Also reject a negative result."),
                ),
            )
        )
    return plants


def _hidden_plants() -> list[_Plant]:
    unmarked = (
        "from conftest import covers\n"
        "from double import double\n"
        "\n"
        "\n"
        '@covers("R1")\n'
        "def test_double() -> None:\n"
        "    assert double(3) == 6\n"
        "\n"
        "\n"
        "def test_another_value() -> None:\n"
        "    assert double(4) == 8\n"
    )
    unknown = (
        "from conftest import covers\n"
        "from double import double\n"
        "\n"
        "\n"
        '@covers("R9")\n'
        '@covers("R1")\n'
        "def test_double() -> None:\n"
        "    assert double(3) == 6\n"
    )
    secret = (
        "import pytest\n"
        "from conftest import covers\n"
        "from parse_code import parse_code\n"
        "\n"
        "\n"
        '@covers("R1")\n'
        "def test_reject() -> None:\n"
        '    with pytest.raises(ValueError, match="code was rejected"):\n'
        '        parse_code("nope")\n'
        "    assert 1 == 1\n"
    )
    return [
        _fn(
            "plant_hidden_requirement_1",
            "hidden_requirement",
            "Double an integer",
            "def double(n: int) -> int:\n    return n * 2\n",
            unmarked,
            module="double",
        ),
        _fn(
            "plant_hidden_requirement_2",
            "hidden_requirement",
            "Double an integer",
            "def double(n: int) -> int:\n    return n * 2\n",
            unknown,
            module="double",
        ),
        _fn(
            "plant_hidden_requirement_3",
            "hidden_requirement",
            "Reject a code",
            "def parse_code(text: str) -> str:\n"
            '    raise ValueError("code was rejected")\n',
            secret,
            module="parse_code",
            instruction=(
                "Write parse_code(text) so that it rejects a code "
                "this parser does not accept.\n"
            ),
        ),
    ]


def _wrong_plants() -> list[_Plant]:
    specs = (
        (
            "double",
            "def double(n: int) -> int:\n    return n + n + n\n",
            (
                "from conftest import covers",
                "from double import double",
            ),
            "def test_double() -> None:\n    assert double(3) == 6\n",
        ),
        (
            "shout",
            "def shout(text: str) -> str:\n    return text + text\n",
            (
                "from conftest import covers",
                "from shout import shout",
            ),
            'def test_shout() -> None:\n    assert shout("ab") == "AB"\n',
        ),
        (
            "bump",
            "def bump(n: int) -> int:\n    return n + n\n",
            (
                "from bump import bump",
                "from conftest import covers",
            ),
            "def test_bump() -> None:\n    assert bump(4) == 5\n",
        ),
    )
    plants: list[_Plant] = []
    for index, (module, solution, imports, body) in enumerate(specs, start=1):
        tests = _covered(imports, body)
        plants.append(
            _fn(
                f"plant_solution_fails_{index}",
                "solution_fails_tests",
                "The reference solution does not match the tests",
                solution,
                tests,
                module=module,
            )
        )
    return plants


def _cheat_plants() -> list[_Plant]:
    specs = (
        (
            "echo",
            "def echo(text: str) -> str:\n    return text\n",
            (
                "from conftest import covers",
                "from echo import echo",
            ),
            'def test_echo() -> None:\n    assert echo("hi") == "hi"\n',
        ),
        (
            "same",
            "def same(n: int) -> int:\n    return n\n",
            (
                "from conftest import covers",
                "from same import same",
            ),
            "def test_same() -> None:\n    assert same(4) == 4\n",
        ),
        (
            "keep",
            "def keep(flag: bool) -> bool:\n    return flag\n",
            (
                "from conftest import covers",
                "from keep import keep",
            ),
            "def test_keep() -> None:\n    assert keep(True) is True\n",
        ),
    )
    plants: list[_Plant] = []
    for index, (module, solution, imports, body) in enumerate(specs, start=1):
        tests = _covered(imports, body)
        plants.append(
            _fn(
                f"plant_cheat_passes_{index}",
                "cheat_solution_passes",
                "The tests accept the input unchanged",
                solution,
                tests,
                module=module,
            )
        )
    return plants


def _flaky_plants() -> list[_Plant]:
    specs = (
        (
            "double",
            "def double(n: int) -> int:\n    return n * 2\n",
            "from double import double",
            "double(3) == 6",
            "runs.txt",
        ),
        (
            "scale",
            "def scale(n: int) -> int:\n    return n * 10\n",
            "from scale import scale",
            "scale(3) == 30",
            "passes.txt",
        ),
        (
            "triple",
            "def triple(n: int) -> int:\n    return n * 3\n",
            "from triple import triple",
            "triple(2) == 6",
            "ticks.txt",
        ),
    )
    plants: list[_Plant] = []
    for index, (module, solution, imported, check, filename) in enumerate(
        specs, start=1
    ):
        tests = (
            "from pathlib import Path\n"
            "\n"
            + _preamble("from conftest import covers", imported)
            + "def test_once() -> None:\n"
            f"    path = Path({json.dumps(filename)})\n"
            '    seen = ""\n'
            "    if path.exists():\n"
            '        seen = path.read_text(encoding="utf-8")\n'
            '    path.write_text(seen + "x", encoding="utf-8")\n'
            '    assert seen == ""\n'
            f"    assert {check}\n"
        )
        tests = tests.replace(
            "def test_once() -> None:\n",
            '@covers("R1")\ndef test_once() -> None:\n',
            1,
        )
        plants.append(
            _fn(
                f"plant_flaky_tests_{index}",
                "flaky_tests",
                "A counter file changes across runs in one directory",
                solution,
                tests,
                module=module,
            )
        )
    return plants


def _mutant_plants() -> list[_Plant]:
    specs = (
        (
            "add_two",
            "def add_two(n: int) -> int:\n    return n + 2\n",
            (
                "from add_two import add_two",
                "from conftest import covers",
            ),
            "assert add_two(3) > 4\n",
        ),
        (
            "pad",
            "def pad(n: int) -> int:\n    return n + 10\n",
            (
                "from conftest import covers",
                "from pad import pad",
            ),
            "assert pad(1) > 10\n",
        ),
        (
            "widen",
            "def widen(n: int) -> int:\n    return n + 4\n",
            (
                "from conftest import covers",
                "from widen import widen",
            ),
            "assert widen(2) >= 6\n",
        ),
    )
    plants: list[_Plant] = []
    for index, (module, solution, imports, assertion) in enumerate(specs, start=1):
        tests = _preamble(*imports) + (
            f'@covers("R1")\ndef test_shift() -> None:\n    {assertion}'
        )
        plants.append(
            _fn(
                f"plant_surviving_mutants_{index}",
                "surviving_mutants",
                "A weak comparison lets an off-by-one change survive",
                solution,
                tests,
                module=module,
            )
        )
    return plants


def _preamble(*imports: str) -> str:
    return "\n".join(imports) + "\n\n\n"


def _covered(imports: tuple[str, ...], body: str) -> str:
    return _preamble(*imports) + '@covers("R1")\n' + body


def _covered_double() -> str:
    return (
        "from conftest import covers\n"
        "from double import double\n"
        "\n"
        "\n"
        '@covers("R1")\n'
        "def test_double() -> None:\n"
        "    assert double(3) == 6\n"
        "    assert double(0) == 0\n"
        "    assert double(-2) == -4\n"
    )


def _fn(
    task_id: str,
    check: str,
    title: str,
    solution: str,
    tests: str,
    *,
    module: str,
    instruction: str | None = None,
    requirements: tuple[tuple[str, str], ...] | None = None,
) -> _Plant:
    if instruction is None:
        instruction = (
            f"Write {module} so that it follows the requirement in task.yaml.\n"
        )
    if requirements is None:
        requirements = (("R1", "Follow the behavior the tests describe."),)
    return _Plant(
        task_id,
        check,
        title,
        requirements,
        instruction,
        module,
        solution,
        tests,
    )


def _write(plant: _Plant) -> None:
    root = SAMPLE / plant.task_id
    if root.exists():
        for path in sorted(root.rglob("*"), reverse=True):
            if path.is_file():
                path.unlink()
        for path in sorted(root.rglob("*"), reverse=True):
            if path.is_dir():
                path.rmdir()
    (root / "environment").mkdir(parents=True)
    (root / "solution").mkdir(parents=True)
    (root / "tests").mkdir(parents=True)
    (root / "task.yaml").write_text(_task_yaml(plant), encoding="utf-8")
    (root / "instruction.md").write_text(plant.instruction, encoding="utf-8")
    (root / "expected_findings.yaml").write_text(
        f"- {plant.check}\n",
        encoding="utf-8",
    )
    starter = _starter(plant.solution)
    (root / "environment" / f"{plant.module}.py").write_text(starter, encoding="utf-8")
    (root / "solution" / "solution.py").write_text(plant.solution, encoding="utf-8")
    (root / "tests" / "conftest.py").write_text(CONFTEST, encoding="utf-8")
    test_path = root / "tests" / f"test_{plant.module}.py"
    test_path.write_text(plant.tests, encoding="utf-8")


def _starter(solution: str) -> str:
    lines: list[str] = []
    for line in solution.splitlines():
        if line.startswith("class "):
            lines.extend(
                [
                    line,
                    '    """Starter implementation. Replace this body."""',
                    "",
                    "    pass",
                    "",
                ]
            )
        elif line.startswith("def "):
            lines.extend(
                [
                    line,
                    '    """Starter implementation. Replace this body."""',
                    "    raise NotImplementedError",
                    "",
                ]
            )
    return "\n".join(lines).rstrip() + "\n"


def _task_yaml(plant: _Plant) -> str:
    lines = [
        f"id: {plant.task_id}",
        f"title: {plant.title}",
        "language: python",
        "requirements:",
    ]
    for requirement_id, text in plant.requirements:
        lines.append(f"  - id: {requirement_id}")
        lines.append(f"    text: {text}")
    return "\n".join(lines) + "\n"


if __name__ == "__main__":
    main()
