import unittest

from data.importer import detect_format, import_text, parse_delimited_text


class TestImporter(unittest.TestCase):
    def test_wide_detection_and_parse(self):
        text = "A\tB\tC\n10.2\t13.5\t14.9\n10.5\t13.7\t15.1"
        rows = parse_delimited_text(text)
        self.assertEqual(detect_format(rows), "wide")
        raw, fmt = import_text(text)
        self.assertEqual(fmt, "wide")
        self.assertEqual(raw["A"], [10.2, 10.5])
        self.assertEqual(raw["C"], [14.9, 15.1])

    def test_long_detection_and_parse(self):
        text = "Grupo,Valor\nA,10.2\nA,10.5\nB,13.5\nB,13.7"
        rows = parse_delimited_text(text)
        self.assertEqual(detect_format(rows), "long")
        raw, fmt = import_text(text)
        self.assertEqual(fmt, "long")
        self.assertEqual(raw["A"], [10.2, 10.5])
        self.assertEqual(raw["B"], [13.5, 13.7])

    def test_missing_cells_become_none_not_zero(self):
        text = "A,B\n1,4\n,5\n3,6"
        raw, _ = import_text(text, fmt="wide")
        self.assertEqual(raw["A"], [1.0, None, 3.0])  # NOT [1,0,3]

    def test_text_in_numeric_becomes_none(self):
        text = "A,B\n1,4\noops,5"
        raw, _ = import_text(text, fmt="wide")
        self.assertIsNone(raw["A"][1])


if __name__ == "__main__":
    unittest.main()
