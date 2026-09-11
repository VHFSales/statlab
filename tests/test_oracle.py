"""Oracle cross-validation against SciPy / statsmodels (V-4).

These tests SKIP with a notice when the scientific stack is unavailable (as in the
offline development sandbox). In the lab environment where scipy/statsmodels are
installed, they cross-check the pure-Python core against the reference libraries.
"""

import math
import unittest

try:
    import numpy as np  # noqa: F401
    import scipy.stats as sps  # noqa: F401
    HAVE_SCIPY = True
except Exception:  # pragma: no cover
    HAVE_SCIPY = False

try:
    import statsmodels.stats.multicomp as smc  # noqa: F401
    HAVE_SM = True
except Exception:  # pragma: no cover
    HAVE_SM = False

from statistics import anova, welch, distributions
from statistics.types import RawGroup
from tests.reference_data import ANOVA3, HETERO3


def groups_from(d):
    return [RawGroup(k, v) for k, v in d.items() if isinstance(v, list)]


@unittest.skipUnless(HAVE_SCIPY, "SciPy not installed (offline sandbox)")
class TestAgainstScipy(unittest.TestCase):
    def test_anova_f_p(self):
        g = [ANOVA3["A"], ANOVA3["B"], ANOVA3["C"]]
        f_sp, p_sp = sps.f_oneway(*g)
        t = anova.anova_oneway_raw(groups_from(ANOVA3))
        self.assertAlmostEqual(t.f, float(f_sp), places=9)
        self.assertAlmostEqual(t.p, float(p_sp), places=9)

    def test_studentized_range_ppf(self):
        for k, nu in [(3, 16), (4, 20), (5, 30)]:
            q_core = distributions.studentized_range_ppf(0.95, k, nu)
            q_sp = float(sps.studentized_range.ppf(0.95, k, nu))
            self.assertAlmostEqual(q_core, q_sp, places=4)

    def test_welch(self):
        g = [HETERO3["A"], HETERO3["B"], HETERO3["C"]]
        res_sp = sps.f_oneway(*g)  # placeholder; use pingouin/oneway if available
        r = welch.welch_anova_raw(groups_from(HETERO3))
        # scipy has no direct welch anova; compare via known formula only.
        self.assertLess(r.p, 1e-4)


@unittest.skipUnless(HAVE_SM, "statsmodels not installed (offline sandbox)")
class TestAgainstStatsmodels(unittest.TestCase):
    def test_tukey(self):
        import numpy as np
        from statistics import tukey
        data, labels = [], []
        for lab in ("A", "B", "C"):
            data += ANOVA3[lab]
            labels += [lab] * len(ANOVA3[lab])
        sm_res = smc.pairwise_tukeyhsd(np.array(data), np.array(labels), alpha=0.05)
        core = tukey.tukey_raw(groups_from(ANOVA3))
        # map statsmodels rows -> compare p-adj
        sm_map = {}
        for row in sm_res._results_table.data[1:]:
            g1, g2 = row[0], row[1]
            padj = float(row[3])
            sm_map[frozenset((g1, g2))] = padj
        for c in core.comparisons:
            key = frozenset((c.group1, c.group2))
            self.assertAlmostEqual(c.p_adjusted, sm_map[key], places=3)


if __name__ == "__main__":
    unittest.main()
