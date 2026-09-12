import unittest

from data import importer as imp


class TestDedupHeaders(unittest.TestCase):
    def test_empty_headers_named(self):
        out = imp.dedup_headers(["", "Classe", ""])
        self.assertEqual(out, ["Coluna 1", "Classe", "Coluna 3"])

    def test_duplicates_suffixed(self):
        out = imp.dedup_headers(["Classe", "Classe", "Classe"])
        self.assertEqual(out, ["Classe", "Classe (2)", "Classe (3)"])

    def test_all_unique(self):
        self.assertEqual(len(set(imp.dedup_headers(["", "Classe", "Classe", ""]))), 4)

    def test_mixed(self):
        out = imp.dedup_headers(["", "A", "A", "B", ""])
        self.assertEqual(len(set(out)), 5)   # every name unique
        self.assertNotIn("", out)            # no empty names


class TestRawWideNoCollision(unittest.TestCase):
    def test_duplicate_and_empty_headers_do_not_merge(self):
        rows = [["", "Classe", "Classe", ""],
                ["10.2", "13.5", "12.1", "9.9"],
                ["10.8", "14.0", "11.8", "10.1"]]
        raw, fmt, dec = imp.rows_to_raw(rows, fmt="wide")
        # 4 distinct groups, no empty label, no data lost
        self.assertEqual(len(raw), 4)
        self.assertNotIn("", raw)
        self.assertEqual(raw["Classe"], [13.5, 14.0])
        self.assertEqual(raw["Classe (2)"], [12.1, 11.8])


class TestSummaryNoCollision(unittest.TestCase):
    def test_duplicate_group_label_kept_separate(self):
        rows = imp.parse_delimited_text(
            "Grupo;Media;DP;n\nA;10,5;1,2;5\nA;13,7;0,8;5\nB;15,2;1,0;6")
        summ, _ = imp.rows_to_summary(rows)
        self.assertEqual(len(summ), 3)  # A, A (2), B — nothing overwritten
        self.assertIn("A", summ)
        self.assertIn("A (2)", summ)
        self.assertEqual(summ["A"]["mean"], 10.5)
        self.assertEqual(summ["A (2)"]["mean"], 13.7)


if __name__ == "__main__":
    unittest.main()
