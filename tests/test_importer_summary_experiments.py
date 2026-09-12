import unittest

from data import importer as imp


class TestSummaryFromRows(unittest.TestCase):
    def test_named_columns_comma_decimal(self):
        rows = imp.parse_delimited_text(
            "Grupo;Media;DP;n\nA;10,5;1,2;5\nB;13,7;0,8;5\nC;15,2;1,0;6")
        summ, dec = imp.rows_to_summary(rows)
        self.assertEqual(dec, "comma")
        self.assertEqual(summ["A"], {"mean": 10.5, "sd": 1.2, "n": 5})
        self.assertEqual(summ["C"], {"mean": 15.2, "sd": 1.0, "n": 6})

    def test_positional_columns(self):
        rows = imp.parse_delimited_text("A,10.54,1.21,5\nB,13.72,0.84,5")
        summ, _ = imp.rows_to_summary(rows)
        self.assertAlmostEqual(summ["A"]["mean"], 10.54)
        self.assertAlmostEqual(summ["A"]["sd"], 1.21)
        self.assertEqual(summ["A"]["n"], 5)

    def test_header_variations(self):
        rows = imp.parse_delimited_text(
            "Tratamento,Média,Desvio,Tamanho\nX,5.0,0.5,4\nY,7.0,0.6,4")
        summ, _ = imp.rows_to_summary(rows)
        self.assertIn("X", summ)
        self.assertEqual(summ["Y"]["n"], 4)

    def test_missing_n_absent_key(self):
        rows = imp.parse_delimited_text("Grupo;Media;DP\nA;10,5;1,2\nB;13,7;0,8")
        summ, _ = imp.rows_to_summary(rows)
        self.assertNotIn("n", summ["A"])
        self.assertIn("mean", summ["A"])

    def test_import_summary_file_csv(self):
        data = "Grupo,Media,DP,n\nA,10.5,1.2,5\nB,13.7,0.8,5".encode("utf-8")
        summ, dec, rows = imp.import_summary_file(data, "s.csv")
        self.assertEqual(summ["B"], {"mean": 13.7, "sd": 0.8, "n": 5})


class TestExperimentDetection(unittest.TestCase):
    def test_detects_experiment_column(self):
        rows = imp.parse_delimited_text(
            "Experimento;Grupo;Valor\nE1;A;10,2\nE1;B;13,5\nE2;A;5,1\nE2;B;8,0")
        idx = imp.detect_experiment_column(rows)
        self.assertEqual(idx, 0)

    def test_no_experiment_column_when_single_value(self):
        rows = imp.parse_delimited_text(
            "Experimento;Grupo;Valor\nE1;A;10,2\nE1;B;13,5")
        self.assertIsNone(imp.detect_experiment_column(rows))

    def test_no_experiment_column_when_absent(self):
        rows = imp.parse_delimited_text("Grupo;Valor\nA;10,2\nB;13,5")
        self.assertIsNone(imp.detect_experiment_column(rows))

    def test_split_by_experiment_removes_column(self):
        rows = imp.parse_delimited_text(
            "Experimento;Grupo;Valor\nE1;A;10,2\nE1;A;10,8\nE2;A;5,1\nE2;B;8,0")
        idx = imp.detect_experiment_column(rows)
        parts = imp.split_by_experiment(rows, idx)
        self.assertEqual(list(parts.keys()), ["E1", "E2"])
        self.assertEqual(parts["E1"][0], ["Grupo", "Valor"])  # exp col removed


class TestImportFileMulti(unittest.TestCase):
    def test_multi_raw(self):
        csv = ("Experimento;Grupo;Valor\nE1;A;10,2\nE1;A;10,8\nE1;B;13,5\n"
               "E2;A;5,1\nE2;A;5,4\nE2;B;8,0").encode("utf-8")
        res = imp.import_file_multi(csv, "d.csv", kind="raw")
        self.assertTrue(res["multi"])
        self.assertEqual(set(res["experiments"].keys()), {"E1", "E2"})
        self.assertEqual(res["experiments"]["E1"]["A"], [10.2, 10.8])
        self.assertEqual(res["experiments"]["E2"]["B"], [8.0])

    def test_multi_summary(self):
        csv = ("Experimento;Grupo;Media;DP;n\nBrilho20;A;10,5;1,2;5\n"
               "Brilho20;B;13,7;0,8;5\nBrilho60;A;90,1;2,3;5\n"
               "Brilho60;B;94,6;1,6;5").encode("utf-8")
        res = imp.import_file_multi(csv, "d.csv", kind="summary")
        self.assertTrue(res["multi"])
        self.assertEqual(res["experiments"]["Brilho20"]["A"],
                         {"mean": 10.5, "sd": 1.2, "n": 5})
        self.assertEqual(res["experiments"]["Brilho60"]["B"]["mean"], 94.6)

    def test_single_experiment_keyed_unique(self):
        csv = "Grupo;Media;DP;n\nA;10,5;1,2;5\nB;13,7;0,8;5".encode("utf-8")
        res = imp.import_file_multi(csv, "d.csv", kind="summary")
        self.assertFalse(res["multi"])
        self.assertIn("(único)", res["experiments"])

    def test_end_to_end_each_experiment_analysed(self):
        from app.core.orchestrator import analyze_summary, AnalysisOptions
        from statistics.decision_engine import DesignSpec
        csv = ("Experimento;Grupo;Media;DP;n\nE1;A;10,5;1,2;5\nE1;B;13,7;0,8;5\n"
               "E1;C;16,0;1,1;5\nE2;A;90,1;2,3;5\nE2;B;94,6;1,6;5\n"
               "E2;C;80,2;2,0;5").encode("utf-8")
        res = imp.import_file_multi(csv, "d.csv", kind="summary")
        for name, ds in res["experiments"].items():
            r = analyze_summary(ds, DesignSpec(n_factors=1), AnalysisOptions())
            self.assertFalse(r.refusals, msg=f"{name}: {r.refusals}")
            self.assertEqual(r.omnibus_kind, "anova")


if __name__ == "__main__":
    unittest.main()
