import math
import unittest

from statistics import anova, descriptive
from statistics.anova import InsufficientDataError
from statistics.types import RawGroup, SummaryGroup
from tests.reference_data import ANOVA3, TWO_GROUPS


def groups_from(d):
    return [RawGroup(k, v) for k, v in d.items() if isinstance(v, list)]


class TestAnovaRaw(unittest.TestCase):
    def setUp(self):
        self.t = anova.anova_oneway_raw(groups_from(ANOVA3))

    def test_sums_of_squares(self):
        self.assertAlmostEqual(self.t.ss_between, ANOVA3["ss_between"], places=9)
        self.assertAlmostEqual(self.t.ss_within, ANOVA3["ss_within"], places=9)
        self.assertAlmostEqual(self.t.ss_total, ANOVA3["ss_total"], places=9)

    def test_decomposition_identity(self):
        self.assertAlmostEqual(self.t.ss_between + self.t.ss_within,
                               self.t.ss_total, places=9)

    def test_df(self):
        self.assertEqual(self.t.df_between, ANOVA3["df_between"])
        self.assertEqual(self.t.df_within, ANOVA3["df_within"])

    def test_f_and_p(self):
        self.assertAlmostEqual(self.t.f, ANOVA3["F"], places=6)
        self.assertAlmostEqual(self.t.p, ANOVA3["p"], places=9)


class TestAnovaSummaryEqualsRaw(unittest.TestCase):
    def test_equivalence(self):
        raw = anova.anova_oneway_raw(groups_from(ANOVA3))
        sg = []
        for lab in ("A", "B", "C"):
            dr = descriptive.describe_group(lab, ANOVA3[lab])
            sg.append(SummaryGroup(lab, dr.mean, dr.sd, dr.n))
        summ = anova.anova_oneway_summary(sg)
        self.assertAlmostEqual(summ.f, raw.f, places=9)
        self.assertAlmostEqual(summ.ss_between, raw.ss_between, places=9)
        self.assertAlmostEqual(summ.ss_within, raw.ss_within, places=9)


class TestFEqualsTSquared(unittest.TestCase):
    def test_two_group_identity(self):
        a, b = TWO_GROUPS["A"], TWO_GROUPS["B"]
        t = anova.anova_oneway_raw([RawGroup("A", a), RawGroup("B", b)])
        na, nb = len(a), len(b)
        ma, mb = sum(a) / na, sum(b) / nb
        va = sum((x - ma) ** 2 for x in a) / (na - 1)
        vb = sum((x - mb) ** 2 for x in b) / (nb - 1)
        sp2 = ((na - 1) * va + (nb - 1) * vb) / (na + nb - 2)
        tstat = (ma - mb) / math.sqrt(sp2 * (1 / na + 1 / nb))
        self.assertAlmostEqual(t.f, tstat ** 2, places=9)


class TestAnovaEdgeCases(unittest.TestCase):
    def test_zero_within_variance_refused(self):
        with self.assertRaises(InsufficientDataError):
            anova.anova_oneway_raw([RawGroup("A", [5, 5, 5]), RawGroup("B", [7, 7, 7])])

    def test_single_group_refused(self):
        with self.assertRaises(InsufficientDataError):
            anova.anova_oneway_raw([RawGroup("A", [1, 2, 3])])

    def test_missing_values_ignored_not_zeroed(self):
        # NaN must be dropped, not treated as 0.
        g = [RawGroup("A", [1.0, 2.0, float("nan"), 3.0]),
             RawGroup("B", [4.0, 5.0, 6.0])]
        t = anova.anova_oneway_raw(g)
        # group A effectively [1,2,3] -> N=6, k=2, df_within=4
        self.assertEqual(t.df_within, 4)

    def test_unequal_n(self):
        g = [RawGroup("A", [1, 2, 3, 4]), RawGroup("B", [5, 6]),
             RawGroup("C", [7, 8, 9])]
        t = anova.anova_oneway_raw(g)
        self.assertEqual(t.n_total, 9)
        self.assertEqual(t.df_between, 2)
        self.assertEqual(t.df_within, 6)


if __name__ == "__main__":
    unittest.main()
