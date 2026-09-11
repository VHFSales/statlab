import math
import unittest

from statistics import descriptive


class TestDescriptive(unittest.TestCase):
    def test_known_values(self):
        d = descriptive.describe_group("X", [2, 4, 4, 4, 5, 5, 7, 9])
        self.assertAlmostEqual(d.mean, 5.0, places=12)
        self.assertAlmostEqual(d.variance, 32.0 / 7.0, places=9)  # ddof=1
        self.assertAlmostEqual(d.sd, math.sqrt(32.0 / 7.0), places=9)
        self.assertAlmostEqual(d.median, 4.5, places=12)

    def test_quartiles_type7(self):
        d = descriptive.describe_group("X", [2, 4, 4, 4, 5, 5, 7, 9])
        self.assertAlmostEqual(d.q1, 4.0, places=12)
        self.assertAlmostEqual(d.q3, 5.5, places=12)
        self.assertAlmostEqual(d.iqr, 1.5, places=12)

    def test_se_and_ci(self):
        d = descriptive.describe_group("X", [10, 12, 14, 16, 18])  # mean 14, sd sqrt(10)
        self.assertAlmostEqual(d.mean, 14.0, places=12)
        self.assertAlmostEqual(d.sd, math.sqrt(10.0), places=9)
        self.assertAlmostEqual(d.se, math.sqrt(10.0) / math.sqrt(5), places=9)
        self.assertLess(d.ci_low, d.mean)
        self.assertGreater(d.ci_high, d.mean)

    def test_missing_not_zeroed(self):
        d = descriptive.describe_group("X", [1.0, float("nan"), 3.0])
        self.assertEqual(d.n, 2)
        self.assertEqual(d.n_missing, 1)
        self.assertAlmostEqual(d.mean, 2.0, places=12)  # (1+3)/2, NOT (1+0+3)/3

    def test_single_value(self):
        d = descriptive.describe_group("X", [42.0])
        self.assertEqual(d.n, 1)
        self.assertTrue(math.isnan(d.sd))
        self.assertTrue(math.isnan(d.ci_low))

    def test_cv_flagged_near_zero_mean(self):
        d = descriptive.describe_group("X", [-1.0, 0.0, 1.0])  # mean 0
        self.assertTrue(math.isnan(d.cv))


if __name__ == "__main__":
    unittest.main()
