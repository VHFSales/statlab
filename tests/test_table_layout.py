import unittest

from data import table_layout as tl


# Reproduces the "Tabela 29" layout: 2 header rows, label column, mean±sd cells
# with grouping letters.
T29 = [
    ["Amostras", "Brilho antes", "Brilho antes", "Brilho antes"],
    ["", "20", "60", "85"],
    ["D2.A", "61,4 ±1,3b", "94,8 ±0,3a", "92,3 ±1,2a"],
    ["D3.A", "52,7 ±1,1c", "82,8 ±0,4c", "78,2 ±0,9c"],
    ["D4.A", "67,8 ±2,8a", "96,3 ±1,1a", "88,4 ±2,5b"],
    ["D5.A", "71,8 ±4,2a", "97,5 ±1,1a", "92,1 ±2,8a"],
]


class TestMeanSD(unittest.TestCase):
    def test_pm_with_letter(self):
        r = tl.parse_mean_sd("61,4 ±1,3b")
        self.assertAlmostEqual(r.mean, 61.4)
        self.assertAlmostEqual(r.sd, 1.3)
        self.assertEqual(r.letter, "b")

    def test_paren_sd(self):
        r = tl.parse_mean_sd("92,3 (1,4)")
        self.assertAlmostEqual(r.mean, 92.3)
        self.assertAlmostEqual(r.sd, 1.4)

    def test_two_numbers(self):
        r = tl.parse_mean_sd("50,1 4,0")
        self.assertAlmostEqual(r.mean, 50.1)
        self.assertAlmostEqual(r.sd, 4.0)

    def test_plain_number(self):
        r = tl.parse_mean_sd("61,4")
        self.assertAlmostEqual(r.mean, 61.4)
        self.assertIsNone(r.sd)

    def test_superscript_letter_mapped(self):
        r = tl.parse_mean_sd("94,6 \u00b11,6\u1d47")  # ᵇ
        self.assertEqual(r.letter, "b")

    def test_text_returns_none(self):
        self.assertIsNone(tl.parse_mean_sd("Classe A"))
        self.assertIsNone(tl.parse_mean_sd(""))

    def test_cell_looks_mean_sd(self):
        self.assertTrue(tl.cell_looks_mean_sd("61,4 ±1,3"))
        self.assertTrue(tl.cell_looks_mean_sd("92,3 (1,4)"))
        self.assertFalse(tl.cell_looks_mean_sd("61,4"))


class TestHeaders(unittest.TestCase):
    def test_detects_two_header_rows(self):
        self.assertEqual(tl.detect_header_rows(T29), 2)

    def test_single_header_row(self):
        rows = [["A", "B", "C"], ["10.2", "13.5", "12.1"], ["10.8", "14.0", "11.8"]]
        self.assertEqual(tl.detect_header_rows(rows), 1)

    def test_merge_spanning_titles(self):
        labels = tl.merge_header_rows(T29[:2])
        self.assertEqual(labels[1], "Brilho antes 20")
        self.assertEqual(labels[2], "Brilho antes 60")
        self.assertEqual(labels[3], "Brilho antes 85")

    def test_label_column_by_hint(self):
        self.assertEqual(tl.detect_label_column(T29, 2), 0)

    def test_label_column_fallback(self):
        rows = [["Especime", "V1", "V2"], ["a", "1", "2"], ["b", "3", "4"],
                ["c", "5", "6"]]
        self.assertEqual(tl.detect_label_column(rows, 1), 0)


class TestClassify(unittest.TestCase):
    def test_summary(self):
        self.assertEqual(tl.classify_table(T29), "summary")

    def test_raw(self):
        rows = [["A", "B", "C"], ["10.2", "13.5", "12.1"], ["10.8", "14.0", "11.8"],
                ["11.1", "13.8", "12.5"]]
        self.assertEqual(tl.classify_table(rows), "raw")

    def test_descriptive(self):
        rows = [["Classe", "Aplicacao", "Resistencia"],
                ["A", "servico externo", "alta"],
                ["B", "servico interno", "media"],
                ["C", "estrutural", "baixa"]]
        self.assertEqual(tl.classify_table(rows), "descriptive")


