import math
import unittest

from statistics import repeated_measures as rm
from statistics.anova import InsufficientDataError
from statistics.cld import compact_letter_display, verify_invariants
from app.core.orchestrator import AnalysisOptions, analyze_repeated_measures


class TestFriedman(unittest.TestCase):
    def test_reference_Q(self):
        # consistent ranking A<B<C in every block -> R_A=4,R_B=8,R_C=12; Q=8
        blocks = [[1, 2, 3], [2, 3, 4], [1, 3, 5], [2, 4, 6]]
        r = rm.friedman(blocks, ["A", "B", "C"])
        self.assertAlmostEqual(r.statistic, 8.0, places=9)
        self.assertEqual(r.df, 2)
        self.assertAlmostEqual(r.tie_correction, 1.0, places=9)
        self.assertAlmostEqual(r.mean_ranks["A"], 1.0, places=9)
        self.assertAlmostEqual(r.mean_ranks["C"], 3.0, places=9)

    def test_significant_large_n(self):
        blocks = [[i, i + 2, i + 5] for i in range(1, 11)]
        r = rm.friedman(blocks, ["A", "B", "C"])
        self.assertLess(r.p, 0.001)

    def test_fewer_than_3_conditions_refused(self):
        with self.assertRaises(InsufficientDataError):
            rm.friedman([[1, 2], [3, 4]], ["A", "B"])

    def test_incomplete_block_refused(self):
        with self.assertRaises(InsufficientDataError):
            rm.friedman([[1, 2, 3], [4, 5]], ["A", "B", "C"])

    def test_missing_value_refused(self):
        with self.assertRaises(InsufficientDataError):
            rm.friedman([[1, 2, 3], [4, None, 6]], ["A", "B", "C"])

    def test_tie_correction_applied(self):
        blocks = [[1, 1, 2], [2, 2, 3], [1, 1, 3]]
        r = rm.friedman(blocks, ["A", "B", "C"])
        self.assertLess(r.tie_correction, 1.0)


class TestNemenyi(unittest.TestCase):
    def test_se_and_separation(self):
        blocks = [[i, i + 2, i + 5] for i in range(1, 11)]
        ph = rm.nemenyi_test(blocks, ["A", "B", "C"])
        expected_se = math.sqrt(3 * 4 / (6.0 * 10))
        self.assertAlmostEqual(ph.comparisons[0].se, expected_se, places=9)
        ac = next(c for c in ph.comparisons
                  if {c.group1, c.group2} == {"A", "C"})
        self.assertTrue(ac.significant)

    def test_feeds_cld(self):
        blocks = [[i, i + 2, i + 5] for i in range(1, 11)]
        ph = rm.nemenyi_test(blocks, ["A", "B", "C"])
        sig = ph.significance_matrix()
        cld = compact_letter_display(sig, order=["C", "B", "A"])
        self.assertEqual(verify_invariants(sig, cld), [])
        self.assertEqual(sig.source, "Nemenyi")


class TestRepeatedMeasuresOrchestration(unittest.TestCase):
    def test_end_to_end(self):
        blocks = [[i, i + 2, i + 5] for i in range(1, 11)]
        res = analyze_repeated_measures(blocks, ["A", "B", "C"], AnalysisOptions())
        self.assertFalse(res.refusals)
        self.assertIsNotNone(res.omnibus)
        self.assertIsNotNone(res.posthoc)
        self.assertIsNotNone(res.cld)
        self.assertIn("posto", res.interpretation["conclusion"].lower())

    def test_nonsignificant_suppresses_posthoc(self):
        # near-random -> Friedman not significant
        blocks = [[2, 1, 3], [1, 3, 2], [3, 2, 1], [2, 3, 1]]
        res = analyze_repeated_measures(blocks, ["A", "B", "C"], AnalysisOptions())
        if res.omnibus and res.omnibus["p"] >= 0.05:
            self.assertIsNone(res.posthoc)

    def test_refusal_propagates(self):
        res = analyze_repeated_measures([[1, 2], [3, 4]], ["A", "B"],
                                        AnalysisOptions())
        self.assertTrue(res.refusals)


if __name__ == "__main__":
    unittest.main()
