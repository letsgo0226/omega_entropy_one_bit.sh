#!/usr/bin/env python3
"""Verify the one-bit state model; this does not measure physical RNG entropy."""

import contextlib
import io
import json
import math
from pathlib import Path
import shlex
import subprocess
import sys
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "omega_entropy_one_bit.sh"
CORE = b"OMEGA|ONTOLOGICAL_TM|FIXPOINT"


def load_source():
    text = SCRIPT.read_text(encoding="utf-8")
    words = shlex.split(text)
    return text, words[words.index("-c") + 1]


def run_model(source, bit, rounds=8):
    """Enumerate an assumed branch and inspect actual state bytes at each step."""
    namespace = {}
    records = []
    snapshots = []

    def capture_print(payload):
        row = json.loads(payload)
        records.append(row)
        if "n" in row:
            snapshots.append(tuple(namespace["states"]))

    namespace["print"] = capture_print
    status = 0
    with patch.object(sys, "argv", ["omega", str(rounds)]):
        with patch("secrets.randbits", return_value=bit) as draw:
            with contextlib.redirect_stdout(io.StringIO()):
                try:
                    exec(compile(source, str(SCRIPT), "exec"), namespace)
                except SystemExit as error:
                    status = error.code
            calls = draw.call_count
    return namespace, records, snapshots, status, calls


def entropy_of_equal_branches(outcomes):
    """Independent entropy calculation for two equally weighted source cases."""
    probabilities = {}
    for outcome in outcomes:
        probabilities[outcome] = probabilities.get(outcome, 0) + 0.5
    return -sum(p * math.log2(p) for p in probabilities.values())


class OneBitModelTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.shell_source, cls.python_source = load_source()

    def test_one_line_under_two_kib(self):
        self.assertLess(len(SCRIPT.read_bytes()), 2048)
        self.assertEqual(len(self.shell_source.splitlines()), 1)

    def test_real_shell_run_is_finite_and_keeps_the_initial_bit(self):
        result = subprocess.run(
            ["sh", str(SCRIPT), "8"],
            check=True, capture_output=True, text=True, timeout=15,
        )
        header, *rows = [json.loads(line) for line in result.stdout.splitlines()]
        self.assertEqual(header["MODEL"], "ONE_FAIR_BIT_REUSED")
        self.assertIs(header["RNG_PHYSICAL_ENTROPY_VERIFIED"], False)
        self.assertEqual([row["n"] for row in rows], list(range(1, 9)))
        self.assertEqual(len({row["BIT"] for row in rows}), 1)
        self.assertTrue(all(row["SPEC_OK"] for row in rows))

    def test_both_actual_state_paths_and_whole_history_have_one_model_bit(self):
        selected_paths = []
        printed_paths = []
        for bit in (0, 1):
            namespace, records, snapshots, status, calls = run_model(
                self.python_source, bit,
            )
            self.assertEqual(status, 0)
            self.assertEqual(calls, 1, "Repeated RNG draws change the history model")
            self.assertEqual(len(snapshots), 8)
            self.assertEqual([r["n"] for r in records[1:]], list(range(1, 9)))
            selected_paths.append(tuple(states[bit] for states in snapshots))
            printed_paths.append(tuple(json.dumps(r, sort_keys=True) for r in records[1:]))
            for row, states in zip(records[1:], snapshots):
                self.assertEqual(len(states), 2)
                self.assertNotEqual(states[0], states[1])
                self.assertEqual(entropy_of_equal_branches(states), 1)
                self.assertEqual(row["H_MODEL_BITS"], 1)
                self.assertEqual(row["BIT"], bit)
                self.assertEqual(row["STATE_BYTES"], len(states[bit]))
                self.assertIs(row["SPEC_OK"], True)
                for candidate, state in enumerate(states):
                    self.assertEqual(state.split(b"\n", 1)[0], CORE)
                    self.assertTrue(state.endswith(b"\nBIT=" + str(candidate).encode()))
                    self.assertEqual(namespace["D"](namespace["E"](state)), state)
            self.assertTrue(all(transform(CORE) == CORE for transform in namespace["F"]))
        self.assertEqual(entropy_of_equal_branches(selected_paths), 1)
        self.assertEqual(entropy_of_equal_branches(printed_paths), 1)
        for index in range(8):
            self.assertEqual(
                entropy_of_equal_branches([path[index] for path in selected_paths]), 1,
            )

    def test_encoding_preserves_empty_leading_zero_and_high_bytes(self):
        namespace, _, _, status, _ = run_model(self.python_source, 0, rounds=1)
        self.assertEqual(status, 0)
        examples = (b"", b"\0", b"\0\0", bytes(range(256)), b"\xff" * 100)
        for example in examples:
            with self.subTest(example=example[:16]):
                self.assertEqual(namespace["D"](namespace["E"](example)), example)

    def test_biased_probability_model_is_rejected(self):
        old = "P=(0.5,0.5)"
        self.assertEqual(self.python_source.count(old), 1)
        changed = self.python_source.replace(old, "P=(0.75,0.25)")
        _, rows, _, status, _ = run_model(changed, 0)
        self.assertEqual(status, 1)
        self.assertIs(rows[-1]["SPEC_OK"], False)
        self.assertAlmostEqual(rows[-1]["H_MODEL_BITS"], 0.8112781244591328)

    def test_merging_the_two_state_outcomes_is_rejected(self):
        old = "bytes([48+k])"
        self.assertEqual(self.python_source.count(old), 1)
        changed = self.python_source.replace(old, "bytes([48])")
        _, rows, _, status, _ = run_model(changed, 0)
        self.assertEqual(status, 1)
        self.assertIs(rows[-1]["SPEC_OK"], False)
        self.assertEqual(rows[-1]["H_MODEL_BITS"], 0)


if __name__ == "__main__":
    unittest.main(verbosity=2)
