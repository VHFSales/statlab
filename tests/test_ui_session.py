import json
import unittest

from app.core.orchestrator import AnalysisOptions, analyze_raw
from app.core.ui_session import (build_workspace_dict,
                                 restore_from_workspace_dict)
from statistics.decision_engine import DesignSpec


RAW = {"A": [6, 8, 4, 5, 3, 4], "B": [8, 12, 9, 11, 6, 8],
       "C": [13, 9, 11, 8, 7, 12]}
PROJECT = {"Nome": "P1", "Pesquisador": "Fulano", "Laboratório": "Lab",
           "Descrição": "desc"}
DESIGN = {"n_factors": 1, "independent_groups": True}


class TestUISessionRoundTrip(unittest.TestCase):
    def test_roundtrip_raw_with_result(self):
        res = analyze_raw(RAW, DesignSpec(n_factors=1), AnalysisOptions())
        d = build_workspace_dict(PROJECT, "RAW", RAW, DESIGN, res)
        # must be JSON-serializable
        text = json.dumps(d)
        loaded = restore_from_workspace_dict(json.loads(text))
        self.assertEqual(loaded["project"]["Nome"], "P1")
        self.assertEqual(loaded["data_kind"], "RAW")
        self.assertEqual(loaded["data"]["A"], RAW["A"])
        self.assertEqual(loaded["design"]["n_factors"], 1)
        self.assertIsNotNone(loaded["result"])
        self.assertEqual(loaded["result"].analysis_id, res.analysis_id)
        self.assertEqual(loaded["result"].cld["display"], res.cld["display"])

    def test_roundtrip_summary(self):
        summ = {"A": {"mean": 10.0, "sd": 1.2, "n": 5},
                "B": {"mean": 14.0, "sd": 1.0, "n": 5}}
        d = build_workspace_dict(PROJECT, "SUMMARY", summ, DESIGN, None)
        loaded = restore_from_workspace_dict(json.loads(json.dumps(d)))
        self.assertEqual(loaded["data_kind"], "SUMMARY")
        self.assertEqual(loaded["data"]["A"]["mean"], 10.0)
        self.assertIsNone(loaded["result"])

    def test_restore_tolerant_of_missing_sections(self):
        loaded = restore_from_workspace_dict({"project": {"Nome": "X"}})
        self.assertEqual(loaded["project"]["Nome"], "X")
        self.assertEqual(loaded["data_kind"], "RAW")
        self.assertIsNone(loaded["data"])
        self.assertIsNone(loaded["result"])


if __name__ == "__main__":
    unittest.main()
