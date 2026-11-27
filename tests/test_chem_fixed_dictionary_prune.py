import unittest

import numpy as np

from tools.chem_fixed_dictionary_prune import omission_bounds, pair_colors, prune


class ChemistryPruneTests(unittest.TestCase):
    def test_correlated_projection_matches_direct_refit(self) -> None:
        dictionary = np.asarray([[1.0, 0.0, 0.0], [1.0, 1.0, 0.0], [0.0, 1.0, 1.0]])
        coefficients = np.asarray([[1.0, 2.0], [3.0, 4.0], [0.5, 1.0]])
        target = dictionary.T @ coefficients
        for keep in (1, 2, 3):
            result = prune(dictionary @ dictionary.T, coefficients, keep)
            retained = dictionary[result.selected].T
            direct = np.linalg.lstsq(retained, target, rcond=None)[0]
            np.testing.assert_allclose(direct, result.weights, atol=1e-12)
            self.assertAlmostEqual(float(np.linalg.norm(retained @ direct - target) ** 2), result.total_squared_loss)

    def test_singleton_bound_matches_direct_selected_span(self) -> None:
        features = np.asarray([[1.0, 1.0, 0.0], [0.0, 1.0, 1.0]])
        target = np.asarray([[1.0, 2.0, 0.5], [2.0, 3.0, 0.0], [0.5, 0.0, -0.5]])
        result = omission_bounds(features, target, group_width=2)
        self.assertEqual(result["status"], "working_precision")
        groups = result["groups"]
        assert isinstance(groups, list)
        bounds = np.asarray(groups[0]["singleton_residuals"])
        for omitted in range(2):
            retained = features[1 - omitted]
            projector = np.outer(retained, retained) / np.dot(retained, retained)
            self.assertAlmostEqual(float(bounds[omitted]), float(np.linalg.norm(target - projector @ target @ projector)))

    def test_pair_coloring_distinguishes_compatible_and_incompatible(self) -> None:
        dual = np.asarray([[1.0, 0.6], [0.0, 0.8]])
        for diagonal, expected_colors in ((0.010, 2), (0.016, 1)):
            action = diagonal * dual
            self.assertEqual(len(pair_colors(dual, action, 0.0)), expected_colors)


if __name__ == "__main__":
    unittest.main()
