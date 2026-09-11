import os
import tempfile
import unittest

from app.core.orchestrator import (AnalysisOptions, analyze_raw,
                                   reproduce_from_config, results_match)
from statistics.decision_engine import DesignSpec
from persistence.result_store import (build_repro_config, load_repro_config,
                                       load_result, result_from_dict,
                                       result_to_dict, save_repro_config,
                                       save_result)
from persistence.workspace import Workspace


RAW = {"A": [6, 8, 4, 5, 3, 4], "B": [8, 12, 9, 11, 6, 8],
       "C": [13, 9, 11, 8, 7, 12]}


def sample():
    return analyze_raw(RAW, DesignSpec(n_factors=1), AnalysisOptions())


class TestResultRoundTrip(unittest.TestCase):
    def test_dict_roundtrip(self):
        r = sample()
        r2 = result_from_dict(result_to_dict(r))
        self.assertEqual(r2.analysis_id, r.analysis_id)
        self.assertEqual(r2.omnibus_kind, r.omnibus_kind)
        self.assertAlmostEqual(r2.omnibus["f"], r.omnibus["f"], places=12)
        self.assertEqual(r2.cld["display"], r.cld["display"])

    def test_file_roundtrip(self):
        r = sample()
        with tempfile.TemporaryDirectory() as d:
            p = save_result(r, os.path.join(d, "res.json"))
            r2 = load_result(p)
        self.assertTrue(results_match(r, r2))


class TestReproduction(unittest.TestCase):
    def test_repro_config_reproduces_identically(self):
        design = DesignSpec(n_factors=1)
        options = AnalysisOptions(alpha=0.05)
        r = analyze_raw(RAW, design, options)
        cfg = build_repro_config(RAW, "RAW", design, options, r)
        r2 = reproduce_from_config(cfg)
        self.assertTrue(results_match(r, r2))
        # data hash preserved
        self.assertEqual(r2.data_hash, r.data_hash)

    def test_repro_config_file_roundtrip(self):
        design = DesignSpec(n_factors=1)
        options = AnalysisOptions(alpha=0.01)
        r = analyze_raw(RAW, design, options)
        cfg = build_repro_config(RAW, "RAW", design, options, r)
        with tempfile.TemporaryDirectory() as d:
            p = save_repro_config(cfg, os.path.join(d, "cfg.json"))
            cfg2 = load_repro_config(p)
        r2 = reproduce_from_config(cfg2)
        self.assertTrue(results_match(r, r2))
        self.assertEqual(r2.alpha, 0.01)

    def test_summary_repro(self):
        from statistics import descriptive
        summ = {}
        for lab, vals in RAW.items():
            dr = descriptive.describe_group(lab, vals)
            summ[lab] = {"mean": dr.mean, "sd": dr.sd, "n": dr.n}
        from app.core.orchestrator import analyze_summary
        design = DesignSpec(n_factors=1)
        options = AnalysisOptions()
        r = analyze_summary(summ, design, options)
        cfg = build_repro_config(summ, "SUMMARY", design, options, r)
        r2 = reproduce_from_config(cfg)
        self.assertTrue(results_match(r, r2))


class TestWorkspace(unittest.TestCase):
    def test_store_and_get(self):
        ws = Workspace(project={"Nome": "P1"})
        r = sample()
        ws.store_result("exp1/Y", r)
        got = ws.get_result("exp1/Y")
        self.assertIsNotNone(got)
        self.assertEqual(got.analysis_id, r.analysis_id)

    def test_staleness_detection(self):
        ws = Workspace()
        r = sample()
        ws.store_result("k", r)
        # same hash -> not stale
        self.assertFalse(ws.mark_stale_by_data_hash("k", r.data_hash))
        # different hash -> stale
        self.assertTrue(ws.mark_stale_by_data_hash("k", "deadbeef"))
        self.assertIn("k", ws.stale_keys())

    def test_snapshot_and_persistence(self):
        ws = Workspace(project={"Nome": "P"})
        ws.store_result("k", sample())
        ws.take_snapshot("original")
        with tempfile.TemporaryDirectory() as d:
            p = ws.save(os.path.join(d, "ws.json"))
            ws2 = Workspace.load(p)
        self.assertEqual(ws2.project["Nome"], "P")
        self.assertEqual(len(ws2.snapshots), 1)
        self.assertEqual(ws2.snapshots[0].label, "original")
        self.assertIsNotNone(ws2.get_result("k"))


if __name__ == "__main__":
    unittest.main()