class TestInterpret(unittest.TestCase):
    def test_summary_sample_by_condition(self):
        it = tl.interpret_table(T29, default_n=5)
        self.assertEqual(it.kind, "summary")
        self.assertEqual(it.n_header_rows, 2)
        self.assertEqual(it.label_col, 0)
        self.assertIn("Brilho antes 20", it.summary_by_column)
        col = it.summary_by_column["Brilho antes 20"]
        self.assertEqual(col["D2.A"], {"mean": 61.4, "sd": 1.3, "n": 5})
        self.assertEqual(it.grouping_letters["Brilho antes 20"]["D4.A"], "a")

    def test_summary_without_n(self):
        it = tl.interpret_table(T29)
        col = it.summary_by_column["Brilho antes 20"]
        self.assertNotIn("n", col["D2.A"])
        self.assertTrue(any("tamanho amostral" in m.lower() for m in it.messages))

    def test_raw_wide(self):
        rows = [["A", "B", "C"], ["10.2", "13.5", "12.1"], ["10.8", "14.0", "11.8"],
                ["11.1", "13.8", "12.5"]]
        it = tl.interpret_table(rows)
        self.assertEqual(it.kind, "raw")
        self.assertEqual(it.raw["A"], [10.2, 10.8, 11.1])

    def test_descriptive_message(self):
        rows = [["Classe", "Aplicacao"], ["A", "externo"], ["B", "interno"],
                ["C", "estrutural"]]
        it = tl.interpret_table(rows)
        self.assertEqual(it.kind, "descriptive")
        self.assertTrue(it.messages)

    def test_reproduces_original_tukey_letters(self):
        # end-to-end: analysing "Brilho antes 20" with n=5 should match the
        # letters printed in the original table.
        from app.core.orchestrator import analyze_summary, AnalysisOptions
        from statistics.decision_engine import DesignSpec
        it = tl.interpret_table(T29, default_n=5)
        ds = it.summary_by_column["Brilho antes 20"]
        r = analyze_summary(ds, DesignSpec(n_factors=1), AnalysisOptions())
        self.assertFalse(r.refusals)
        # StatLab CLD should agree with the original letters for this column
        self.assertEqual(r.cld["display"], it.grouping_letters["Brilho antes 20"])


# --------------------------------------------------------------------------- #
# Real tables from a materials thesis (factor × condition, before/after layout,
# with intercalated "Variação (%)" rows that must NOT be loaded as data).
# --------------------------------------------------------------------------- #

# Tabela 3 — contact angle: Potência × Condição (Sem/Com plasma) + Variação rows.
# Note the factor "600 W" sits on the MIDDLE row of each block (the "Com plasma"
# row); the control row above has "N/A".
T3_CONTACT_ANGLE = [
    ["Potência", "Condição", "Glicerol (°)", "Diiodometano (°)"],
    ["N/A", "Sem plasma", "36,9 ± 2,9", "17,4 ± 3,8"],
    ["600 W", "Com plasma", "20,0 ± 4,0", "19,0 ± 4,5"],
    ["", "Variação (%)", "45,8%", "9,3%"],
    ["N/A", "Sem plasma", "34,1 ± 7,3", "20,4 ± 5,9"],
    ["750 W", "Com plasma", "16,0 ± 4,7", "12,5 ± 2,4"],
    ["", "Variação (%)", "53%", "38,5%"],
    ["N/A", "Sem plasma", "73,7 ± 11,2", "33,8 ± 3,1"],
    ["900 W", "Com plasma", "26,3 ± 8,7", "27,9 ± 3,6"],
    ["", "Variação (%)", "64,3%", "17,4%"],
]

# Tabela 4 — surface energy: same layout but bare means, NO ± sd.
T4_ENERGY = [
    ["Potência", "Condição", "γtotal (mJ/m²)", "γSd (mJ/m²)", "γSp (mJ/m²)"],
    ["N/A", "Sem plasma", "58,1", "48,5", "9,6"],
    ["600 W", "Com plasma", "63,7", "48,1", "15,6"],
    ["", "Variação (%)", "9,6", "0,8", "62,5"],
    ["N/A", "Sem plasma", "58,8", "47,7", "11,1"],
    ["750 W", "Com plasma", "65,3", "49,6", "15,7"],
    ["", "Variação (%)", "11,1", "4,1", "41,4"],
    ["N/A", "Sem plasma", "42,9", "42,6", "0,3"],
    ["900 W", "Com plasma", "60,5", "45,1", "15,5"],
    ["", "Variação (%)", "41,0", "5,9", "5063"],
]

# Tabela 2 — adhesive properties: transposed "measure × sample" (no factor col).
T2_ADHESIVE = [
    ["Resultados", "PVAc", "PVAc + AlCl\u2083"],
    ["pH", "4,43", "2,86"],
    ["Viscosidade (mPa\u00b7s)", "4900 ± 79", "3800 ± 100"],
    ["Teor de sólidos (%)", "48,6 ± 0,3", "47,8 ± 0,7"],
]


class TestDerivedRows(unittest.TestCase):
    def test_variation_label_row_is_derived(self):
        self.assertTrue(tl.row_is_derived(["", "Variação (%)", "45,8%", "9,3%"]))

    def test_all_percent_row_is_derived(self):
        self.assertTrue(tl.row_is_derived(["", "", "45,8%", "9,3%"]))

    def test_delta_symbol_row_is_derived(self):
        self.assertTrue(tl.row_is_derived(["Δ", "12,3", "4,5"]))

    def test_normal_data_row_not_derived(self):
        self.assertFalse(tl.row_is_derived(["600 W", "Com plasma", "20,0 ± 4,0"]))


