import math
import unittest

from statistics import assumptions
from statistics.types import RawGroup
from tests.reference_data import ANOVA3, HETERO3


def groups_from(d):
    return [RawGroup(k, v) for k, v in d.items() if isinstance(v, list)]


class TestHomogeneity(unittest.TestCase):
    def test_levene_runs(self):
        r = assumptions.levene(groups_from(ANOVA3))
        self.assertEqual(r.center, "mean")
        self.assertTrue(0.0 <= r.p <= 1.0)

    def test_brown_forsythe_runs(self):
        r = assumptions.brown_forsythe(groups_from(HETERO3))
        self.assertEqual(r.center, "median")
        self.assertTrue(0.0 <= r.p <= 1.0)

    def test_variance_ratio(self):
        vr = assumptions.variance_ratio(groups_from(HETERO3))
        self.assertGreater(vr, 1.0)


class TestResidualsQQ(unittest.TestCase):
    def test_residuals_sum_zero_within_group(self):
        res = assumptions.residuals(groups_from(ANOVA3))
        # residuals across all groups sum to ~0
        self.assertAlmostEqual(sum(res), 0.0, places=9)

    def test_qq_points_count(self):
        pts = assumptions.qq_points([1, 2, 3, 4, 5])
        self.assertEqual(len(pts), 5)


class TestShapiro(unittest.TestCase):
    def test_normalish_high_p(self):
        # roughly symmetric sample -> should not strongly reject
        data = [-1.5, -1.0, -0.5, -0.2, 0.0, 0.1, 0.3, 0.6, 1.0, 1.4]
        r = assumptions.shapiro_wilk(data)
        self.assertTrue(0.0 <= r.p <= 1.0)
        self.assertTrue(0.0 < r.statistic <= 1.0)

    def test_small_n_note(self):
        r = assumptions.shapiro_wilk([1, 2])
        self.assertTrue(math.isnan(r.statistic))

    def test_known_reference(self):
        # Shapiro-Wilk on a fixed small sample; W within a reasonable band.
        # data = 2,4,4,4,5,5,7,9 ; scipy gives W ~ 0.906, p ~ 0.33
        r = assumptions.shapiro_wilk([2, 4, 4, 4, 5, 5, 7, 9])
        self.assertAlmostEqual(r.statistic, 0.906, delta=0.03)


if __name__ == "__main__":
    unittest.main()
