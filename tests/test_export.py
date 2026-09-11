import os
import tempfile
import unittest

from app.core.orchestrator import AnalysisOptions, analyze_raw
from statistics.decision_engine import DesignSpec
from reports.excel_export import export_excel, summary_csv_string
from reports.pdf_report import build_html_report, save_html_report


def sample_result():
    raw = {"A": [6, 8, 4, 5, 3, 4], "B": [8, 12, 9, 11, 6, 8],
           "C": [13, 9, 11, 8, 7, 12]}
    return analyze_raw(raw, DesignSpec(n_factors=1), AnalysisOptions())


class TestExport(unittest.TestCase):
    def test_summary_csv_has_letters_column(self):
        res = sample_result()
        csv_txt = summary_csv_string(res)
        self.assertIn("Letras", csv_txt.splitlines()[0])
        self.assertIn("Grupo", csv_txt.splitlines()[0])

    def test_excel_export_fallback(self):
        res = sample_result()
        with tempfile.TemporaryDirectory() as d:
            out = export_excel(res, os.path.join(d, "report.xlsx"),
                               project_meta={"Nome": "Teste"})
            self.assertTrue(os.path.exists(out))
            # fallback creates a directory of CSVs incl. Resumo & Auditoria
            if os.path.isdir(out):
                names = set(os.listdir(out))
                self.assertIn("Resumo.csv", names)
                self.assertIn("Auditoria.csv", names)

    def test_html_report_contains_sections(self):
        res = sample_result()
        html = build_html_report(res, project_meta={"Pesquisador": "Fulano"})
        for token in ["Estatística descritiva", "Teste global",
                      "Compact Letter Display", "Auditoria",
                      "Por que este teste"]:
            self.assertIn(token, html)

    def test_save_html(self):
        res = sample_result()
        with tempfile.TemporaryDirectory() as d:
            p = save_html_report(res, os.path.join(d, "r.html"))
            self.assertTrue(os.path.exists(p))


if __name__ == "__main__":
    unittest.main()
