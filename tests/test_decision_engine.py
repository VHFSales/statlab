import unittest

from statistics.decision_engine import DesignSpec, Diagnostics, recommend


class TestDecisionEngine(unittest.TestCase):
    def test_classical_to_tukey(self):
        r = recommend(DesignSpec(n_factors=1), Diagnostics(k_groups=4, balanced=True,
                      variance_ratio=1.2, brown_forsythe_p=0.6), omnibus_p=0.001)
        self.assertEqual(r.method, "one-way ANOVA")
        self.assertEqual(r.posthoc, "Tukey HSD")
        self.assertTrue(r.run_posthoc)

    def test_unequal_n_to_kramer(self):
        r = recommend(DesignSpec(n_factors=1),
                      Diagnostics(k_groups=3, n_per_group=[5, 3, 4],
                                  variance_ratio=1.1, brown_forsythe_p=0.5),
                      omnibus_p=0.01)
        self.assertEqual(r.method, "one-way ANOVA")
        self.assertEqual(r.posthoc, "Tukey-Kramer")

    def test_welch_to_games_howell(self):
        r = recommend(DesignSpec(n_factors=1),
                      Diagnostics(k_groups=3, variance_ratio=8.0,
                                  brown_forsythe_p=0.001), omnibus_p=0.001)
        self.assertEqual(r.method, "Welch's ANOVA")
        self.assertEqual(r.posthoc, "Games-Howell")

    def test_welch_does_not_select_tukey(self):
        r = recommend(DesignSpec(n_factors=1),
                      Diagnostics(k_groups=3, variance_ratio=10.0,
                                  brown_forsythe_p=0.0005), omnibus_p=0.001)
        self.assertNotIn("Tukey", str(r.posthoc))

    def test_two_groups_not_tukey(self):
        r = recommend(DesignSpec(n_factors=1),
                      Diagnostics(k_groups=2, variance_ratio=1.1,
                                  brown_forsythe_p=0.5))
        self.assertIn("t-test", r.method)
        self.assertIsNone(r.posthoc)
        self.assertFalse(r.run_posthoc)

    def test_two_groups_hetero_welch_t(self):
        r = recommend(DesignSpec(n_factors=1),
                      Diagnostics(k_groups=2, variance_ratio=9.0,
                                  brown_forsythe_p=0.001))
        self.assertEqual(r.method, "Welch's t-test")

    def test_two_factors_recommends_two_way(self):
        r = recommend(DesignSpec(n_factors=2), Diagnostics(k_groups=4))
        self.assertFalse(r.is_refused)
        self.assertEqual(r.method, "two-way ANOVA")

    def test_three_factors_refused(self):
        r = recommend(DesignSpec(n_factors=3), Diagnostics(k_groups=8))
        self.assertTrue(r.is_refused)
        self.assertIsNone(r.method)

    def test_repeated_measures_refused(self):
        r = recommend(DesignSpec(n_factors=1, repeated_measures=True),
                      Diagnostics(k_groups=3))
        self.assertTrue(r.is_refused)

    def test_paired_refused(self):
        r = recommend(DesignSpec(n_factors=1, paired=True), Diagnostics(k_groups=2))
        self.assertTrue(r.is_refused)

    def test_technical_replicates_warns(self):
        r = recommend(DesignSpec(n_factors=1, multiple_obs_per_unit=True,
                                 independent_units_asserted=False),
                      Diagnostics(k_groups=3, variance_ratio=1.2,
                                  brown_forsythe_p=0.5), omnibus_p=0.01)
        self.assertTrue(any("pseudorreplica" in w.lower() or "replicatas" in w.lower()
                            for w in r.warnings))

    def test_nonsignificant_omnibus_suppresses_posthoc(self):
        r = recommend(DesignSpec(n_factors=1),
                      Diagnostics(k_groups=3, variance_ratio=1.1,
                                  brown_forsythe_p=0.6), omnibus_p=0.20)
        self.assertFalse(r.run_posthoc)
        self.assertTrue(any("não apresentou signific" in w.lower() for w in r.warnings))


if __name__ == "__main__":
    unittest.main()
