import unittest

from statistics import games_howell
from statistics.anova import InsufficientDataError
from statistics.types import RawGroup
from tests.reference_data import HETERO3


def groups_from(d):
    return [RawGroup(k, v) for k, v in d.items() if isinstance(v, list)]


class TestGamesHowell(unittest.TestCase):
    def setUp(self):
        self.res = games_howell.games_howell_raw(groups_from(HETERO3))

    def test_per_pair_df_distinct(self):
        dfs = {round(c.df, 6) for c in self.res.comparisons}
        self.assertGreater(len(dfs), 1)

    def test_unpooled_se(self):
        import math
        # verify SE for A vs B uses s_i^2/n_i + s_j^2/n_j (unpooled)
        a = HETERO3["A"]; b = HETERO3["B"]
        na, nb = len(a), len(b)
        ma, mb = sum(a) / na, sum(b) / nb
        va = sum((x - ma) ** 2 for x in a) / (na - 1)
        vb = sum((x - mb) ** 2 for x in b) / (nb - 1)
        expected_se = math.sqrt(va / na + vb / nb)
        ab = next(c for c in self.res.comparisons
                  if {c.group1, c.group2} == {"A", "B"})
        self.assertAlmostEqual(ab.se, expected_se, places=12)

    def test_separated_group_significant(self):
        # group C is far from A and B
        ac = next(c for c in self.res.comparisons
                  if {c.group1, c.group2} == {"A", "C"})
        bc = next(c for c in self.res.comparisons
                  if {c.group1, c.group2} == {"B", "C"})
        self.assertTrue(ac.significant)
        self.assertTrue(bc.significant)

    def test_ci_contains_diff(self):
        for c in self.res.comparisons:
            self.assertLessEqual(c.ci_low, c.diff)
            self.assertGreaterEqual(c.ci_high, c.diff)

    def test_small_n_refused(self):
        with self.assertRaises(InsufficientDataError):
            games_howell.games_howell_raw(
                [RawGroup("A", [1]), RawGroup("B", [2, 3, 4])]
            )


if __name__ == "__main__":
    unittest.main()
