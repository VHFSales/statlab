import math
import unittest

from statistics import paired
from statistics.anova import InsufficientDataError
from app.core.orchestrator import AnalysisOptions, analyze_paired


BEFORE = [210, 180, 195, 220, 231, 199, 224, 240]
AFTER = [200, 170, 188, 215, 225, 190, 220, 232]


class TestPairedT(unittest.TestCase):
    def test_matches_hand_computation(self):
        r = paired.paired_t_test(BEFORE, AFTER)
        d = [b - a for b, a in zip(BEFORE, AFTER)]
        n = len(d)
        md = sum(d) / n
        sd = math.sqrt(sum((x - md) ** 2 for x in d) / (n - 1))
        t = md / (sd / math.sqrt(n))
        self.assertAlmostEqual(r.statistic, t, places=9)
        self.assertEqual(r.df, n - 1)
        self.assertAlmostEqual(r.mean_diff, md, places=9)
        self.assertAlmostEqual(r.cohens_dz, md / sd, places=9)
        self.assertTrue(r.significant)

    def test_ci_contains_mean_diff(self):
        r = paired.paired_t_test(BEFORE, AFTER)
        self.assertLessEqual(r.ci_low, r.mean_diff)
        self.assertGreaterEqual(r.ci_high, r.mean_diff)

    def test_mismatched_length_refused(self):
        with self.assertRaises(InsufficientDataError):
            paired.paired_t_test([1, 2, 3], [1, 2])

    def test_missing_pair_dropped(self):
        r = paired.paired_t_test([1, 2, None, 4], [0, 1, 3, 2])
        self.assertEqual(r.n_pairs, 3)  # the (None, 3) pair dropped

    def test_zero_variance_refused(self):
        with self.assertRaises(InsufficientDataError):
            paired.paired_t_test([5, 6, 7], [4, 5, 6])  # all diffs == 1


class TestWilcoxon(unittest.TestCase):
    def test_all_positive_differences(self):
        w = paired.wilcoxon_signed_rank(BEFORE, AFTER)
        self.assertEqual(w.w_minus, 0.0)      # all diffs positive
        self.assertGreater(w.w_plus, 0.0)
        self.assertEqual(w.w_statistic, 0.0)

    def test_mixed_signs_with_zero(self):
        # diffs = 0, -2, 1, -2, 2, 1 -> drop the zero
        x1 = [1, 2, 3, 4, 5, 6]
        x2 = [1, 4, 2, 6, 3, 5]
        w = paired.wilcoxon_signed_rank(x1, x2)
        self.assertEqual(w.n_zeros, 1)
        self.assertEqual(w.n_pairs, 5)
        self.assertAlmostEqual(w.w_plus, 7.0, places=9)
        self.assertAlmostEqual(w.w_minus, 8.0, places=9)

    def test_small_n_note(self):
        w = paired.wilcoxon_signed_rank([1, 2, 3], [0, 0, 0])
        self.assertTrue(w.note)


class TestPairedOrchestration(unittest.TestCase):
    def test_parametric_flow(self):
        res = analyze_paired(BEFORE, AFTER, "Antes", "Depois", AnalysisOptions())
        self.assertFalse(res.refusals)
        self.assertIsNotNone(res.parametric)
        self.assertIsNone(res.nonparametric)
        self.assertIsNotNone(res.descriptive_diff)
        self.assertIn("primary", res.interpretation)

    def test_nonparametric_flow(self):
        res = analyze_paired(BEFORE, AFTER, "Antes", "Depois",
                             AnalysisOptions(mode="advanced", nonparametric=True))
        self.assertIsNotNone(res.nonparametric)
        self.assertIsNone(res.parametric)
        self.assertTrue(any("não-paramétrico" in w.lower() for w in res.warnings))

    def test_dropped_pairs_reported(self):
        res = analyze_paired([1, 2, None, 4, 5], [0, 1, 3, 2, 4],
                             options=AnalysisOptions())
        self.assertEqual(res.n_dropped, 1)
        self.assertTrue(any("descartado" in w for w in res.warnings))


if __name__ == "__main__":
    unittest.main()
