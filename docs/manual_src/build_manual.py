"""Gera o manual de instruções do StatLab em PDF (docs/manual_statlab.pdf).

Usa o gerador de PDF puro-stdlib (pdf_writer.py), então roda em qualquer ambiente.
"""

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from pdf_writer import Block, build_pdf  # noqa: E402

APP_URL = "https://statlabapp.streamlit.app/"

B = []
def title(t): B.append(Block(t, "title"))
def h1(t): B.append(Block(t, "h1"))
def h2(t): B.append(Block(t, "h2"))
def p(t): B.append(Block(t, "body"))
def bullet(t): B.append(Block(t, "bullet"))
def code(t): B.append(Block(t, "code"))
def small(t): B.append(Block(t, "small"))
def sp(): B.append(Block("", "spacer"))

# ---------------------------------------------------------------- Capa / intro
title("StatLab — Manual de Instruções")
p("Plataforma de análise estatística científica para laboratório.")
p("Comparação de grupos (ANOVA, Welch, Tukey, Tukey-Kramer, Games-Howell, CLD), "
  "testes t, não-paramétricos, ANOVA fatorial, dados pareados, medidas repetidas, "
  "correlação e regressão linear.")
sp()
p("Endereço do aplicativo (abra em qualquer navegador):")
code(APP_URL)
sp()
small("Este manual acompanha o StatLab v1.2. As telas podem variar ligeiramente "
      "conforme a versão. Correção estatística é a prioridade do programa: quando "
      "uma análise não é apropriada, ele informa em vez de produzir um número "
      "incorreto.")

# ---------------------------------------------------------------- 1. Acesso
h1("1. Como acessar")
p("Há duas formas de usar o StatLab:")
bullet("Pelo link, sem instalar nada: abra o endereço acima no navegador "
       "(computador ou celular).")
bullet("No seu computador (uso offline / local): instale o Python 3.9+ e rode:")
code("pip install -r requirements.txt")
code("streamlit run streamlit_app.py")
sp()
p("A tela inicial mostra, à esquerda, o MENU com duas partes: o seletor de MODO "
  "(Rápido ou Avançado) e a lista de SEÇÕES. À direita aparece o conteúdo da seção "
  "escolhida.")

# ---------------------------------------------------------------- 2. Modos
h1("2. Modos de uso")
h2("Modo Rápido (recomendado para começar)")
p("O programa orienta a análise: valida os dados, calcula a estatística descritiva, "
  "avalia os pressupostos, recomenda o método, executa o teste, faz o pós-teste "
  "quando apropriado, gera as letras de agrupamento (CLD) e o gráfico.")
h2("Modo Avançado")
p("Permite controle manual: escolher alpha, o método global (ANOVA clássica ou "
  "Welch), o pós-teste (Tukey/Tukey-Kramer ou Games-Howell), forçar o pós-teste "
  "mesmo sem significância global, usar testes não-paramétricos e ajustar opções de "
  "exibição.")

# ---------------------------------------------------------------- 3. Seções
h1("3. As seções do programa")
bullet("PROJETO: nome, pesquisador, laboratório e descrição. Também salva/reabre o "
       "projeto em arquivo (.json).")
bullet("DADOS: onde você cola os dados (brutos ou resumidos).")
bullet("DELINEAMENTO: você confirma a estrutura do experimento (nº de fatores, "
       "independência, medidas repetidas, pareamento, blocos, replicatas técnicas).")
bullet("DESCRITIVA: n, média, mediana, DP, EP, IC, mínimo, máximo, quartis, CV.")
bullet("PRESSUPOSTOS: Levene, Brown-Forsythe, Shapiro-Wilk (nos resíduos), razão de "
       "variâncias e a nota sobre independência.")
bullet("ANÁLISE: executa o teste global (ANOVA/Welch) e, quando cabível, o "
       "pós-teste. Mostra F, p, tamanho de efeito e a tabela com letras.")
bullet("PÓS-TESTES: a tabela detalhada de comparações par a par (Tukey, "
       "Games-Howell, Dunn...).")
bullet("OUTLIERS: diagnóstico (IQR, Grubbs) e exclusão registrada, com comparação "
       "antes/depois. Nunca exclui automaticamente.")
bullet("GRÁFICOS: boxplot, média ± DP/EP/IC, Q-Q plot e resíduos vs. ajustados, com "
       "as letras de agrupamento.")
