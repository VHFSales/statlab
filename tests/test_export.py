import os
import tempfile
import unittest

from app.core.orchestrator import (AnalysisOptions, analyze_batch, analyze_raw)
from statistics.decision_engine import DesignSpec
from reports.excel_export import (batch_csv_string, export_excel,
                                  summary_csv_string)
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

    def test_ttest_appears_in_html_and_excel(self):
        raw = {"A": [10.2, 10.8, 11.1, 10.6, 10.4],
               "B": [13.5, 14.0, 13.8, 14.2, 13.9]}
        res = analyze_raw(raw, DesignSpec(n_factors=1), AnalysisOptions())
        self.assertIsNotNone(res.ttest)
        html = build_html_report(res)
        self.assertIn("Comparação de dois grupos", html)
        # posthoc rows in Excel bundle should carry the t-test
        with tempfile.TemporaryDirectory() as d:
            out = export_excel(res, os.path.join(d, "r.xlsx"))
            if os.path.isdir(out):
                with open(os.path.join(out, "Pós-testes.csv"), encoding="utf-8") as f:
                    content = f.read()
                self.assertIn("d de Cohen", content)

    def test_batch_csv(self):
        variables = {
            "Var1": {"A": [1, 2, 3], "B": [8, 9, 10]},
            "Var2": {"A": [5, 5, 6], "B": [5, 6, 5]},
        }
        out = analyze_batch(variables, DesignSpec(n_factors=1), AnalysisOptions(),
                            fdr_method="holm")
        csv_txt = batch_csv_string(out)
        self.assertIn("Variável", csv_txt.splitlines()[0])
        self.assertIn("p ajustado", csv_txt.splitlines()[0])
        self.assertIn("Var1", csv_txt)


if __name__ == "__main__":
    unittest.main()
