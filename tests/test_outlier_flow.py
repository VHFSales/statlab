import unittest

from app.core.orchestrator import AnalysisOptions
from app.core.outlier_flow import (apply_exclusions, compare_with_exclusions,
                                   diagnose_outliers)
from statistics.decision_engine import DesignSpec


class TestDiagnose(unittest.TestCase):
    def test_iqr_flags_extreme(self):
        raw = {"A": [10, 11, 12, 13, 100], "B": [9, 10, 11, 12, 13]}
        flagged = diagnose_outliers(raw, method="iqr")
        vals_a = [f["value"] for f in flagged["A"]]
        self.assertIn(100, vals_a)
        self.assertEqual(flagged["B"], [])

    def test_grubbs_flags_single(self):
        raw = {"A": [10, 11, 12, 13, 100]}
        flagged = diagnose_outliers(raw, method="grubbs", alpha=0.05)
        self.assertTrue(flagged["A"])
        self.assertEqual(flagged["A"][0]["value"], 100)

    def test_never_auto_excludes(self):
        # diagnose returns candidates only; the data is untouched
        raw = {"A": [1, 2, 3, 4, 50], "B": [1, 2, 3, 4, 5]}
        diagnose_outliers(raw, method="iqr")
        self.assertEqual(raw["A"], [1, 2, 3, 4, 50])


class TestApplyExclusions(unittest.TestCase):
    def test_removes_and_logs(self):
        raw = {"A": [1, 2, 3, 100], "B": [4, 5, 6]}
        new_raw, log = apply_exclusions(
            raw, [{"group": "A", "value": 100}], reason="erro de digitação",
            method="IQR")
        self.assertEqual(new_raw["A"], [1, 2, 3])
        self.assertEqual(raw["A"], [1, 2, 3, 100])  # original untouched
        self.assertEqual(len(log), 1)
        self.assertEqual(log[0].group, "A")
        self.assertEqual(log[0].value, 100.0)
        self.assertEqual(log[0].reason, "erro de digitação")
        self.assertTrue(log[0].timestamp)

    def test_removes_one_of_duplicates(self):
        raw = {"A": [5, 5, 5, 1]}
        new_raw, log = apply_exclusions(raw, [{"group": "A", "value": 5}],
                                        reason="r", method="manual")
        self.assertEqual(new_raw["A"].count(5), 2)  # only one removed
        self.assertEqual(len(log), 1)


class TestComparison(unittest.TestCase):
    def test_compare_before_after(self):
        raw = {"A": [10, 11, 12, 13, 14], "B": [20, 21, 22, 23, 24],
               "C": [30, 31, 32, 33, 90]}
        comp = compare_with_exclusions(
            raw, DesignSpec(n_factors=1),
            targets=[{"group": "C", "value": 90}], reason="anomalia instrumental",
            method="IQR", options=AnalysisOptions())
        self.assertIn("omnibus_kind", comp.original)
        self.assertIn("omnibus_kind", comp.after_exclusion)
        self.assertEqual(len(comp.exclusions), 1)
        # after-result carries a registered-exclusion warning
        self.assertTrue(any("excluída" in w for w in
                            comp.after_exclusion["warnings"]))


if __name__ == "__main__":
    unittest.main()