bullet("FATORIAL: ANOVA de duas vias (com interação), balanceada ou desbalanceada "
       "(tipos de SS I/II/III).")
bullet("PAREADO: teste t pareado ou Wilcoxon (duas condições na mesma unidade).")
bullet("MEDIDAS REPETIDAS: Friedman e pós-teste de Nemenyi (3+ condições "
       "relacionadas).")
bullet("CORRELAÇÃO: Pearson e Spearman, com intervalo de confiança.")
bullet("REGRESSÃO: regressão linear simples e múltipla (MQO).")
bullet("LOTE: analisa várias variáveis de uma vez, com aviso de multiplicidade e "
       "correção opcional (Holm, Benjamini-Hochberg, etc.).")
bullet("RELATÓRIO: gera um relatório completo em HTML.")
bullet("EXPORTAR: baixa o Resumo (CSV), o Excel, o resultado e a configuração de "
       "reprodução.")

# ---------------------------------------------------------------- 4. Entrada
h1("4. Como inserir os dados")
h2("Dados brutos (recomendado)")
p("Na seção DADOS, deixe 'Dados brutos'. Cole no formato LARGO (uma coluna por "
  "grupo). As colunas podem ser separadas por TAB (ao copiar do Excel) ou por "
  "vírgula. Exemplo:")
code("Controle   Trat_A   Trat_B")
code("10.2       13.5     12.1")
code("10.8       14.0     11.8")
code("11.1       13.8     12.5")
code("10.6       14.2     12.0")
p("Também aceita o formato LONGO (duas colunas: Grupo e Valor). Deixe o Formato em "
  "'auto-detectar' e clique em 'Carregar dados brutos'. Uma prévia aparece abaixo.")
h2("Dados resumidos")
p("Se você só tem média, desvio padrão e n por grupo, escolha 'Estatísticas "
  "resumidas' e informe uma linha por grupo: Grupo, Média, DP, n. Atenção: sem o n, "
  "a ANOVA e o Tukey não podem ser calculados.")
sp()
small("Células vazias nunca são convertidas em zero; valores ausentes são contados "
      "e descartados de forma explícita.")

# ---------------------------------------------------------------- 5. TUKEY passo a passo
h1("5. Passo a passo: ANOVA + Tukey")
p("No StatLab, o Tukey é o pós-teste da ANOVA: ele roda logo após uma ANOVA "
  "significativa (fluxo cientificamente correto).")
h2("Passo 1 — DADOS")
p("Cole seus grupos (formato largo) e clique em 'Carregar dados brutos'.")
h2("Passo 2 — DELINEAMENTO")
p("Confirme: Quantos fatores? = 1; 'Os grupos são independentes?' marcado; deixe "
  "medidas repetidas, pareado e blocos desmarcados. Isso caracteriza uma ANOVA de "
  "uma via com grupos independentes.")
h2("Passo 3 — ANÁLISE")
p("Deixe alpha = 0,05 e clique em 'Analisar'. O programa executa a ANOVA e, se ela "
  "for significativa, executa o Tukey HSD automaticamente. A tela mostra F, p, o "
  "tamanho de efeito e a tabela resumo com as LETRAS de agrupamento (a, b, c...).")
h2("Passo 4 — PÓS-TESTES")
p("Abra a seção PÓS-TESTES para ver a tabela completa do Tukey: para cada par de "
  "grupos, a diferença entre médias, o intervalo de confiança simultâneo, o p "
  "ajustado e se a diferença é significativa.")
sp()
h2("Observações importantes sobre o Tukey")
bullet("Balanceado x desbalanceado: com n igual em todos os grupos, o método é "
       "Tukey HSD; com n diferente, o programa usa Tukey-Kramer automaticamente (a "
       "formulação correta para n desigual).")
bullet("Variâncias muito diferentes: o programa pode recomendar ANOVA de Welch; "
       "nesse caso o pós-teste apropriado é Games-Howell, não Tukey.")
bullet("Modo Rápido: se a ANOVA não for significativa, o Tukey não roda "
       "automaticamente (é a prática recomendada). Para executá-lo mesmo assim, use "
       "o Modo Avançado e marque a opção de forçar o pós-teste.")

