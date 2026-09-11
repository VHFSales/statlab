import math
import unittest

from statistics import correlation as corr
from statistics.anova import InsufficientDataError
from app.core.orchestrator import AnalysisOptions, analyze_correlation


# Anscombe dataset I — a standard reference (r = 0.8164, p = 0.00217).
ANS_X = [10, 8, 13, 9, 11, 14, 6, 4, 12, 7, 5]
ANS_Y = [8.04, 6.95, 7.58, 8.81, 8.33, 9.96, 7.24, 4.26, 10.84, 4.82, 5.68]


class TestPearson(unittest.TestCase):
    def test_perfect_positive(self):
        r = corr.pearson([1, 2, 3, 4, 5], [2, 4, 6, 8, 10])
        self.assertAlmostEqual(r.r, 1.0, places=9)

    def test_perfect_negative(self):
        r = corr.pearson([1, 2, 3, 4, 5], [10, 8, 6, 4, 2])
        self.assertAlmostEqual(r.r, -1.0, places=9)

    def test_anscombe_reference(self):
        r = corr.pearson(ANS_X, ANS_Y)
        self.assertAlmostEqual(r.r, 0.81642, places=4)
        self.assertEqual(r.df, 9)
        self.assertAlmostEqual(r.p, 0.00217, places=4)
        # Fisher-z CI brackets r and excludes 0 here
        self.assertLess(r.ci_low, r.r)
        self.assertGreater(r.ci_high, r.r)
        self.assertGreater(r.ci_low, 0.0)

    def test_zero_variance_refused(self):
        with self.assertRaises(InsufficientDataError):
            corr.pearson([1, 1, 1], [2, 3, 4])

    def test_n_too_small_refused(self):
        with self.assertRaises(InsufficientDataError):
            corr.pearson([1, 2], [3, 4])

    def test_mismatched_length_refused(self):
        with self.assertRaises(InsufficientDataError):
            corr.pearson([1, 2, 3], [1, 2])


class TestSpearman(unittest.TestCase):
    def test_monotonic_nonlinear_is_one(self):
        # y = x^2 monotonic -> Spearman = 1, Pearson < 1
        sp = corr.spearman([1, 2, 3, 4, 5], [1, 4, 9, 16, 25])
        pe = corr.pearson([1, 2, 3, 4, 5], [1, 4, 9, 16, 25])
        self.assertAlmostEqual(sp.r, 1.0, places=9)
        self.assertLess(pe.r, 1.0)

    def test_ties(self):
        sp = corr.spearman([1, 2, 2, 3, 4], [2, 2, 3, 4, 5])
        self.assertTrue(-1.0 <= sp.r <= 1.0)
        self.assertTrue(sp.note)  # approximate-CI note


class TestCorrelationOrchestration(unittest.TestCase):
    def test_pearson_flow(self):
        res = analyze_correlation(ANS_X, ANS_Y, "peso", "altura", "pearson",
                                  AnalysisOptions())
        self.assertFalse(res.refusals)
        self.assertAlmostEqual(res.result["r"], 0.81642, places=4)
        self.assertIn("causalidade", res.interpretation["conclusion"].lower())

    def test_missing_dropped(self):
        res = analyze_correlation([1, 2, None, 4, 5], [2, 3, 3, 5, 6],
                                  method="pearson", options=AnalysisOptions())
        self.assertEqual(res.result["n"], 4)
        self.assertTrue(any("descartado" in w for w in res.warnings))

    def test_refusal_propagates(self):
        res = analyze_correlation([1, 1, 1], [2, 3, 4], options=AnalysisOptions())
        self.assertTrue(res.refusals)


if __name__ == "__main__":
    unittest.main()
