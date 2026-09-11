# Exemplos

## `exemplo_relatorio_statlab.html`

Relatório de análise estatística gerado pelo StatLab a partir de um conjunto de
dados de demonstração (4 grupos: Controle + 3 tratamentos). Contém estatística
descritiva, tabela ANOVA, tamanho de efeito, pós-teste de Tukey HSD, Compact Letter
Display e a trilha de auditoria/reprodutibilidade.

### Como abrir o relatório formatado

O arquivo é um HTML autocontido (HTML + CSS embutido) — abre em qualquer navegador.

**Opção A — pelo GitHub (um clique, sem baixar nada):**
Use o visualizador htmlpreview. Cole este link no navegador
(troque `main` pelo branch, se necessário):

```
https://htmlpreview.github.io/?https://github.com/VHFSales/statlab/blob/main/examples/exemplo_relatorio_statlab.html
```

**Opção B — baixando o arquivo:**
1. Abra o arquivo no GitHub e clique em **Download raw file** (ou **Raw** → salvar
   como `.html`).
2. Dê um duplo-clique no arquivo salvo: ele abre no seu navegador padrão.

**Opção C — clonando o repositório:**
```bash
git clone https://github.com/VHFSales/statlab.git
# abra examples/exemplo_relatorio_statlab.html no navegador
```

### Como gerar o seu próprio relatório

```python
from app.core.orchestrator import analyze_raw, AnalysisOptions
from statistics.decision_engine import DesignSpec
from reports.pdf_report import save_html_report

dados = {"Controle": [10.2, 10.8, 11.1, 10.6, 10.4],
         "Trat_A":   [13.5, 14.0, 13.8, 14.2, 13.9]}
r = analyze_raw(dados, DesignSpec(n_factors=1), AnalysisOptions())
save_html_report(r, "meu_relatorio.html", project_meta={"Nome": "Meu estudo"})
```
