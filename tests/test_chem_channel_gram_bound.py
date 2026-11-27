from fractions import Fraction
import unittest

import numpy as np

from tools.chem_channel_gram_bound import Normalizations, exact_group


class ChannelGramBoundTests(unittest.TestCase):
    def test_signed_pair_cancellation(self) -> None:
        weights = np.asarray([[1.0, 1.0], [1.0, -1.0]])
        self.assertEqual(exact_group(weights), Normalizations(Fraction(1), Fraction(2), Fraction(1, 2), Fraction(0)))

    def test_common_scale_and_orthogonal_invariance(self) -> None:
        weights = np.asarray([[1.0, 0.0, 0.0, 0.0], [-0.25, 0.5, 0.0, 0.0]])
        rotation = np.asarray([[1, 1, 1, 1], [1, -1, 1, -1], [1, 1, -1, -1], [1, -1, -1, 1]]) / 2
        lower = Fraction(29, 64)
        self.assertEqual(exact_group(weights), Normalizations(lower, lower, Fraction(1, 4), Fraction(0)))
        rotated = exact_group(weights @ rotation)
        self.assertEqual(rotated.gram_bound, lower)
        self.assertEqual(rotated.weight_gram_bound, Fraction(1, 4))
        self.assertGreater(rotated.current, lower)

    def test_negative_gram_sum_excludes_the_identity_row(self) -> None:
        weights = np.asarray([[1.0, 0.0], [-0.25, 0.5], [0.0, -1.0]])
        self.assertEqual(exact_group(weights).negative_weight_gram_sum, Fraction(1, 2))


if __name__ == "__main__":
    unittest.main()
