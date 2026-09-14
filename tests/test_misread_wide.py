"""Regression tests for detecting a MISREAD wide table.

A tidy/long spreadsheet (one row per condition, with factor columns, repeated
measurement columns and derived Média/DP columns) must NOT be silently treated as
"one column per group". ``detect_misread_wide`` flags that so the UI can warn the
user instead of computing a meaningless ANOVA over heterogeneous columns.

Scenario from a real user report: columns
``Potência | Velocidade | Med1..Med5 | Média | DP`` were compared as 9 "groups".
"""

import unittest

from data.importer import detect_misread_wide


class TestDetectMisreadWide(unittest.TestCase):
    def test_flags_user_report_layout(self):
        header = ["Potência", "Velocidade", "Med1", "Med2", "Med3", "Med4",
                  "Med5", "Média", "DP"]
        prob = detect_misread_wide(header)
        self.assertIsNotNone(prob)
        self.assertIn("Potência", prob["factors"])
        self.assertIn("Velocidade", prob["factors"])
        self.assertEqual(len(prob["measures"]), 5)      # Med1..Med5
        self.assertIn("Média", prob["derived"])
        self.assertIn("DP", prob["derived"])

    def test_flags_factor_plus_derived_only(self):
        # a factor column + derived summaries (no measurement run) is still a misread
        self.assertIsNotNone(detect_misread_wide(["Tratamento", "Média", "DP", "n"]))

    def test_does_not_flag_legitimate_wide(self):
        # genuine "one column per group" tables must NOT be flagged
        self.assertIsNone(detect_misread_wide(["Controle", "600 W", "750 W", "900 W"]))
        self.assertIsNone(detect_misread_wide(["A", "B", "C"]))
        self.assertIsNone(detect_misread_wide(["Grupo 1", "Grupo 2", "Grupo 3"]))

    def test_does_not_flag_measurements_without_factor(self):
        # only measurement columns, no factor -> ambiguous, don't false-alarm
        self.assertIsNone(detect_misread_wide(["Med1", "Med2", "Med3", "Med4"]))

    def test_does_not_flag_two_column_longish(self):
        self.assertIsNone(detect_misread_wide(["Tratamento", "Valor"]))


if __name__ == "__main__":
    unittest.main()