class TestGroupedBeforeAfter(unittest.TestCase):
    def test_unit_is_not_a_grouping_letter(self):
        # "600 W" must not be parsed as value 600 with grouping letter "w"
        r = tl.parse_mean_sd("600 W")
        self.assertEqual(r.letter, "")

    def test_glued_lowercase_letter_still_works(self):
        r = tl.parse_mean_sd("61,4 ±1,3b")
        self.assertEqual(r.letter, "b")

    def test_detects_layout(self):
        n_header = tl.detect_header_rows(T3_CONTACT_ANGLE)
        self.assertEqual(
            tl.detect_grouped_before_after(T3_CONTACT_ANGLE, n_header), (0, 1))

    def test_contact_angle_loads_six_paired_groups(self):
        it = tl.interpret_table(T3_CONTACT_ANGLE, default_n=5)
        self.assertEqual(it.layout, "grouped_before_after")
        self.assertEqual(it.dropped_derived_rows, 3)
        self.assertEqual(it.measurement_columns,
                         ["Glicerol (°)", "Diiodometano (°)"])
        col = it.summary_by_column["Glicerol (°)"]
        # every factor·condition cell present, correctly paired
        self.assertEqual(col["600 W · Sem plasma"], {"mean": 36.9, "sd": 2.9, "n": 5})
        self.assertEqual(col["600 W · Com plasma"], {"mean": 20.0, "sd": 4.0, "n": 5})
        self.assertEqual(col["750 W · Sem plasma"], {"mean": 34.1, "sd": 7.3, "n": 5})
        self.assertEqual(col["900 W · Sem plasma"],
                         {"mean": 73.7, "sd": 11.2, "n": 5})
        # no phantom grouping letters from the "W" unit
        self.assertEqual(it.grouping_letters, {})
        # variation values never leaked into the data
        self.assertNotIn("Variação (%)", col)
        self.assertFalse(any("45" in str(v.get("mean")) for v in col.values()))

    def test_energy_without_sd_warns_and_keeps_structure(self):
        it = tl.interpret_table(T4_ENERGY)
        self.assertEqual(it.layout, "grouped_before_after")
        self.assertEqual(it.dropped_derived_rows, 3)
        col = it.summary_by_column["γSp (mJ/m²)"]
        self.assertEqual(col["900 W · Sem plasma"], {"mean": 0.3})
        self.assertEqual(col["900 W · Com plasma"], {"mean": 15.5})
        # no sd anywhere -> explicit warning, nothing fabricated
        self.assertFalse(any("sd" in e for e in col.values()))
        self.assertTrue(any("sem desvio" in m.lower() or "sem dp" in m.lower()
                            for m in it.messages))

    def test_end_to_end_welch_on_loaded_contact_angle(self):
        from app.core.orchestrator import analyze_summary, AnalysisOptions
        from statistics.decision_engine import DesignSpec
        it = tl.interpret_table(T3_CONTACT_ANGLE, default_n=5)
        ds = it.summary_by_column["Glicerol (°)"]
        r = analyze_summary(ds, DesignSpec(n_factors=1), AnalysisOptions())
        self.assertFalse(r.refusals)
        self.assertEqual(len(ds), 6)
        self.assertIsNotNone(r.omnibus)


class TestSummaryMisloadedAsRaw(unittest.TestCase):
    """A mean±sd sample×condition table (like Tabela 29) wrongly sent through the
    RAW path must be detectable so the UI can steer the user to Documento mode."""

    T29_XLSX = [
        ["Amostra", "Antes 20", "Após 20"],
        ["D2.A", "61,4 ±1,3b", "70,2 ±1,1a"],
        ["D3.A", "52,7 ±1,1c", "60,3 ±1,4b"],
        ["D4.A", "67,8 ±2,8a", "72,1 ±2,0a"],
    ]

    def test_cells_flagged_as_meansd(self):
        has_meansd = any(tl.cell_looks_mean_sd(str(c))
                         for r in self.T29_XLSX for c in r)
        self.assertTrue(has_meansd)

    def test_label_column_becomes_empty_group_in_raw(self):
        from data import importer as imp
        raw, used, _ = imp.rows_to_raw(self.T29_XLSX, None, "auto")
        self.assertEqual(used, "wide")
        # the text label column ('Amostra') has no numbers -> all-None group
        self.assertIn("Amostra", raw)
        self.assertTrue(all(x is None for x in raw["Amostra"]))

    def test_interpreter_reads_it_correctly(self):
        it = tl.interpret_table(self.T29_XLSX, default_n=5)
        self.assertEqual(it.kind, "summary")
        self.assertEqual(it.label_col, 0)
        self.assertEqual(it.summary_by_column["Antes 20"]["D2.A"],
                         {"mean": 61.4, "sd": 1.3, "n": 5})
        self.assertEqual(it.grouping_letters["Antes 20"]["D3.A"], "c")


class TestTransposedSummary(unittest.TestCase):
    def test_adhesive_measure_by_sample(self):
        it = tl.interpret_table(T2_ADHESIVE)
        self.assertEqual(it.kind, "summary")
        self.assertIn("PVAc", it.summary_by_column)
        self.assertEqual(it.summary_by_column["PVAc"]["Viscosidade (mPa·s)"],
                         {"mean": 4900.0, "sd": 79.0})
        self.assertEqual(it.summary_by_column["PVAc + AlCl\u2083"]["pH"],
                         {"mean": 2.86})


if __name__ == "__main__":
    unittest.main()
