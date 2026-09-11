import math
import unittest

from statistics import nonparametric as npm
from statistics.anova import InsufficientDataError
from statistics.cld import compact_letter_display, verify_invariants
from statistics.types import RawGroup


class TestChi2SF(unittest.TestCase):
    def test_critical_values(self):
        self.assertAlmostEqual(npm._chi2_sf(5.991465, 2), 0.05, places=4)
        self.assertAlmostEqual(npm._chi2_sf(7.814728, 3), 0.05, places=4)
        self.assertAlmostEqual(npm._chi2_sf(9.21034, 2), 0.01, places=4)
        self.assertAlmostEqual(npm._chi2_sf(0.0, 2), 1.0, places=6)


class TestKruskalWallis(unittest.TestCase):
    def test_reference_no_ties(self):
        # scipy.stats.kruskal reference: H=0.7714, p=0.6799
        g1 = [2.9, 3.0, 2.5, 2.6, 3.2]
        g2 = [3.8, 2.7, 4.0, 2.4]
        g3 = [2.8, 3.4, 3.7, 2.2, 2.0]
        r = npm.kruskal_wallis([RawGroup("A", g1), RawGroup("B", g2),
                                RawGroup("C", g3)])
        self.assertAlmostEqual(r.statistic, 0.7714, places=3)
        self.assertAlmostEqual(r.p, 0.6799, places=3)
        self.assertEqual(r.df, 2)
        self.assertAlmostEqual(r.tie_correction, 1.0, places=9)

    def test_separated_groups_significant(self):
        r = npm.kruskal_wallis([RawGroup("A", [1, 2, 3, 4, 5]),
                                RawGroup("B", [6, 7, 8, 9, 10]),
                                RawGroup("C", [11, 12, 13, 14, 15])])
        # mean ranks 3/8/13 -> H = 12/(15*16)*(sum R^2/n) - 3*16
        self.assertAlmostEqual(r.statistic, 12.5, places=6)
        self.assertLess(r.p, 0.01)

    def test_tie_correction_applied(self):
        a = [1, 1, 2, 3]; b = [1, 2, 2, 4]; c = [3, 4, 4, 5]
        r = npm.kruskal_wallis([RawGroup("A", a), RawGroup("B", b),
                                RawGroup("C", c)])
        self.assertLess(r.tie_correction, 1.0)   # ties present
        self.assertGreater(r.tie_correction, 0.0)

    def test_too_few_groups(self):
        with self.assertRaises(InsufficientDataError):
            npm.kruskal_wallis([RawGroup("A", [1, 2, 3])])


class TestDunn(unittest.TestCase):
    def setUp(self):
        self.groups = [RawGroup("A", [1, 2, 3, 4, 5]),
                       RawGroup("B", [6, 7, 8, 9, 10]),
                       RawGroup("C", [11, 12, 13, 14, 15])]

    def test_z_and_se_reference(self):
        r = npm.dunn_test(self.groups, adjust="none")
        ab = next(c for c in r.comparisons if {c.group1, c.group2} == {"A", "B"})
        expected_se = math.sqrt(15 * 16 / 12 * (1 / 5 + 1 / 5))
        self.assertAlmostEqual(ab.se, expected_se, places=9)
        self.assertAlmostEqual(abs(ab.statistic), 1.7678, places=3)

    def test_holm_adjustment(self):
        r = npm.dunn_test(self.groups, adjust="holm")
        ac = next(c for c in r.comparisons if {c.group1, c.group2} == {"A", "C"})
        # raw p(A,C) ~ 0.00041 -> Holm x3 ~ 0.00122
        self.assertAlmostEqual(ac.p_adjusted, 0.00122, places=4)
        self.assertTrue(ac.significant)

    def test_mean_ranks_recorded(self):
        r = npm.dunn_test(self.groups, adjust="none")
        # mean ranks A=3, B=8, C=13
        by = {(c.group1, c.group2): c for c in r.comparisons}
        ab = by[("A", "B")]
        self.assertAlmostEqual(ab.mean1, 3.0, places=9)
        self.assertAlmostEqual(ab.mean2, 8.0, places=9)


class TestDunnToCLD(unittest.TestCase):
    def test_cld_from_dunn_matrix(self):
        groups = [RawGroup("A", [1, 2, 3, 4, 5]),
                  RawGroup("B", [6, 7, 8, 9, 10]),
                  RawGroup("C", [11, 12, 13, 14, 15])]
        ph = npm.dunn_test(groups, adjust="holm")
        sig = ph.significance_matrix()
        cld = compact_letter_display(sig, order=["C", "B", "A"])
        self.assertEqual(verify_invariants(sig, cld), [])
        self.assertIn("Dunn", sig.source)


if __name__ == "__main__":
    unittest.main()
