import unittest

from app.core.orchestrator import AnalysisOptions, analyze_raw
from statistics.decision_engine import DesignSpec


class TestOrchestratorEndToEnd(unittest.TestCase):
    def test_classical_flow_produces_everything(self):
        raw = {
            "A": [6, 8, 4, 5, 3, 4],
            "B": [8, 12, 9, 11, 6, 8],
            "C": [13, 9, 11, 8, 7, 12],
        }
        res = analyze_raw(raw, DesignSpec(n_factors=1), AnalysisOptions())
        self.assertFalse(res.refusals, msg=res.refusals)
        self.assertEqual(res.omnibus_kind, "anova")
        self.assertIsNotNone(res.effect_sizes)
        self.assertIsNotNone(res.posthoc)
        self.assertIsNotNone(res.cld)
        # every group has a letter
        self.assertEqual(set(res.cld["display"].keys()), {"A", "B", "C"})
        # audit fields present
        self.assertTrue(res.analysis_id)
        self.assertTrue(res.data_hash)
        self.assertIn("omnibus", res.interpretation)

    def test_heteroscedastic_flow_uses_welch_games_howell(self):
        raw = {
            "A": [27, 26, 21, 24, 15, 18, 25, 23],
            "B": [19, 18, 20, 21, 22, 17],
            "C": [40, 38, 42, 39, 41, 44, 43],
        }
        res = analyze_raw(raw, DesignSpec(n_factors=1), AnalysisOptions())
        self.assertEqual(res.omnibus_kind, "welch")
        self.assertEqual(res.posthoc["method"], "Games-Howell")

    def test_multiple_factors_refused(self):
        raw = {"A": [1, 2, 3], "B": [4, 5, 6]}
        res = analyze_raw(raw, DesignSpec(n_factors=2), AnalysisOptions())
        self.assertTrue(res.refusals)
        self.assertIsNone(res.omnibus)

    def test_data_error_refused(self):
        raw = {"A": [1, 2, "oops"], "B": [4, 5, 6]}
        res = analyze_raw(raw, DesignSpec(n_factors=1), AnalysisOptions())
        self.assertTrue(res.refusals)

    def test_data_hash_changes_with_data(self):
        d1 = analyze_raw({"A": [1, 2, 3], "B": [4, 5, 6]}, DesignSpec(),
                         AnalysisOptions())
        d2 = analyze_raw({"A": [1, 2, 4], "B": [4, 5, 6]}, DesignSpec(),
                         AnalysisOptions())
        self.assertNotEqual(d1.data_hash, d2.data_hash)


class TestNonParametricFlow(unittest.TestCase):
    RAW = {"A": [1, 2, 3, 4, 5], "B": [6, 7, 8, 9, 10],
           "C": [11, 12, 13, 14, 15]}

    def test_optin_kruskal_dunn(self):
        res = analyze_raw(self.RAW, DesignSpec(n_factors=1),
                          AnalysisOptions(mode="advanced", nonparametric=True,
                                          dunn_adjust="holm"))
        self.assertEqual(res.omnibus_kind, "kruskal")
        self.assertIsNotNone(res.nonparametric_omnibus)
        self.assertIn("Dunn", res.posthoc["method"])
        self.assertIsNotNone(res.cld)
        # explicit-choice warning recorded (guardrail: not auto by normality)
        self.assertTrue(any("não-paramétrico" in w.lower() or
                            "nao-parametrico" in w.lower() for w in res.warnings))

    def test_not_used_by_default(self):
        # default options do NOT trigger the non-parametric path
        res = analyze_raw(self.RAW, DesignSpec(n_factors=1), AnalysisOptions())
        self.assertNotEqual(res.omnibus_kind, "kruskal")
        self.assertIsNone(res.nonparametric_omnibus)

    def test_conclusion_is_rank_based(self):
        res = analyze_raw(self.RAW, DesignSpec(n_factors=1),
                          AnalysisOptions(mode="advanced", nonparametric=True))
        # rank wording, not "médias"
        self.assertIn("posto", res.interpretation["conclusion"].lower())

    def test_two_groups_nonparametric_uses_mann_whitney(self):
        res = analyze_raw({"A": [1, 2, 3, 4, 5], "B": [6, 7, 8, 9, 10]},
                          DesignSpec(n_factors=1),
                          AnalysisOptions(mode="advanced", nonparametric=True))
        self.assertEqual(res.omnibus_kind, "mann_whitney")
        self.assertIsNotNone(res.mann_whitney)
        self.assertIsNone(res.nonparametric_omnibus)  # not Kruskal for 2 groups


if __name__ == "__main__":
    unittest.main()
