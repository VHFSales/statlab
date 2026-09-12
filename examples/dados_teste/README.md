# Dados de teste para o StatLab

Arquivos fictícios (porém realistas) para você experimentar o aplicativo. Baixe o
que quiser e envie na seção **DADOS**. Todos usam `;` como separador de colunas.

| Arquivo | Modo no app | O que testa |
|---|---|---|
| `1_bruto_largo_ponto.csv` | Dados brutos | 4 grupos, decimal com **ponto** |
| `2_bruto_largo_virgula.csv` | Dados brutos | 4 grupos, decimal com **vírgula** (padrão BR) |
| `3_bruto_multi_experimentos.csv` | Dados brutos | **3 experimentos** num só arquivo (coluna Experimento) |
| `4_resumido_simples.csv` | Estatísticas resumidas | 4 grupos com Média/DP/n |
| `5_resumido_multi_experimentos.csv` | Estatísticas resumidas | **3 experimentos** resumidos num só arquivo |

## Como usar

1. Baixe um arquivo (no GitHub: abra o arquivo → botão **Download raw file**).
2. No app, seção **DADOS**, escolha o modo indicado na tabela acima.
3. Clique em **Enviar um arquivo** e selecione o CSV.
4. Se o arquivo tiver vários experimentos (3 e 5), escolha qual analisar no seletor.
5. Vá em **DELINEAMENTO** (1 fator, grupos independentes) → **ANÁLISE**.

> Observação: são dados de demonstração. Nos arquivos com múltiplos experimentos,
> as variâncias entre grupos diferem bastante, então o app costuma recomendar
> **ANOVA de Welch → Games-Howell** (em vez de ANOVA clássica → Tukey) — que é o
> comportamento estatisticamente correto quando as variâncias são desiguais.
