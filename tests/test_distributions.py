import math
import unittest

from statistics import distributions as d
from tests.reference_data import Q_CRIT_05


class TestNormal(unittest.TestCase):
    def test_ppf(self):
        self.assertAlmostEqual(d.norm_ppf(0.975), 1.959963985, places=7)
        self.assertAlmostEqual(d.norm_ppf(0.995), 2.575829304, places=7)
        self.assertAlmostEqual(d.norm_ppf(0.5), 0.0, places=10)

    def test_cdf(self):
        self.assertAlmostEqual(d.norm_cdf(1.96), 0.9750021049, places=9)
        self.assertAlmostEqual(d.norm_cdf(0.0), 0.5, places=12)

    def test_ppf_cdf_roundtrip(self):
        for p in (0.01, 0.1, 0.3, 0.7, 0.9, 0.99):
            self.assertAlmostEqual(d.norm_cdf(d.norm_ppf(p)), p, places=9)


class TestStudentT(unittest.TestCase):
    def test_cauchy(self):
        self.assertAlmostEqual(d.t_cdf(1.0, 1.0), 0.75, places=8)

    def test_critical(self):
        # t_0.975(10) = 2.228138852
        self.assertAlmostEqual(d.t_cdf(2.228138852, 10), 0.975, places=6)
        self.assertAlmostEqual(d.t_two_sided_p(2.228138852, 10), 0.05, places=6)

    def test_approaches_normal(self):
        self.assertAlmostEqual(d.t_cdf(1.96, 1e6), 0.9750021, places=5)


class TestF(unittest.TestCase):
    def test_critical(self):
        self.assertAlmostEqual(d.f_sf(3.238871523, 3, 16), 0.05, places=6)
        self.assertAlmostEqual(d.f_cdf(3.238871523, 3, 16), 0.95, places=6)

    def test_closed_form_df1_2(self):
        # P(F>f) = (1 + 2f/n)^(-n/2) for df1=2
        for f, n in [(9.2647, 15), (3.0, 20), (1.5, 8)]:
            self.assertAlmostEqual(d.f_sf(f, 2, n), (1 + 2 * f / n) ** (-n / 2), places=10)

    def test_relation_to_t(self):
        # F(1, nu) sf at t^2 equals two-sided t p
        self.assertAlmostEqual(d.f_sf(2.228138852 ** 2, 1, 10), 0.05, places=6)


class TestStudentizedRange(unittest.TestCase):
    def test_critical_values(self):
        for (k, nu), qexp in Q_CRIT_05.items():
            nu_val = float("inf") if nu == "inf" else nu
            q = d.studentized_range_ppf(0.95, k, nu_val)
            self.assertAlmostEqual(q, qexp, delta=2e-3,
                                   msg=f"q_0.05({k},{nu}) got {q} expected {qexp}")

    def test_cdf_monotone(self):
        prev = -1.0
        for q in (1.0, 2.0, 3.0, 4.0, 5.0):
            c = d.studentized_range_cdf(q, 3, 20)
            self.assertGreaterEqual(c, prev)
            prev = c
            self.assertTrue(0.0 <= c <= 1.0)


if __name__ == "__main__":
    unittest.main()
