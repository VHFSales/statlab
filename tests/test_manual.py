"""Tests for the in-app MANUAL / AJUDA section.

These guard that the manual stays in sync with the app menu: every analysis
section shown in the sidebar must have a step-by-step entry in the manual, and
each entry must actually explain what it is and how to use it. They also exercise
``render`` against a minimal Streamlit stub so a template/formatting error is
caught in CI (Streamlit itself is not installed in the offline sandbox).
"""

import re
import unittest
from pathlib import Path

from app.ui import manual


# The analysis/workflow sections the manual is expected to cover. This mirrors the
# sidebar in app/ui/streamlit_app.py, minus "MANUAL / AJUDA" itself.
EXPECTED_SECTIONS = {
    "PROJETO", "DADOS", "DELINEAMENTO", "DESCRITIVA", "PRESSUPOSTOS", "ANÁLISE",
    "PÓS-TESTES", "OUTLIERS", "GRÁFICOS", "FATORIAL", "PAREADO",
    "MEDIDAS REPETIDAS", "CORRELAÇÃO", "REGRESSÃO", "LOTE", "RELATÓRIO", "EXPORTAR",
}


class _Ctx:
    def __enter__(self):
        return self

    def __exit__(self, *a):
        return False


class _StStub:
    """Records every string passed to Streamlit text methods."""

    def __init__(self):
        self.texts = []

    def _record(self, *a, **k):
        for x in a:
            if isinstance(x, str):
                self.texts.append(x)

    header = subheader = markdown = caption = info = warning = success = _record

    def expander(self, *a, **k):
        self._record(*a)
        return _Ctx()


class TestManualCoverage(unittest.TestCase):
    def test_covers_every_menu_section(self):
        self.assertEqual(manual.COVERED_SECTIONS, EXPECTED_SECTIONS,
                         "O manual precisa cobrir exatamente as seções do menu.")

    def test_menu_and_manual_are_in_sync(self):
        # Read the actual sidebar list from the app and compare (minus MANUAL).
        src = Path(__file__).resolve().parents[1] / "app" / "ui" / "streamlit_app.py"
        text = src.read_text(encoding="utf-8")
        block = text.split('st.sidebar.radio("Seção", [', 1)[1].split("])", 1)[0]
        menu = set(re.findall(r'"([^"]+)"', block)) - {"MANUAL / AJUDA"}
        self.assertEqual(menu, manual.COVERED_SECTIONS,
                         "Menu e manual divergiram: atualize app/ui/manual.py.")

    def test_each_section_has_what_and_how(self):
        for name, info in manual.SECOES.items():
            self.assertTrue(info.get("o_que", "").strip(),
                            f"Seção {name} sem explicação 'o_que'.")
            self.assertTrue(info.get("passos"),
                            f"Seção {name} sem passos de 'como usar'.")


class TestManualContent(unittest.TestCase):
    def test_has_core_learner_content(self):
        self.assertTrue(manual.INTRO.strip())
        self.assertIn("p", manual.COMO_LER_P.lower())
        self.assertGreaterEqual(len(manual.QUICK_START), 5)
        self.assertGreaterEqual(len(manual.CONCEITOS), 8)
        self.assertGreaterEqual(len(manual.GLOSSARIO), 10)
        self.assertGreaterEqual(len(manual.FAQ), 4)

    def test_render_runs_without_error(self):
        st = _StStub()
        manual.render(st)
        blob = "\n".join(st.texts)
        # a few anchors that must reach the screen
        self.assertIn("Manual", blob)
        self.assertIn("valor-p", blob.lower())
        for name in EXPECTED_SECTIONS:
            self.assertIn(name, blob, f"Seção {name} não apareceu no manual renderizado.")


if __name__ == "__main__":
    unittest.main()
