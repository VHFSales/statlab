# -*- coding: utf-8 -*-
"""Gera arquivos de teste (CSV) para experimentar o StatLab.

Dados fictícios, porém plausíveis, com sementes fixas para reprodutibilidade.
Cobrem: bruto largo (ponto e vírgula decimais), bruto longo com múltiplos
experimentos, resumido simples e resumido com múltiplos experimentos.
"""
import os
import random

random.seed(42)
HERE = os.path.dirname(os.path.abspath(__file__))


def val(media, dp):
    return round(random.gauss(media, dp), 1)


# --------------------------------------------------------------------------- #
# 1) BRUTO — formato LARGO, decimal PONTO (uma coluna por grupo)
# --------------------------------------------------------------------------- #
grupos = {"Controle": (10.6, 0.4), "Trat_A": (13.9, 0.5),
          "Trat_B": (12.1, 0.4), "Trat_C": (10.8, 0.4)}
n = 6
linhas = [",".join(grupos.keys())]
for i in range(n):
    linhas.append(",".join(str(val(m, s)) for (m, s) in grupos.values()))
open(os.path.join(HERE, "1_bruto_largo_ponto.csv"), "w", encoding="utf-8").write(
    "\n".join(linhas) + "\n")

# --------------------------------------------------------------------------- #
# 2) BRUTO — formato LARGO, decimal VÍRGULA, separador ; (padrão brasileiro)
# --------------------------------------------------------------------------- #
linhas = [";".join(grupos.keys())]
for i in range(n):
    linhas.append(";".join(str(val(m, s)).replace(".", ",")
                           for (m, s) in grupos.values()))
open(os.path.join(HERE, "2_bruto_largo_virgula.csv"), "w", encoding="utf-8").write(
    "\n".join(linhas) + "\n")

# --------------------------------------------------------------------------- #
# 3) BRUTO — MÚLTIPLOS EXPERIMENTOS (formato longo: Experimento;Grupo;Valor)
#    3 experimentos de brilho (20°, 60°, 85°), 4 amostras cada, n=5
# --------------------------------------------------------------------------- #
experimentos = {
    "Brilho 20 graus": {"D2": (61.4, 1.3), "D3": (52.7, 1.1),
                        "D4": (67.8, 2.8), "D5": (71.8, 4.2)},
    "Brilho 60 graus": {"D2": (94.8, 0.3), "D3": (82.8, 0.4),
                        "D4": (96.3, 1.1), "D5": (97.5, 1.1)},
    "Brilho 85 graus": {"D2": (92.3, 1.2), "D3": (78.2, 0.9),
                        "D4": (88.4, 2.5), "D5": (92.1, 2.8)},
}
linhas = ["Experimento;Grupo;Valor"]
for exp, gs in experimentos.items():
    for g, (m, s) in gs.items():
        for _ in range(5):
            linhas.append(f"{exp};{g};{str(val(m, s)).replace('.', ',')}")
open(os.path.join(HERE, "3_bruto_multi_experimentos.csv"), "w",
     encoding="utf-8").write("\n".join(linhas) + "\n")

# --------------------------------------------------------------------------- #
# 4) RESUMIDO — simples (Grupo;Media;DP;n), decimal vírgula
# --------------------------------------------------------------------------- #
linhas = ["Grupo;Media;DP;n",
          "Controle;10,6;0,4;6",
          "Trat_A;13,9;0,5;6",
          "Trat_B;12,1;0,4;6",
          "Trat_C;10,8;0,4;6"]
open(os.path.join(HERE, "4_resumido_simples.csv"), "w", encoding="utf-8").write(
    "\n".join(linhas) + "\n")

# --------------------------------------------------------------------------- #
# 5) RESUMIDO — MÚLTIPLOS EXPERIMENTOS (Experimento;Grupo;Media;DP;n)
# --------------------------------------------------------------------------- #
linhas = ["Experimento;Grupo;Media;DP;n"]
resumo_multi = {
    "Brilho 20 graus": {"D2": (61.4, 1.3), "D3": (52.7, 1.1),
                        "D4": (67.8, 2.8), "D5": (71.8, 4.2)},
    "Brilho 60 graus": {"D2": (94.8, 0.3), "D3": (82.8, 0.4),
                        "D4": (96.3, 1.1), "D5": (97.5, 1.1)},
    "Brilho 85 graus": {"D2": (92.3, 1.2), "D3": (78.2, 0.9),
                        "D4": (88.4, 2.5), "D5": (92.1, 2.8)},
}
for exp, gs in resumo_multi.items():
    for g, (m, s) in gs.items():
        linhas.append(f"{exp};{g};{str(m).replace('.', ',')};"
                      f"{str(s).replace('.', ',')};5")
open(os.path.join(HERE, "5_resumido_multi_experimentos.csv"), "w",
     encoding="utf-8").write("\n".join(linhas) + "\n")

print("Arquivos gerados em", HERE)
for f in sorted(os.listdir(HERE)):
    if f.endswith(".csv"):
        print("  ", f)
