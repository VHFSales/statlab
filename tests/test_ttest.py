import math
import unittest

from statistics import anova, ttest
from statistics.anova import InsufficientDataError
from statistics.types import RawGroup


class TestStudentT(unittest.TestCase):
    def test_f_equals_t_squared(self):
        a = [10.2, 10.8, 11.1, 10.6, 10.4]
        b = [13.5, 14.0, 13.8, 14.2, 13.9]
        tt = ttest.student_t(RawGroup("A", a), RawGroup("B", b))
        table = anova.anova_oneway_raw([RawGroup("A", a), RawGroup("B", b)])
        self.assertAlmostEqual(tt.statistic ** 2, table.f, places=9)
        # p from t (2-sided) equals ANOVA p for k=2
        self.assertAlmostEqual(tt.p, table.p, places=9)

    def test_known_reference(self):
        # Classic example: A=[1,2,3,4,5], B=[2,4,6,8,10]
        # mean1=3, mean2=6, diff=-3; pooled var = (2.5+10)/... check t sign/magnitude
        a = [1, 2, 3, 4, 5]
        b = [2, 4, 6, 8, 10]
        tt = ttest.student_t(RawGroup("A", a), RawGroup("B", b))
        self.assertAlmostEqual(tt.diff, -3.0, places=9)
        self.assertEqual(tt.df, 8)
        # significance direction
        self.assertTrue(0.0 <= tt.p <= 1.0)

    def test_ci_contains_diff(self):
        tt = ttest.student_t(RawGroup("A", [1, 2, 3, 4]),
                             RawGroup("B", [3, 4, 5, 6]))
        self.assertLessEqual(tt.ci_low, tt.diff)
        self.assertGreaterEqual(tt.ci_high, tt.diff)

    def test_small_n_refused(self):
        with self.assertRaises(InsufficientDataError):
            ttest.student_t(RawGroup("A", [5]), RawGroup("B", [1, 2, 3]))


class TestWelchT(unittest.TestCase):
    def test_unequal_variance(self):
        a = [27, 26, 21, 24, 15, 18, 25, 23]
        b = [40, 38, 42, 39, 41, 44, 43]
        tt = ttest.welch_t(RawGroup("A", a), RawGroup("B", b))
        # groups clearly separated -> significant
        self.assertTrue(tt.significant)
        # Welch df is fractional and <= n1+n2-2
        self.assertLessEqual(tt.df, len(a) + len(b) - 2 + 1e-9)
        self.assertGreater(tt.df, 1)

    def test_welch_df_formula(self):
        a = [1.0, 2.0, 3.0, 4.0]      # var = 5/3
        b = [10.0, 20.0, 30.0]        # var = 100
        tt = ttest.welch_t(RawGroup("A", a), RawGroup("B", b))
        n1, n2 = 4, 3
        v1 = sum((x - 2.5) ** 2 for x in a) / (n1 - 1)
        m2 = 20.0
        v2 = sum((x - m2) ** 2 for x in b) / (n2 - 1)
        A, B = v1 / n1, v2 / n2
        expected_df = (A + B) ** 2 / (A ** 2 / (n1 - 1) + B ** 2 / (n2 - 1))
        self.assertAlmostEqual(tt.df, expected_df, places=9)


if __name__ == "__main__":
    unittest.main()
