import unittest

from data import transformer as tr


class TestWideLong(unittest.TestCase):
    def test_wide_to_long_drops_missing(self):
        pairs = tr.wide_to_long({"A": [1.0, None, 3.0], "B": [4.0, float("nan")]})
        self.assertIn(("A", 1.0), pairs)
        self.assertIn(("A", 3.0), pairs)
        self.assertIn(("B", 4.0), pairs)
        self.assertEqual(len(pairs), 3)  # missing dropped, not zeroed

    def test_long_to_wide_roundtrip(self):
        raw = {"A": [1.0, 2.0], "B": [3.0]}
        pairs = tr.wide_to_long(raw)
        back = tr.long_to_wide(pairs)
        self.assertEqual(sorted(back["A"]), [1.0, 2.0])
        self.assertEqual(back["B"], [3.0])


class TestMissing(unittest.TestCase):
    def test_drop_missing_report(self):
        clean, rep = tr.drop_missing({"A": [1, None, 3, "x"], "B": [4, 5]})
        self.assertEqual(clean["A"], [1.0, 3.0])
        self.assertEqual(rep.per_group_informed["A"], 4)
        self.assertEqual(rep.per_group_valid["A"], 2)
        self.assertEqual(rep.per_group_missing["A"], 2)
        self.assertEqual(rep.total_missing, 2)

    def test_never_zero_fill(self):
        clean, _ = tr.drop_missing({"A": [None, None], "B": [1, 2]})
        self.assertEqual(clean["A"], [])          # NOT [0, 0]


class TestAggregation(unittest.TestCase):
    def test_mean_aggregation_reduces_to_unit_n(self):
        reps = {
            "Trat": {"u1": [10, 12, 11], "u2": [20, 22], "u3": [30]},
            "Ctrl": {"u4": [5, 5, 5], "u5": [7, 9]},
        }
        out, rep = tr.aggregate_technical_replicates(reps, agg="mean")
        self.assertEqual(rep.units_per_group["Trat"], 3)  # 3 units, not 6 obs
        self.assertEqual(rep.units_per_group["Ctrl"], 2)
        self.assertAlmostEqual(out["Trat"][0], 11.0, places=9)  # mean(10,12,11)
        self.assertAlmostEqual(out["Trat"][1], 21.0, places=9)  # mean(20,22)
        self.assertAlmostEqual(out["Ctrl"][1], 8.0, places=9)   # mean(7,9)

    def test_missing_replicate_dropped(self):
        reps = {"A": {"u1": [1, None, 3]}, "B": {"u2": [None, None]}}
        out, rep = tr.aggregate_technical_replicates(reps)
        self.assertAlmostEqual(out["A"][0], 2.0, places=9)  # mean(1,3), not (1+0+3)/3
        self.assertEqual(out["B"], [])                       # no valid unit


if __name__ == "__main__":
    unittest.main()
