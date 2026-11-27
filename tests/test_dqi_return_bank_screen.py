import lzma
from pathlib import Path
from random import Random
from tempfile import TemporaryDirectory
import unittest

from tools.dqi_return_bank_screen import Displacements, screen


class ReturnBankScreenTests(unittest.TestCase):
    def test_displacements_match_explicit_sets(self) -> None:
        width = 5
        rng = Random(50189)
        space = Displacements(width)
        states = {0}
        for _ in range(512):
            left, right = rng.sample(range(width), 2)
            left_bit, right_bit = 1 << left, 1 << right
            op = rng.randrange(4)
            if op == 0:
                space.measure(left)
                states = {state & ~left_bit for state in states if not state & left_bit}
                states |= {state | left_bit for state in states}
            elif op == 1:
                space.require_zero(left)
                states = {state for state in states if not state & left_bit}
            elif op == 2:
                space.cx(left, right)
                states = {state ^ right_bit if state & left_bit else state for state in states}
            else:
                space.swap(left, right)
                states = {
                    state ^ (left_bit | right_bit) if bool(state & left_bit) != bool(state & right_bit) else state
                    for state in states
                }
            self.assertEqual(1 << space.dimension, len(states))
            for wire in range(width):
                self.assertEqual(space.constraints[wire] == 0, 1 << wire in states)
                self.assertEqual(bool(space.vectors[wire]), any(state & (1 << wire) for state in states))

    def test_joint_deletions_and_boundaries(self) -> None:
        with TemporaryDirectory() as temporary:
            source = Path(temporary) / "fixture.kmx.xz"
            cases = (
                (b"CCX q0 q1 q2\nCX q2 q3\nHMR q2 b0\nHMR q3 b1\n", 1),
                (b"CCX q0 q1 q2\nCCX q2 q3 q4\nHMR q2 b0\nHMR q4 b1\n", 2),
                (b"CCX q0 q1 q2\nCZ q2 q0\nHMR q2 b0\n", 0),
                (b"CCX q0 q1 q2\nPUSH_CONDITION b0\nHMR q2 b1\nPOP_CONDITION\n", 0),
            )
            for assembly, expected in cases:
                with self.subTest(assembly=assembly):
                    source.write_bytes(lzma.compress(assembly))
                    self.assertEqual(screen(source, width=5)["ccx_savings_ceiling"], expected)


if __name__ == "__main__":
    unittest.main()
