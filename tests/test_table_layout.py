import unittest

from data import table_layout as tl


# Reproduces the "Tabela 29" layout: 2 header rows, label column, mean±sd cells
# with grouping letters.
T29 = [
    ["Amostras", "Brilho antes", "Brilho antes", "Brilho antes"],
    ["", "20", "60", "85"],
    ["D2.A", "61,4 ±1,3b", "94,8 ±0,3a", "92,3 ±1,2a"],
    ["D3.A", "52,7 ±1,1c", "82,8 ±0,4c", "78,2 ±0,9c"],
    ["D4.A", "67,8 ±2,8a", "96,3 ±1,1a", "88,4 ±2,5b"],
    ["D5.A", "71,8 ±4,2a", "97,5 ±1,1a", "92,1 ±2,8a"],
]


class TestMeanSD(unittest.TestCase):
    def test_pm_with_letter(self):
        r = tl.parse_mean_sd("61,4 ±1,3b")
        self.assertAlmostEqual(r.mean, 61.4)
        self.assertAlmostEqual(r.sd, 1.3)
        self.assertEqual(r.letter, "b")

    def test_paren_sd(self):
        r = tl.parse_mean_sd("92,3 (1,4)")
        self.assertAlmostEqual(r.mean, 92.3)
        self.assertAlmostEqual(r.sd, 1.4)

    def test_two_numbers(self):
        r = tl.parse_mean_sd("50,1 4,0")
        self.assertAlmostEqual(r.mean, 50.1)
        self.assertAlmostEqual(r.sd, 4.0)

    def test_plain_number(self):
        r = tl.parse_mean_sd("61,4")
        self.assertAlmostEqual(r.mean, 61.4)
        self.assertIsNone(r.sd)

    def test_superscript_letter_mapped(self):
        r = tl.parse_mean_sd("94,6 \u00b11,6\u1d47")  # ᵇ
        self.assertEqual(r.letter, "b")

    def test_text_returns_none(self):
        self.assertIsNone(tl.parse_mean_sd("Classe A"))
        self.assertIsNone(tl.parse_mean_sd(""))

    def test_cell_looks_mean_sd(self):
        self.assertTrue(tl.cell_looks_mean_sd("61,4 ±1,3"))
        self.assertTrue(tl.cell_looks_mean_sd("92,3 (1,4)"))
        self.assertFalse(tl.cell_looks_mean_sd("61,4"))


class TestHeaders(unittest.TestCase):
    def test_detects_two_header_rows(self):
        self.assertEqual(tl.detect_header_rows(T29), 2)

    def test_single_header_row(self):
        rows = [["A", "B", "C"], ["10.2", "13.5", "12.1"], ["10.8", "14.0", "11.8"]]
        self.assertEqual(tl.detect_header_rows(rows), 1)

    def test_merge_spanning_titles(self):
        labels = tl.merge_header_rows(T29[:2])
        self.assertEqual(labels[1], "Brilho antes 20")
        self.assertEqual(labels[2], "Brilho antes 60")
        self.assertEqual(labels[3], "Brilho antes 85")

    def test_label_column_by_hint(self):
        self.assertEqual(tl.detect_label_column(T29, 2), 0)

    def test_label_column_fallback(self):
        rows = [["Especime", "V1", "V2"], ["a", "1", "2"], ["b", "3", "4"],
                ["c", "5", "6"]]
        self.assertEqual(tl.detect_label_column(rows, 1), 0)


class TestClassify(unittest.TestCase):
    def test_summary(self):
        self.assertEqual(tl.classify_table(T29), "summary")

    def test_raw(self):
        rows = [["A", "B", "C"], ["10.2", "13.5", "12.1"], ["10.8", "14.0", "11.8"],
                ["11.1", "13.8", "12.5"]]
        self.assertEqual(tl.classify_table(rows), "raw")

    def test_descriptive(self):
        rows = [["Classe", "Aplicacao", "Resistencia"],
                ["A", "servico externo", "alta"],
                ["B", "servico interno", "media"],
                ["C", "estrutural", "baixa"]]
        self.assertEqual(tl.classify_table(rows), "descriptive")


class TestInterpret(unittest.TestCase):
    def test_summary_sample_by_condition(self):
        it = tl.interpret_table(T29, default_n=5)
        self.assertEqual(it.kind, "summary")
        self.assertEqual(it.n_header_rows, 2)
        self.assertEqual(it.label_col, 0)
        self.assertIn("Brilho antes 20", it.summary_by_column)
        col = it.summary_by_column["Brilho antes 20"]
        self.assertEqual(col["D2.A"], {"mean": 61.4, "sd": 1.3, "n": 5})
        self.assertEqual(it.grouping_letters["Brilho antes 20"]["D4.A"], "a")

    def test_summary_without_n(self):
        it = tl.interpret_table(T29)
        col = it.summary_by_column["Brilho antes 20"]
        self.assertNotIn("n", col["D2.A"])
        self.assertTrue(any("tamanho amostral" in m.lower() for m in it.messages))

    def test_raw_wide(self):
        rows = [["A", "B", "C"], ["10.2", "13.5", "12.1"], ["10.8", "14.0", "11.8"],
                ["11.1", "13.8", "12.5"]]
        it = tl.interpret_table(rows)
        self.assertEqual(it.kind, "raw")
        self.assertEqual(it.raw["A"], [10.2, 10.8, 11.1])

    def test_descriptive_message(self):
        rows = [["Classe", "Aplicacao"], ["A", "externo"], ["B", "interno"],
                ["C", "estrutural"]]
        it = tl.interpret_table(rows)
        self.assertEqual(it.kind, "descriptive")
        self.assertTrue(it.messages)

    def test_reproduces_original_tukey_letters(self):
        # end-to-end: analysing "Brilho antes 20" with n=5 should match the
        # letters printed in the original table.
        from app.core.orchestrator import analyze_summary, AnalysisOptions
        from statistics.decision_engine import DesignSpec
        it = tl.interpret_table(T29, default_n=5)
        ds = it.summary_by_column["Brilho antes 20"]
        r = analyze_summary(ds, DesignSpec(n_factors=1), AnalysisOptions())
        self.assertFalse(r.refusals)
        # StatLab CLD should agree with the original letters for this column
        self.assertEqual(r.cld["display"], it.grouping_letters["Brilho antes 20"])


if __name__ == "__main__":
    unittest.main()
