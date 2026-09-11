import unittest

from statistics import anova, effect_sizes
from statistics.types import RawGroup
from tests.reference_data import ANOVA3


def groups_from(d):
    return [RawGroup(k, v) for k, v in d.items() if isinstance(v, list)]


class TestEffectSizes(unittest.TestCase):
    def setUp(self):
        self.t = anova.anova_oneway_raw(groups_from(ANOVA3))
        self.es = effect_sizes.effect_sizes_from_anova(self.t)

    def test_eta_squared(self):
        self.assertAlmostEqual(self.es.eta_squared, 84.0 / 152.0, places=9)

    def test_omega_squared(self):
        msw = 68.0 / 15.0
        expected = (84.0 - 2 * msw) / (152.0 + msw)
        self.assertAlmostEqual(self.es.omega_squared, expected, places=9)

    def test_omega_clamped_nonnegative(self):
        # near-null effect: three groups with almost identical means
        g = [RawGroup("A", [5.0, 5.1, 4.9, 5.0]),
             RawGroup("B", [5.0, 4.9, 5.1, 5.0]),
             RawGroup("C", [5.05, 4.95, 5.0, 5.0])]
        t = anova.anova_oneway_raw(g)
        es = effect_sizes.effect_sizes_from_anova(t)
        self.assertGreaterEqual(es.omega_squared, 0.0)

    def test_labels_note_present(self):
        self.assertTrue(any("context-dependent" in n for n in self.es.notes))


if __name__ == "__main__":
    unittest.main()
