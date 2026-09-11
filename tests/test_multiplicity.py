import unittest

from statistics import multiplicity as mp


class TestBonferroni(unittest.TestCase):
    def test_scaling_and_clamp(self):
        r = mp.bonferroni([0.01, 0.02, 0.5], alpha=0.05)
        self.assertAlmostEqual(r.p_adjusted[0], 0.03, places=12)
        self.assertAlmostEqual(r.p_adjusted[1], 0.06, places=12)
        self.assertAlmostEqual(r.p_adjusted[2], 1.0, places=12)  # clamped
        self.assertEqual(r.rejected, [True, False, False])


class TestHolm(unittest.TestCase):
    def test_known_values(self):
        # p = [0.01, 0.04, 0.03]; m=3
        # sorted: 0.01(*3=0.03), 0.03(*2=0.06), 0.04(*1=0.04 -> max w/ 0.06 = 0.06)
        r = mp.holm([0.01, 0.04, 0.03], alpha=0.05)
        # original order
        self.assertAlmostEqual(r.p_adjusted[0], 0.03, places=12)   # 0.01
        self.assertAlmostEqual(r.p_adjusted[1], 0.06, places=12)   # 0.04
        self.assertAlmostEqual(r.p_adjusted[2], 0.06, places=12)   # 0.03 (monotone)
        self.assertEqual(r.rejected, [True, False, False])

    def test_monotonicity(self):
        r = mp.holm([0.001, 0.002, 0.003, 0.9], alpha=0.05)
        # adjusted p must be non-decreasing in the sorted order
        pairs = sorted(zip(r.p_raw, r.p_adjusted))
        adj_sorted = [a for _, a in pairs]
        self.assertEqual(adj_sorted, sorted(adj_sorted))


class TestBenjaminiHochberg(unittest.TestCase):
    def test_known_values(self):
        # p = [0.01, 0.02, 0.03, 0.04, 0.05]; m=5
        # BH adj: p*m/rank -> [0.05, 0.05, 0.05, 0.05, 0.05] after monotone
        r = mp.benjamini_hochberg([0.01, 0.02, 0.03, 0.04, 0.05], alpha=0.05)
        for pa in r.p_adjusted:
            self.assertAlmostEqual(pa, 0.05, places=12)
        self.assertTrue(all(r.rejected))

    def test_less_conservative_than_bonferroni(self):
        p = [0.01, 0.02, 0.03, 0.04]
        bh = mp.benjamini_hochberg(p, 0.05)
        bonf = mp.bonferroni(p, 0.05)
        # BH adjusted <= Bonferroni adjusted elementwise
        for a, b in zip(bh.p_adjusted, bonf.p_adjusted):
            self.assertLessEqual(a, b + 1e-12)

    def test_dispatch(self):
        for name in ("holm", "bh", "fdr", "bonferroni"):
            r = mp.adjust([0.01, 0.2], method=name, alpha=0.05)
            self.assertEqual(len(r.p_adjusted), 2)
        with self.assertRaises(ValueError):
            mp.adjust([0.1], method="nope")


if __name__ == "__main__":
    unittest.main()
