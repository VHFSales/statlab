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


if __name__ == "__main__":
    unittest.main()
