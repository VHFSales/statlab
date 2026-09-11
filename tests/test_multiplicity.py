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
        for name in ("holm", "bh", "fdr", "bonferroni", "sidak", "holm-sidak",
                     "hochberg"):
            r = mp.adjust([0.01, 0.2], method=name, alpha=0.05)
            self.assertEqual(len(r.p_adjusted), 2)
        with self.assertRaises(ValueError):
            mp.adjust([0.1], method="nope")


class TestSidak(unittest.TestCase):
    def test_formula(self):
        r = mp.sidak([0.01, 0.05, 0.5], alpha=0.05)
        # 1-(1-p)^m with m=3
        self.assertAlmostEqual(r.p_adjusted[0], 1 - (1 - 0.01) ** 3, places=12)
        self.assertAlmostEqual(r.p_adjusted[1], 1 - (1 - 0.05) ** 3, places=12)
        self.assertAlmostEqual(r.p_adjusted[2], 1 - (1 - 0.5) ** 3, places=12)

    def test_less_conservative_than_bonferroni(self):
        p = [0.01, 0.02, 0.03, 0.2]
        s = mp.sidak(p, 0.05)
        b = mp.bonferroni(p, 0.05)
        for a, c in zip(s.p_adjusted, b.p_adjusted):
            self.assertLessEqual(a, c + 1e-12)


class TestHolmSidak(unittest.TestCase):
    def test_monotone_and_at_least_as_powerful_as_holm(self):
        p = [0.01, 0.04, 0.03]
        hs = mp.holm_sidak(p, 0.05)
        h = mp.holm(p, 0.05)
        # Holm-Sidak adjusted p <= Holm adjusted p elementwise (more powerful)
        for a, b in zip(hs.p_adjusted, h.p_adjusted):
            self.assertLessEqual(a, b + 1e-12)
        # monotone in sorted order
        pairs = sorted(zip(hs.p_raw, hs.p_adjusted))
        adj = [a for _, a in pairs]
        self.assertEqual(adj, sorted(adj))


class TestHochberg(unittest.TestCase):
    def test_at_least_as_powerful_as_holm(self):
        p = [0.005, 0.02, 0.03, 0.045]
        hoch = mp.hochberg(p, 0.05)
        holm = mp.holm(p, 0.05)
        for a, b in zip(hoch.p_adjusted, holm.p_adjusted):
            self.assertLessEqual(a, b + 1e-12)

    def test_known_values(self):
        # p=[0.01,0.04,0.03], m=3; step-up: sorted 0.01,0.03,0.04
        # largest: 1*0.04=0.04; next: min(0.04, 2*0.03=0.06)=0.04; next: min(0.04,3*0.01=0.03)=0.03
        r = mp.hochberg([0.01, 0.04, 0.03], 0.05)
        self.assertAlmostEqual(r.p_adjusted[0], 0.03, places=12)  # 0.01
        self.assertAlmostEqual(r.p_adjusted[1], 0.04, places=12)  # 0.04
        self.assertAlmostEqual(r.p_adjusted[2], 0.04, places=12)  # 0.03


if __name__ == "__main__":
    unittest.main()
