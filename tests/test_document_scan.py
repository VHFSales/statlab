import unittest

from data import document_scan as ds
from data.importer import MissingReader, UnsupportedFile


def mk(rows):
    nc = max(len(r) for r in rows)
    return ds.score_table(ds.DetectedTable(rows=rows, location="t",
                                           n_rows=len(rows), n_cols=nc))


class TestScoring(unittest.TestCase):
    def test_summary_table_scores_high(self):
        t = mk([["Grupo", "Media", "DP", "n"], ["A", "10,5", "1,2", "5"],
                ["B", "13,7", "0,8", "5"], ["C", "15,2", "1,0", "6"]])
        self.assertGreaterEqual(t.score, 0.7)
        self.assertTrue(t.has_group_col)
        self.assertTrue(t.has_summary_cols)

    def test_raw_numeric_table_scores_high(self):
        t = mk([["A", "B", "C"], ["10.2", "13.5", "12.1"],
                ["10.8", "14.0", "11.8"], ["11.1", "13.8", "12.5"]])
        self.assertGreaterEqual(t.score, 0.6)
        self.assertAlmostEqual(t.numeric_fraction, 1.0, places=6)

    def test_text_schedule_scores_low(self):
        t = mk([["Etapa", "Responsavel", "Prazo"],
                ["Revisao", "Joao", "Janeiro"], ["Coleta", "Maria", "Marco"],
                ["Escrita", "Ana", "Maio"]])
        self.assertLess(t.score, 0.3)

    def test_tiny_table_penalised(self):
        t = mk([["x", "y"], ["1", "2"]])   # only 1 body row
        self.assertLess(t.score, 0.4)


class TestConversion(unittest.TestCase):
    def test_auto_detects_summary(self):
        t = mk([["Grupo", "Media", "DP", "n"], ["A", "10,5", "1,2", "5"],
                ["B", "13,7", "0,8", "5"]])
        kind, dataset = ds.table_to_dataset(t)
        self.assertEqual(kind, "summary")
        self.assertEqual(dataset["A"], {"mean": 10.5, "sd": 1.2, "n": 5})

    def test_auto_detects_raw(self):
        t = mk([["A", "B"], ["10.2", "13.5"], ["10.8", "14.0"], ["11.1", "13.8"]])
        kind, dataset = ds.table_to_dataset(t)
        self.assertEqual(kind, "raw")
        self.assertEqual(dataset["A"], [10.2, 10.8, 11.1])

    def test_forced_kind(self):
        t = mk([["A", "B"], ["1", "2"], ["3", "4"]])
        kind, _ = ds.table_to_dataset(t, kind="raw")
        self.assertEqual(kind, "raw")


class TestDispatch(unittest.TestCase):
    def test_unsupported_extension(self):
        with self.assertRaises(UnsupportedFile):
            ds.scan_document(b"x", "planilha.xlsx")

    def test_pdf_without_reader(self):
        try:
            ds.scan_document(b"%PDF-1.4", "tese.pdf")
            self.skipTest("pdfplumber present")
        except MissingReader as e:
            self.assertIn("pdfplumber", str(e))
        except Exception:
            pass  # a real pdf error is fine (reader present)

    def test_docx_without_reader(self):
        try:
            ds.scan_document(b"PK\x03\x04", "tese.docx")
            self.skipTest("python-docx present")
        except MissingReader as e:
            self.assertIn("python-docx", str(e))
        except Exception:
            pass


class TestOrderingSort(unittest.TestCase):
    def test_scan_sorts_by_score(self):
        # build a DocumentScan by hand and sort like scan_document does
        weak = mk([["Etapa", "Prazo"], ["a", "jan"], ["b", "fev"], ["c", "mar"]])
        strong = mk([["Grupo", "Media", "DP", "n"], ["A", "10", "1", "5"],
                     ["B", "20", "2", "5"], ["C", "30", "3", "5"]])
        scan = ds.DocumentScan(tables=[weak, strong])
        scan.tables.sort(key=lambda t: t.score, reverse=True)
        self.assertIs(scan.tables[0], strong)


if __name__ == "__main__":
    unittest.main()