# ---------------------------------------------------------------- 6. Letras
h1("6. Entendendo as letras de agrupamento (CLD)")
p("As letras resumem quais grupos diferem entre si. A regra é:")
bullet("Grupos que compartilham pelo menos uma letra NÃO diferem significativamente.")
bullet("Grupos que não compartilham nenhuma letra diferem significativamente.")
p("Exemplo: A=a, B=b, C=c, D=c significa que C e D são estatisticamente "
  "semelhantes (mesma letra 'c'), enquanto A, B e o par C/D diferem entre si.")
sp()
small("As letras são símbolos de agrupamento, não um ranking. 'a' não significa "
      "'melhor' nem 'maior' — é apenas uma etiqueta. Por convenção, 'a' costuma ser "
      "atribuída ao grupo de maior média, mas isso é só visual.")

# ---------------------------------------------------------------- 7. Interpretacao
h1("7. Como interpretar os resultados")
bullet("p < alpha (ex.: 0,05): há evidência estatística de diferença entre pelo "
       "menos duas médias. NÃO diz sozinho quais grupos diferem — para isso, olhe o "
       "Tukey e as letras.")
bullet("p >= alpha: não há evidência suficiente para rejeitar a igualdade. Isso não "
       "prova que as médias são iguais.")
bullet("Tamanho de efeito (eta² e omega²): magnitude do efeito. Significância "
       "estatística não é o mesmo que importância prática.")
bullet("Diferença estatística não implica causalidade — isso depende do "
       "delineamento do experimento.")

# ---------------------------------------------------------------- 8. Graficos/relatorio
h1("8. Gráficos, relatório e exportação")
bullet("GRÁFICOS: escolha o tipo (boxplot, média ± DP/EP/IC, Q-Q, resíduos). As "
       "letras de agrupamento aparecem sobre os grupos.")
bullet("RELATÓRIO: gera um relatório em HTML com descritiva, ANOVA/Welch, tamanho "
       "de efeito, pós-teste, letras e a trilha de auditoria; use o botão de "
       "download.")
bullet("EXPORTAR: baixe o Resumo em CSV, o arquivo Excel, o resultado completo e a "
       "configuração de reprodução (que permite refazer a análise idêntica).")

# ---------------------------------------------------------------- 9. Outros testes
h1("9. Escolhendo o teste certo (resumo)")
bullet("2 grupos independentes: teste t (Student ou Welch).")
bullet("3+ grupos independentes, 1 fator: ANOVA de uma via -> Tukey/Tukey-Kramer; "
       "ou Welch -> Games-Howell se as variâncias diferem muito.")
bullet("2 fatores: ANOVA de duas vias (seção FATORIAL).")
bullet("Duas condições na mesma unidade (antes/depois): teste t pareado ou "
       "Wilcoxon (seção PAREADO).")
bullet("3+ condições na mesma unidade: Friedman -> Nemenyi (MEDIDAS REPETIDAS).")
bullet("Associação entre duas variáveis: Correlação (Pearson/Spearman).")
bullet("Prever uma variável a partir de outra(s): Regressão linear.")
bullet("Não-paramétrico (Kruskal-Wallis, Mann-Whitney, Wilcoxon, Friedman): "
       "escolha deliberada, no Modo Avançado. O programa nunca troca para "
       "não-paramétrico automaticamente por causa de um teste de normalidade.")

# ---------------------------------------------------------------- 10. Problemas
h1("10. Perguntas frequentes e problemas")
bullet("O Tukey não apareceu: no Modo Rápido, ele só roda se a ANOVA for "
       "significativa. Veja o aviso na seção ANÁLISE ou use o Modo Avançado.")
bullet("O programa recusou a análise: leia a mensagem. Ele recusa quando o "
       "delineamento não corresponde ao método (ex.: 2 fatores tratados como uma "
       "via, dados resumidos sem n, células vazias no fatorial).")
bullet("Dados não carregaram: confira o separador (TAB ou vírgula) e se cada grupo "
       "tem o cabeçalho. Use a prévia para conferir.")
bullet("O app demorou a abrir: o Streamlit Cloud 'adormece' apps sem uso; a "
       "primeira abertura pode levar alguns segundos.")

sp()
small("StatLab — software livre para uso científico. Repositório: "
      "github.com/VHFSales/statlab. Consulte docs/methodology.md para as fórmulas e "
      "referências metodológicas de cada teste.")

out = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                   "manual_statlab.pdf")
build_pdf(B, out, footer="StatLab — Manual de Instruções")
print("PDF gerado:", out)
