import unittest

from app.core.orchestrator import (AnalysisOptions, analyze_batch, analyze_raw,
                                   analyze_summary)
from statistics import anova, descriptive
from statistics.decision_engine import DesignSpec
from statistics.types import RawGroup, SummaryGroup


ANOVA3 = {"A": [6, 8, 4, 5, 3, 4], "B": [8, 12, 9, 11, 6, 8],
          "C": [13, 9, 11, 8, 7, 12]}


class TestSummaryFlow(unittest.TestCase):
    def test_summary_equals_raw(self):
        # build summaries from raw and check omnibus F matches raw analysis
        summ = {}
        for lab, vals in ANOVA3.items():
            d = descriptive.describe_group(lab, vals)
            summ[lab] = {"mean": d.mean, "sd": d.sd, "n": d.n}
        res_s = analyze_summary(summ, DesignSpec(n_factors=1), AnalysisOptions())
        res_r = analyze_raw(ANOVA3, DesignSpec(n_factors=1), AnalysisOptions())
        self.assertTrue(res_s.summary_based)
        self.assertEqual(res_s.omnibus_kind, res_r.omnibus_kind)
        self.assertAlmostEqual(res_s.omnibus["f"], res_r.omnibus["f"], places=6)
        # CLD present and consistent letters count
        self.assertIsNotNone(res_s.cld)

    def test_summary_flags_limitations(self):
        summ = {"A": {"mean": 10.0, "sd": 1.2, "n": 5},
                "B": {"mean": 14.0, "sd": 1.0, "n": 5}}
        res = analyze_summary(summ, DesignSpec(n_factors=1), AnalysisOptions())
        self.assertTrue(any("estatísticas resumidas" in w for w in res.warnings))

    def test_summary_refuses_without_n(self):
        summ = {"A": {"mean": 10.0, "sd": 1.2}, "B": {"mean": 14.0, "sd": 1.0}}
        res = analyze_summary(summ, DesignSpec(n_factors=1), AnalysisOptions())
        self.assertTrue(res.refusals)


class TestTwoGroupTTest(unittest.TestCase):
    def test_homoscedastic_two_groups_student_t(self):
        raw = {"A": [10.2, 10.8, 11.1, 10.6, 10.4],
               "B": [10.5, 10.9, 10.7, 11.0, 10.6]}
        res = analyze_raw(raw, DesignSpec(n_factors=1), AnalysisOptions())
        self.assertIsNotNone(res.ttest)
        self.assertEqual(res.ttest["method"], "Student's t-test")
        self.assertIsNone(res.posthoc)   # no Tukey for 2 groups

    def test_heteroscedastic_two_groups_welch_t(self):
        raw = {"A": [1, 2, 3, 4, 5, 6, 7, 8],
               "B": [100, 140, 90, 130, 110]}
        res = analyze_raw(raw, DesignSpec(n_factors=1), AnalysisOptions())
        self.assertIsNotNone(res.ttest)
        self.assertEqual(res.ttest["method"], "Welch's t-test")


class TestBatch(unittest.TestCase):
    def test_batch_warns_multiplicity_and_fdr(self):
        variables = {
            "Var1": {"A": [1, 2, 3], "B": [8, 9, 10]},
            "Var2": {"A": [5, 5, 6], "B": [5, 6, 5]},
            "Var3": {"A": [2, 3, 2], "B": [9, 8, 9]},
        }
        out = analyze_batch(variables, DesignSpec(n_factors=1), AnalysisOptions(),
                            fdr_method="bh")
        self.assertEqual(out["consolidated"]["n_variables"], 3)
        self.assertTrue(out["consolidated"]["warnings"])
        self.assertIsNotNone(out["consolidated"]["fdr"])
        self.assertEqual(len(out["consolidated"]["fdr"]["p_adjusted"]),
                         out["consolidated"]["n_tested"])


if __name__ == "__main__":
    unittest.main()
