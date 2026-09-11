import math
import unittest

from statistics import regression as reg
from statistics import correlation as corr
from statistics.anova import InsufficientDataError
from app.core.orchestrator import AnalysisOptions, analyze_regression


# Anscombe dataset I — known OLS fit: intercept 3.0, slope 0.5, R^2 0.6665.
ANS_X = [10, 8, 13, 9, 11, 14, 6, 4, 12, 7, 5]
ANS_Y = [8.04, 6.95, 7.58, 8.81, 8.33, 9.96, 7.24, 4.26, 10.84, 4.82, 5.68]


class TestSimpleRegression(unittest.TestCase):
    def setUp(self):
        self.r = reg.simple_linear_regression(ANS_X, ANS_Y)

    def test_coefficients(self):
        b0, b1 = self.r.coefficients
        self.assertAlmostEqual(b0.estimate, 3.0, places=2)
        self.assertAlmostEqual(b1.estimate, 0.5, places=3)

    def test_r_squared(self):
        self.assertAlmostEqual(self.r.r_squared, 0.6665, places=3)

    def test_r2_equals_pearson_r_squared(self):
        pr = corr.pearson(ANS_X, ANS_Y)
        self.assertAlmostEqual(self.r.r_squared, pr.r ** 2, places=9)

    def test_f_equals_slope_t_squared(self):
        b1 = self.r.coefficients[1]
        self.assertAlmostEqual(self.r.f_statistic, b1.t ** 2, places=6)

    def test_df(self):
        self.assertEqual(self.r.df_model, 1)
        self.assertEqual(self.r.df_resid, 9)

    def test_ci_contains_estimate(self):
        for c in self.r.coefficients:
            self.assertLessEqual(c.ci_low, c.estimate)
            self.assertGreaterEqual(c.ci_high, c.estimate)


class TestMultipleRegression(unittest.TestCase):
    def test_recovers_exact_coefficients(self):
        # y = 2 + 3 x1 - 1 x2 exactly
        x1 = [1, 2, 3, 4, 5, 6, 7, 8]
        x2 = [2, 1, 4, 3, 6, 5, 8, 7]
        y = [2 + 3 * a - 1 * b for a, b in zip(x1, x2)]
        r = reg.ols([x1, x2], y, ["x1", "x2"], "y")
        est = {c.name: c.estimate for c in r.coefficients}
        self.assertAlmostEqual(est["(Intercepto)"], 2.0, places=6)
        self.assertAlmostEqual(est["x1"], 3.0, places=6)
        self.assertAlmostEqual(est["x2"], -1.0, places=6)
        self.assertAlmostEqual(r.r_squared, 1.0, places=9)


class TestRegressionGuards(unittest.TestCase):
    def test_constant_predictor_refused(self):
        with self.assertRaises(InsufficientDataError):
            reg.ols([[1, 1, 1, 1, 1]], [2, 3, 4, 5, 6], ["c"], "y")

    def test_n_le_p_refused(self):
        with self.assertRaises(InsufficientDataError):
            reg.ols([[1, 2], [3, 4]], [5, 6], ["a", "b"], "y")

    def test_collinearity_refused(self):
        with self.assertRaises(InsufficientDataError):
            reg.ols([[1, 2, 3, 4, 5], [2, 4, 6, 8, 10]], [1, 2, 1, 2, 3],
                    ["a", "b"], "y")

    def test_missing_rows_dropped(self):
        r = reg.ols([[1, 2, None, 4, 5]], [2, 3, 9, 5, 6], ["x"], "y")
        self.assertEqual(r.n, 4)
        self.assertEqual(r.n_dropped, 1)


class TestRegressionOrchestration(unittest.TestCase):
    def test_end_to_end(self):
        res = analyze_regression([ANS_X], ANS_Y, ["x"], "y",
                                 options=AnalysisOptions())
        self.assertFalse(res.refusals)
        self.assertAlmostEqual(res.result["r_squared"], 0.6665, places=3)
        self.assertIn("causalidade", " ".join(res.warnings).lower())

    def test_refusal_propagates(self):
        res = analyze_regression([[1, 1, 1]], [1, 2, 3], ["c"], "y",
                                 options=AnalysisOptions())
        self.assertTrue(res.refusals)


if __name__ == "__main__":
    unittest.main()
