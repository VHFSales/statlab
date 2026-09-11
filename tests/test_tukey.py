import unittest

from statistics import tukey, anova
from statistics.types import RawGroup
from tests.reference_data import ANOVA3


def groups_from(d):
    return [RawGroup(k, v) for k, v in d.items() if isinstance(v, list)]


class TestTukey(unittest.TestCase):
    def setUp(self):
        self.groups = groups_from(ANOVA3)
        self.res = tukey.tukey_raw(self.groups, alpha=0.05)

    def test_method_label_balanced(self):
        self.assertEqual(self.res.method, "Tukey HSD")

    def test_number_of_comparisons(self):
        self.assertEqual(len(self.res.comparisons), 3)  # C(3,2)

    def test_direction_of_difference(self):
        # means A=5, B=9, C=10 -> A - B = -4
        ab = next(c for c in self.res.comparisons
                  if {c.group1, c.group2} == {"A", "B"})
        self.assertAlmostEqual(ab.diff, -4.0, places=9)

    def test_ci_contains_diff(self):
        for c in self.res.comparisons:
            self.assertLessEqual(c.ci_low, c.diff)
            self.assertGreaterEqual(c.ci_high, c.diff)

    def test_adjusted_p_between_0_and_1(self):
        for c in self.res.comparisons:
            self.assertTrue(0.0 <= c.p_adjusted <= 1.0)

    def test_significance_consistent_with_ci(self):
        # a pair is significant iff its simultaneous CI excludes 0
        for c in self.res.comparisons:
            ci_excludes_zero = (c.ci_low > 0) or (c.ci_high < 0)
            self.assertEqual(c.significant, ci_excludes_zero)

    def test_unbalanced_uses_kramer(self):
        g = [RawGroup("A", [1, 2, 3, 4, 5]), RawGroup("B", [6, 7, 8]),
             RawGroup("C", [9, 10, 11, 12])]
        res = tukey.tukey_raw(g)
        self.assertEqual(res.method, "Tukey-Kramer")

    def test_balanced_kramer_equals_hsd(self):
        # With balanced n the Tukey-Kramer SE reduces exactly to Tukey HSD SE.
        # (Same code path; assert SE uses (1/n+1/n) correctly = 2/n.)
        c = self.res.comparisons[0]
        table = anova.anova_oneway_raw(self.groups)
        import math
        expected_se = math.sqrt(table.ms_within / 2.0 * (1 / 6 + 1 / 6))
        self.assertAlmostEqual(c.se, expected_se, places=12)


if __name__ == "__main__":
    unittest.main()
