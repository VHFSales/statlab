import math
import unittest

from statistics.factorial import two_way_anova_typed
from statistics.two_way_anova import two_way_anova
from statistics.anova import InsufficientDataError
from app.core.orchestrator import AnalysisOptions, analyze_two_way_typed


def flatten(cells):
    av, bv, yv = [], [], []
    for (a, b), vals in cells.items():
        for v in vals:
            av.append(a); bv.append(b); yv.append(v)
    return av, bv, yv


BAL = {("a1", "b1"): [1, 2, 3], ("a1", "b2"): [4, 5, 6],
       ("a2", "b1"): [7, 8, 9], ("a2", "b2"): [10, 11, 12]}

# Unbalanced 2x2
UNBAL_A = ["a1", "a1", "a1", "a2", "a2", "a1", "a1", "a2", "a2", "a2", "a2"]
UNBAL_B = ["b1", "b1", "b2", "b1", "b2", "b2", "b1", "b2", "b1", "b2", "b2"]
UNBAL_Y = [12, 14, 20, 8, 15, 22, 13, 16, 9, 17, 18.0]


class TestBalancedEqualsAllTypes(unittest.TestCase):
    def test_all_types_match_balanced_module(self):
        av, bv, yv = flatten(BAL)
        ref = {e.name: e.ss for e in two_way_anova(BAL).effects}
        for t in (1, 2, 3):
            r = two_way_anova_typed(av, bv, yv, ss_type=t)
            ss = {e.name: e.ss for e in r.effects}
            for name in ("a1" and "A", "B", "A:B", "Error"):
                pass
            self.assertAlmostEqual(ss["A"], ref["A"], places=6)
            self.assertAlmostEqual(ss["B"], ref["B"], places=6)
            self.assertAlmostEqual(ss["A:B"], ref["A:B"], places=6)
            self.assertAlmostEqual(ss["Error"], ref["Error"], places=6)


class TestUnbalancedTypesDiffer(unittest.TestCase):
    def test_error_is_type_invariant(self):
        errs = []
        for t in (1, 2, 3):
            r = two_way_anova_typed(UNBAL_A, UNBAL_B, UNBAL_Y, ss_type=t)
            errs.append(next(e.ss for e in r.effects if e.name == "Error"))
        for e in errs[1:]:
            self.assertAlmostEqual(e, errs[0], places=6)

    def test_type1_decomposition_identity(self):
        r = two_way_anova_typed(UNBAL_A, UNBAL_B, UNBAL_Y, ss_type=1)
        ss = {e.name: e.ss for e in r.effects}
        model = ss["A"] + ss["B"] + ss["A:B"]
        self.assertAlmostEqual(model, ss["Total"] - ss["Error"], places=6)

    def test_types_differ_for_main_effect(self):
        t1 = two_way_anova_typed(UNBAL_A, UNBAL_B, UNBAL_Y, ss_type=1)
        t2 = two_way_anova_typed(UNBAL_A, UNBAL_B, UNBAL_Y, ss_type=2)
        a1 = next(e.ss for e in t1.effects if e.name == "A")
        a2 = next(e.ss for e in t2.effects if e.name == "A")
        self.assertNotAlmostEqual(a1, a2, places=3)

    def test_method_label_unbalanced(self):
        r = two_way_anova_typed(UNBAL_A, UNBAL_B, UNBAL_Y, ss_type=3)
        self.assertIn("unbalanced", r.method)
        self.assertIn("Type 3", r.method)


class TestGuards(unittest.TestCase):
    def test_invalid_type(self):
        with self.assertRaises(ValueError):
            two_way_anova_typed(UNBAL_A, UNBAL_B, UNBAL_Y, ss_type=4)

    def test_empty_cell_refused(self):
        a = ["a1", "a1", "a2", "a2"]
        b = ["b1", "b1", "b1", "b1"]  # b2 never appears with any A -> single level
        with self.assertRaises(InsufficientDataError):
            two_way_anova_typed(a, b, [1, 2, 3, 4], ss_type=2)

    def test_insufficient_error_df(self):
        # 2x2 with exactly 1 obs per cell -> df_err = 0
        a = ["a1", "a1", "a2", "a2"]
        b = ["b1", "b2", "b1", "b2"]
        with self.assertRaises(InsufficientDataError):
            two_way_anova_typed(a, b, [1, 2, 3, 4], ss_type=2)


class TestOrchestration(unittest.TestCase):
    def test_end_to_end_unbalanced(self):
        res = analyze_two_way_typed(UNBAL_A, UNBAL_B, UNBAL_Y, ss_type=2,
                                    factor_a="Dose", factor_b="Mat",
                                    options=AnalysisOptions())
        self.assertFalse(res.refusals)
        self.assertEqual(len(res.effects), 5)
        self.assertTrue(any("desbalanceado" in w for w in res.warnings))
        self.assertTrue(res.interpretation["effects"])

    def test_refusal_propagates(self):
        res = analyze_two_way_typed(["a1", "a1"], ["b1", "b1"], [1, 2], ss_type=2,
                                    options=AnalysisOptions())
        self.assertTrue(res.refusals)


if __name__ == "__main__":
    unittest.main()
