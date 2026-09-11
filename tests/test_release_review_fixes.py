"""Regression tests for issues found in the v1.0 pre-release semantic review."""

import math
import unittest

from app.core.orchestrator import (AnalysisOptions, analyze_batch, analyze_raw,
                                   analyze_summary)
from statistics import descriptive
from statistics.decision_engine import DesignSpec


class TestTwoFactorGuardSummary(unittest.TestCase):
    """BLOCKER fix: analyze_summary must refuse a two-factor design, not run
    a silent one-way ANOVA (parity with analyze_raw)."""

    def test_summary_two_factors_refused(self):
        summ = {"A": {"mean": 10.0, "sd": 1.2, "n": 5},
                "B": {"mean": 14.0, "sd": 1.0, "n": 5},
                "C": {"mean": 12.0, "sd": 1.1, "n": 5}}
        res = analyze_summary(summ, DesignSpec(n_factors=2), AnalysisOptions())
        self.assertTrue(res.refusals)
        self.assertIsNone(res.omnibus)          # NOT a one-way table
        self.assertNotEqual(res.omnibus_kind, "anova")

    def test_raw_two_factors_still_refused(self):
        raw = {"A": [1, 2, 3], "B": [4, 5, 6]}
        res = analyze_raw(raw, DesignSpec(n_factors=2), AnalysisOptions())
        self.assertTrue(res.refusals)


class TestCVNonNegative(unittest.TestCase):
    def test_negative_mean_gives_nonnegative_cv(self):
        d = descriptive.describe_group("X", [-10, -12, -14, -16, -18])  # mean=-14
        self.assertFalse(math.isnan(d.cv))
        self.assertGreaterEqual(d.cv, 0.0)


class TestEmptyGroupDescriptive(unittest.TestCase):
    def test_empty_group_no_crash(self):
        # regression: n=0 DescriptiveRow was missing the cv field
        d = descriptive.describe_group("empty", [None, float("nan")])
        self.assertEqual(d.n, 0)
        self.assertEqual(d.n_missing, 2)
        self.assertTrue(math.isnan(d.cv))


class TestNonParametricGroupFilter(unittest.TestCase):
    def test_n1_group_included_in_rank_test(self):
        # A group with n=1 is valid for Kruskal-Wallis/Dunn (n>=1) but would be
        # dropped by the parametric n>=2 diagnostic filter. The non-parametric path
        # must include it (3 groups -> Kruskal-Wallis, not accidentally 2).
        raw = {"A": [1, 2, 3, 4], "B": [5, 6, 7, 8], "C": [10]}
        res = analyze_raw(raw, DesignSpec(n_factors=1),
                          AnalysisOptions(mode="advanced", nonparametric=True))
        # all three groups present -> Kruskal-Wallis (k=3), not Mann-Whitney (k=2)
        self.assertEqual(res.omnibus_kind, "kruskal")
        self.assertEqual(res.nonparametric_omnibus["k"], 3)


class TestBatchMultiplicityIncludesNonParametric(unittest.TestCase):
    def test_kruskal_pvalues_in_fdr_vector(self):
        variables = {
            "V1": {"A": [1, 2, 3], "B": [8, 9, 10], "C": [4, 5, 6]},
            "V2": {"A": [2, 3, 2], "B": [9, 8, 9], "C": [5, 5, 6]},
        }
        out = analyze_batch(variables, DesignSpec(n_factors=1),
                            AnalysisOptions(mode="advanced", nonparametric=True),
                            fdr_method="holm")
        # both variables produced a Kruskal-Wallis omnibus p -> both tested
        self.assertEqual(out["consolidated"]["n_tested"], 2)
        self.assertIsNotNone(out["consolidated"]["fdr"])


if __name__ == "__main__":
    unittest.main()
