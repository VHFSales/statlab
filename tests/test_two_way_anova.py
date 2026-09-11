import math
import unittest

from statistics.two_way_anova import two_way_anova
from statistics.anova import InsufficientDataError
from app.core.orchestrator import AnalysisOptions, analyze_two_way


class TestTwoWayBalanced(unittest.TestCase):
    def setUp(self):
        # 2x2, n=3. Known SS: A=108, B=27, AB=0, error=8, total=143.
        self.cells = {
            ("a1", "b1"): [1, 2, 3], ("a1", "b2"): [4, 5, 6],
            ("a2", "b1"): [7, 8, 9], ("a2", "b2"): [10, 11, 12],
        }
        self.r = two_way_anova(self.cells, "A", "B")

    def test_sums_of_squares(self):
        ss = {e.name: e.ss for e in self.r.effects}
        self.assertAlmostEqual(ss["A"], 108.0, places=9)
        self.assertAlmostEqual(ss["B"], 27.0, places=9)
        self.assertAlmostEqual(ss["A:B"], 0.0, places=9)
        self.assertAlmostEqual(ss["Error"], 8.0, places=9)
        self.assertAlmostEqual(ss["Total"], 143.0, places=9)

    def test_ss_decomposition_identity(self):
        ss = {e.name: e.ss for e in self.r.effects}
        self.assertAlmostEqual(ss["A"] + ss["B"] + ss["A:B"] + ss["Error"],
                               ss["Total"], places=9)

    def test_df(self):
        df = {e.name: e.df for e in self.r.effects}
        self.assertEqual(df["A"], 1)
        self.assertEqual(df["B"], 1)
        self.assertEqual(df["A:B"], 1)
        self.assertEqual(df["Error"], 8)

    def test_f_values(self):
        by = {e.name: e for e in self.r.effects}
        self.assertAlmostEqual(by["A"].f, 108.0, places=6)   # MS_A/MS_err = 108/1
        self.assertAlmostEqual(by["B"].f, 27.0, places=6)

    def test_interaction_case(self):
        # crossover -> big interaction, small main effects
        cells = {
            ("a1", "b1"): [10, 12, 11], ("a1", "b2"): [20, 22, 21],
            ("a2", "b1"): [20, 21, 19], ("a2", "b2"): [10, 11, 9],
        }
        r = two_way_anova(cells)
        by = {e.name: e for e in r.effects}
        self.assertLess(by["A:B"].p, 0.001)
        self.assertGreater(by["A"].p, 0.05)


class TestTwoWayGuards(unittest.TestCase):
    def test_unbalanced_refused(self):
        with self.assertRaises(InsufficientDataError):
            two_way_anova({
                ("a1", "b1"): [1, 2, 3], ("a1", "b2"): [4, 5],
                ("a2", "b1"): [7, 8, 9], ("a2", "b2"): [10, 11, 12]})

    def test_missing_cell_refused(self):
        with self.assertRaises(InsufficientDataError):
            two_way_anova({
                ("a1", "b1"): [1, 2, 3], ("a2", "b1"): [7, 8, 9],
                ("a2", "b2"): [10, 11, 12]})

    def test_single_replicate_refused(self):
        with self.assertRaises(InsufficientDataError):
            two_way_anova({
                ("a1", "b1"): [1], ("a1", "b2"): [4],
                ("a2", "b1"): [7], ("a2", "b2"): [10]})


class TestTwoWayOrchestration(unittest.TestCase):
    def test_end_to_end(self):
        cells = {
            ("Baixa", "X"): [10, 12, 11], ("Baixa", "Y"): [20, 22, 21],
            ("Alta", "X"): [20, 21, 19], ("Alta", "Y"): [10, 11, 9],
        }
        res = analyze_two_way(cells, "Dose", "Material", AnalysisOptions())
        self.assertFalse(res.refusals)
        self.assertEqual(len(res.effects), 5)  # A, B, A:B, Error, Total
        self.assertTrue(res.interpretation["effects"])
        self.assertIn("interação", res.interpretation["note"].lower())
        self.assertEqual(len(res.cell_descriptive), 4)

    def test_unbalanced_refused_in_orchestrator(self):
        cells = {("a1", "b1"): [1, 2, 3], ("a1", "b2"): [4, 5],
                 ("a2", "b1"): [7, 8, 9], ("a2", "b2"): [10, 11, 12]}
        res = analyze_two_way(cells)
        self.assertTrue(res.refusals)


if __name__ == "__main__":
    unittest.main()
