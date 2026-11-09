"""Snippet tests for nondeterministic_test."""

import pytest

from auditor.checks.model import Severity
from auditor.checks.nondeterministic import run_nondeterministic_test
from tests.check_support import assert_one_sentence, snippet_target

_POSITIVES: list[tuple[str, str]] = [
    (
        "import random\n\ndef test_roll() -> None:\n    assert random.random() >= 0\n",
        "random.random",
    ),
    (
        "import random\n\ndef test_imports_random() -> None:\n    assert True\n",
        "imports random",
    ),
    (
        "import time\n\ndef test_wait() -> None:\n    time.sleep(0)\n    assert True\n",
        "time.sleep",
    ),
    (
        "import time\n\ndef test_clock() -> None:\n    assert time.time() > 0\n",
        "time.time",
    ),
    (
        "import datetime\n\n"
        "def test_year() -> None:\n"
        "    assert datetime.datetime.now().year > 2000\n",
        "datetime.datetime.now",
    ),
    (
        "import requests\n\ndef test_marker() -> None:\n    assert True\n",
        "requests",
    ),
    (
        "import socket\n\n"
        "def test_open_socket() -> None:\n"
        "    assert socket.socket() is not None\n",
        "socket",
    ),
    (
        "import asyncio\n\ndef test_pause() -> None:\n    asyncio.sleep(0)\n",
        "asyncio.sleep",
    ),
]


@pytest.mark.parametrize(("source", "evidence"), _POSITIVES)
def test_nondeterministic_uses_are_flagged(source: str, evidence: str) -> None:
    findings = run_nondeterministic_test(snippet_target(source))

    assert findings
    assert any(evidence in finding.explanation for finding in findings)
    for finding in findings:
        assert finding.check == "nondeterministic_test"
        assert finding.severity == Severity.LOW
        assert_one_sentence(finding.explanation)


@pytest.mark.parametrize(
    "source",
    [
        "def test_add() -> None:\n    assert 1 + 1 == 2\n",
        (
            "import random\n\n"
            "def test_roll() -> None:\n"
            "    random.seed(1)\n"
            "    assert random.random() >= 0\n"
        ),
        (
            "import time\n\n"
            "def test_year() -> None:\n"
            '    assert time.strftime("%Y", time.gmtime(0)) == "1970"\n'
        ),
    ],
)
def test_seeded_or_deterministic_code_is_not_flagged(source: str) -> None:
    assert run_nondeterministic_test(snippet_target(source)) == []


def test_random_instance_constructed_with_a_seed_is_not_flagged() -> None:
    source = (
        "import random\n\n"
        "def test_draw() -> None:\n"
        "    seed = 1\n"
        "    rng = random.Random(seed)\n"
        "    value = rng.random()\n"
        "    assert 0.0 <= value <= 1.0\n"
    )
    assert run_nondeterministic_test(snippet_target(source)) == []


def test_later_unseeded_random_replaces_an_earlier_seed() -> None:
    source = (
        "import random\n\n"
        "def test_draw() -> None:\n"
        "    rng = random.Random(1)\n"
        "    rng = random.Random()\n"
        "    assert rng.random() >= 0\n"
    )
    findings = run_nondeterministic_test(snippet_target(source))
    assert any("unseeded random.Random" in finding.explanation for finding in findings)


def test_fixture_that_freezes_time_is_not_flagged() -> None:
    source = (
        "import datetime\n\n"
        "import pytest\n\n"
        "@pytest.fixture\n"
        "def frozen_clock(monkeypatch: object) -> None:\n"
        "    class Clock:\n"
        "        @staticmethod\n"
        "        def now() -> datetime.datetime:\n"
        "            return datetime.datetime(2020, 1, 1)\n\n"
        '    monkeypatch.setattr(datetime.datetime, "now", Clock.now)\n\n'
        "def test_stamp(frozen_clock: object) -> None:\n"
        "    assert datetime.datetime.now().year == 2020\n"
    )
    assert run_nondeterministic_test(snippet_target(source)) == []


def test_unrelated_fixture_does_not_hide_datetime_now() -> None:
    source = (
        "import datetime\n\n"
        "import pytest\n\n"
        "@pytest.fixture\n"
        "def unused_value() -> int:\n"
        "    return 1\n\n"
        "def test_year(unused_value: int) -> None:\n"
        "    assert datetime.datetime.now().year > 2000\n"
    )
    findings = run_nondeterministic_test(snippet_target(source))
    assert any("datetime.datetime.now" in finding.explanation for finding in findings)
