"""Regression tests from the full-program robustness audit.

Each test pins a bug found during the audit so it cannot silently return:
  - summary group missing SD -> clean refusal (not KeyError);
  - degenerate zero-variance data -> clean refusal (not an unhandled exception);
  - canonical t_ppf: correct, symmetric, and not truncated in extreme tails.
"""

import math
import unittest

from app.core.orchestrator import analyze_raw, analyze_summary, AnalysisOptions
from statistics.decision_engine import DesignSpec
from statistics.distributions import t_ppf
from data.validator import validate_summary, has_errors


class TestSummaryMissingSD(unittest.TestCase):
    """A summary table without SD (e.g. the thesis energy table) must refuse
    cleanly instead of crashing with KeyError('sd')."""

    def test_validate_flags_missing_sd(self):
        issues = validate_summary({"A": {"mean": 9.6, "n": 5},
                                   "B": {"mean": 15.6, "n": 5}})
        self.assertTrue(has_errors(issues))
        self.assertTrue(any(i.code == "NO_SD" for i in issues))

    def test_analyze_summary_refuses_without_crash(self):
        r = analyze_summary({"A": {"mean": 9.6, "n": 5},
                             "B": {"mean": 15.6, "n": 5},
                             "C": {"mean": 11.1, "n": 5}},
                            DesignSpec(n_factors=1), AnalysisOptions())
        self.assertTrue(r.refusals)
        self.assertIsNone(r.omnibus)

    def test_valid_summary_still_runs(self):
        r = analyze_summary({"A": {"mean": 61.4, "sd": 1.3, "n": 5},
                             "B": {"mean": 52.7, "sd": 1.1, "n": 5},
                             "C": {"mean": 67.8, "sd": 2.8, "n": 5}},
                            DesignSpec(n_factors=1), AnalysisOptions())
        self.assertFalse(r.refusals)
        self.assertIsNotNone(r.omnibus)


class TestZeroVarianceRefusesCleanly(unittest.TestCase):
    """All-identical observations make F/t undefined; refuse, do not crash."""

    def test_two_identical_groups(self):
        r = analyze_raw({"A": [5, 5, 5], "B": [5, 5, 5]},
                        DesignSpec(n_factors=1), AnalysisOptions())
        self.assertTrue(r.refusals)

    def test_three_identical_groups(self):
        r = analyze_raw({"A": [5, 5, 5], "B": [5, 5, 5], "C": [5, 5, 5]},
                        DesignSpec(n_factors=1), AnalysisOptions())
        self.assertTrue(r.refusals)

    def test_normal_data_still_runs(self):
        r = analyze_raw({"A": [1, 2, 3, 4], "B": [5, 6, 7, 8]},
                        DesignSpec(n_factors=1), AnalysisOptions())
        self.assertFalse(r.refusals)


class TestCanonicalTPpf(unittest.TestCase):
    """The consolidated t quantile must be accurate, symmetric, and never
    silently truncated in extreme tails (old fixed [-1e4, 1e4] bracket bug)."""

    def test_known_values(self):
        for df, p, ref in [(1, 0.975, 12.7062), (5, 0.975, 2.5706),
                           (30, 0.975, 2.0423), (1000, 0.975, 1.9623),
                           (2, 0.995, 9.9248)]:
            self.assertAlmostEqual(t_ppf(p, df), ref, places=3)

    def test_symmetry(self):
        for df in (1, 5, 30):
            self.assertAlmostEqual(t_ppf(0.025, df), -t_ppf(0.975, df), places=6)

    def test_extreme_tail_not_truncated(self):
        # df=1: t_ppf(p) = tan(pi*(p-0.5)); at p=0.9999999 this is ~3.18e6,
        # which the old ±1e4 bracket truncated to 1e4.
        v = t_ppf(0.9999999, 1)
        self.assertGreater(v, 1e5)
        self.assertAlmostEqual(v, math.tan(math.pi * (0.9999999 - 0.5)), delta=1.0)

    def test_boundaries(self):
        self.assertEqual(t_ppf(0.5, 5), 0.0)
        self.assertTrue(math.isnan(t_ppf(0.9, 0)))
        self.assertEqual(t_ppf(0.0, 5), float("-inf"))
        self.assertEqual(t_ppf(1.0, 5), float("inf"))

    def test_delegates_match_canonical(self):
        # the per-module copies must now agree with the canonical implementation
        from statistics.descriptive import t_ppf as d_ppf
        from statistics.ttest import _t_ppf as tt_ppf
        from statistics.paired import _t_ppf as p_ppf
        from statistics.regression import _t_ppf as r_ppf
        from statistics.outliers import _t_ppf as o_ppf
        for df in (3, 10, 50):
            ref = t_ppf(0.975, df)
            for f in (d_ppf, tt_ppf, p_ppf, r_ppf, o_ppf):
                self.assertAlmostEqual(f(0.975, df), ref, places=9)


if __name__ == "__main__":
    unittest.main()
