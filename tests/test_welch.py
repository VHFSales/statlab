import unittest

from statistics import welch
from statistics.anova import InsufficientDataError
from statistics.types import RawGroup
from tests.reference_data import HETERO3, ANOVA3


def groups_from(d):
    return [RawGroup(k, v) for k, v in d.items() if isinstance(v, list)]


class TestWelch(unittest.TestCase):
    def test_hetero_dataset(self):
        r = welch.welch_anova_raw(groups_from(HETERO3))
        self.assertEqual(r.df1, 2)
        # strongly separated group C -> very small p
        self.assertLess(r.p, 1e-4)
        # df2 fractional and between reasonable bounds
        self.assertTrue(0 < r.df2 < r.n_total)

    def test_matches_anova_direction(self):
        # On the balanced homoscedastic-ish ANOVA3 data, Welch should also be
        # significant (sanity), though F* differs from classical F.
        r = welch.welch_anova_raw(groups_from(ANOVA3))
        self.assertLess(r.p, 0.05)

    def test_zero_variance_refused(self):
        with self.assertRaises(InsufficientDataError):
            welch.welch_anova_raw([RawGroup("A", [3, 3, 3]), RawGroup("B", [4, 5, 6])])

    def test_small_n_refused(self):
        with self.assertRaises(InsufficientDataError):
            welch.welch_anova_raw([RawGroup("A", [3]), RawGroup("B", [4, 5, 6])])


if __name__ == "__main__":
    unittest.main()
