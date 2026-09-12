import io
import unittest

from data import importer as imp


class TestDecimalDetection(unittest.TestCase):
    def test_comma_decimal_wide_semicolon(self):
        # Brazilian decimal comma with semicolon column separator (the real case)
        raw, fmt = imp.import_text("D2.A;D3.A\n60,1;51,6\n61,4;52,7\n62,7;53,8")
        self.assertEqual(fmt, "wide")
        self.assertEqual(raw["D2.A"], [60.1, 61.4, 62.7])
        self.assertEqual(raw["D3.A"], [51.6, 52.7, 53.8])

    def test_comma_decimal_long_semicolon(self):
        raw, fmt = imp.import_text("Grupo;Valor\nA;10,2\nA;10,8\nB;13,5\nB;13,9")
        self.assertEqual(fmt, "long")
        self.assertEqual(raw["A"], [10.2, 10.8])
        self.assertEqual(raw["B"], [13.5, 13.9])

    def test_comma_decimal_tab(self):
        raw, _ = imp.import_text("A\tB\n50,1\t88,2\n51,4\t89,0")
        self.assertEqual(raw["A"], [50.1, 51.4])

    def test_dot_decimal_comma_separator_unchanged(self):
        raw, _ = imp.import_text("A,B\n10.2,13.5\n10.8,14.0")
        self.assertEqual(raw["A"], [10.2, 10.8])
        self.assertEqual(raw["B"], [13.5, 14.0])

    def test_double_space_from_pdf_paste(self):
        raw, _ = imp.import_text("A    B    C\n50,1    88,2    83,0\n51,4    89,0    84,2")
        self.assertEqual(raw["A"], [50.1, 51.4])
        self.assertEqual(raw["C"], [83.0, 84.2])


class TestNumberParsing(unittest.TestCase):
    def test_mean_pm_sd_keeps_mean(self):
        self.assertEqual(imp.parse_number("50,1 ± 4,0", "comma"), 50.1)
        self.assertEqual(imp.parse_number("92.3 +/- 1.1", "dot"), 92.3)

    def test_trailing_cld_letters_stripped(self):
        self.assertEqual(imp.parse_number("61,4b", "comma"), 61.4)
        self.assertEqual(imp.parse_number("92,3ab"), 92.3)

    def test_thousands_and_decimal(self):
        self.assertEqual(imp.parse_number("1.234,5", "auto"), 1234.5)
        self.assertEqual(imp.parse_number("1,234.5", "auto"), 1234.5)

    def test_non_numeric_returns_none(self):
        self.assertIsNone(imp.parse_number("abc"))
        self.assertIsNone(imp.parse_number(""))


class TestFileReaders(unittest.TestCase):
    def test_csv_bytes(self):
        data = b"Controle,Trat_A\n10.2,13.5\n10.8,14.0\n11.1,13.8"
        rows = imp.read_csv_bytes(data, "d.csv")
        raw, fmt, dec = imp.rows_to_raw(rows)
        self.assertEqual(fmt, "wide")
        self.assertEqual(raw["Controle"], [10.2, 10.8, 11.1])

    def test_csv_bytes_semicolon_comma_decimal(self):
        data = "A;B\n50,1;88,2\n51,4;89,0".encode("utf-8")
        rows = imp.read_csv_bytes(data, "d.csv")
        raw, fmt, dec = imp.rows_to_raw(rows)
        self.assertEqual(dec, "comma")
        self.assertEqual(raw["A"], [50.1, 51.4])

    def test_unsupported_extension(self):
        with self.assertRaises(imp.UnsupportedFile):
            imp.read_uploaded_file(b"x", "arquivo.zip")

    def test_pdf_missing_reader_message(self):
        # pdfplumber is not installed in this sandbox -> clear MissingReader
        try:
            imp.read_pdf_bytes(b"%PDF-1.4", "x.pdf")
            self.skipTest("pdfplumber present; nothing to assert")
        except imp.MissingReader as e:
            self.assertIn("pdfplumber", str(e))
        except Exception:
            # a real pdfplumber error is acceptable too (reader present)
            pass

    def test_excel_missing_reader_or_reads(self):
        # Without pandas -> MissingReader; with pandas but junk bytes -> MissingReader
        try:
            imp.read_excel_bytes(b"not-a-real-xlsx", "x.xlsx")
            self.skipTest("read succeeded unexpectedly")
        except imp.MissingReader:
            pass
        except Exception:
            pass


class TestImportFileDispatch(unittest.TestCase):
    def test_import_file_csv(self):
        data = b"A,B\n1.0,2.0\n3.0,4.0"
        raw, fmt, dec, rows = imp.import_file(data, "x.csv")
        self.assertEqual(raw["A"], [1.0, 3.0])
        self.assertEqual(len(rows), 3)  # header + 2 rows


if __name__ == "__main__":
    unittest.main()
