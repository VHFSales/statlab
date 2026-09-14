"""Manual de uso do StatLab — escrito para quem NÃO entende de estatística.

Este módulo é a seção "MANUAL / AJUDA" do aplicativo. O conteúdo fica em estruturas
de dados (``QUICK_START``, ``CONCEITOS``, ``SECOES``, ``GLOSSARIO``, ``FLUXOGRAMA``,
``FAQ``) para que a interface apenas o renderize e os testes possam verificar que
TODAS as seções do app estão cobertas.

Princípio de escrita: linguagem simples, passo a passo numerado, sempre respondendo
"o que é isto?", "para que serve?" e "como faço?". Nada de jargão sem explicação.
"""

from __future__ import annotations

from typing import Dict, List


# --------------------------------------------------------------------------- #
# Introdução em linguagem simples
# --------------------------------------------------------------------------- #
INTRO = (
    "O **StatLab** compara grupos e diz se as diferenças que você vê nos números "
    "são **reais** (provavelmente verdadeiras) ou se **podem ser apenas acaso**. "
    "Você não precisa saber estatística: o programa **escolhe o teste certo** para "
    "os seus dados, executa e **explica o resultado em português**. Este manual "
    "mostra, passo a passo, o que fazer em cada tela."
)

# A regra de ouro sobre significância, escrita para leigos.
COMO_LER_P = (
    "Quase todo resultado traz um número chamado **p** (\"valor-p\"). Pense nele "
    "como a chance de a diferença observada ser **só coincidência**:\n\n"
    "- **p menor que 0,05** → a diferença é considerada **estatisticamente "
    "significativa** (provavelmente real). \n"
    "- **p maior que 0,05** → **não há evidência suficiente** de diferença (pode "
    "ser acaso). \n\n"
    "O corte 0,05 (chamado **α**, alfa) é uma convenção; você pode mudá-lo na tela "
    "de Análise. **Atenção:** \"não significativo\" NÃO prova que os grupos são "
    "iguais — apenas que os dados não bastaram para afirmar que diferem."
)


# --------------------------------------------------------------------------- #
# Guia rápido (o caminho mais comum, do zero ao resultado)
# --------------------------------------------------------------------------- #
QUICK_START: List[str] = [
    "**Abra a seção DADOS** (menu à esquerda) e informe seus números — você pode "
    "enviar um arquivo (Excel, CSV, PDF ou Word) ou colar a tabela.",
    "**Confira a prévia**: veja se cada grupo (coluna) tem os valores certos e se "
    "os números foram lidos corretamente (vírgula/ponto decimal).",
    "**Vá em DELINEAMENTO** e confirme a estrutura do experimento (na dúvida, "
    "deixe o padrão: 1 fator, grupos independentes).",
    "**Vá em ANÁLISE** e clique em **Analisar**. O programa escolhe o teste "
    "adequado sozinho e mostra o resultado.",
    "**Leia o RESULTADO**: veja o valor-p (diferença real ou acaso?) e, se houver "
    "diferença, as **letras** que dizem quais grupos diferem de quais.",
    "**Opcional:** veja GRÁFICOS, gere um RELATÓRIO em HTML ou EXPORTE para "
    "Excel/CSV.",
]


# --------------------------------------------------------------------------- #
# Conceitos essenciais, explicados sem jargão
# --------------------------------------------------------------------------- #
CONCEITOS: List[Dict[str, str]] = [
    {
        "titulo": "Grupo",
        "texto": "Uma categoria que você quer comparar. Ex.: \"Sem tratamento\", "
                 "\"600 W\", \"750 W\". No formato de tabela, normalmente cada "
                 "**coluna** é um grupo (ou uma coluna diz a qual grupo cada linha "
                 "pertence).",
    },
    {
        "titulo": "Observação / repetição (n)",
        "texto": "Cada medida individual dentro de um grupo. Se você mediu 5 corpos "
                 "de prova por condição, o **n** daquele grupo é 5. Mais repetições "
                 "= mais confiança no resultado.",
    },
    {
        "titulo": "Média",
        "texto": "O valor \"típico\" do grupo: soma dos valores dividida pelo "
                 "número de valores.",
    },
    {
        "titulo": "Desvio padrão (DP)",
        "texto": "O quanto os valores variam em torno da média. DP pequeno = grupo "
                 "homogêneo; DP grande = valores espalhados.",
    },
    {
        "titulo": "Valor-p",
        "texto": "A chance de a diferença observada ser apenas acaso. Abaixo de "
                 "0,05 costuma-se dizer que a diferença é \"significativa\". "
                 "(Veja \"Como ler o valor-p\" no topo do manual.)",
    },
    {
        "titulo": "α (alfa)",
        "texto": "O limite que você escolhe para decidir o que é \"significativo\" "
                 "(padrão 0,05 = 5%). É o risco que você aceita de gritar "
                 "\"diferença!\" quando na verdade foi acaso.",
    },
    {
        "titulo": "Teste global (omnibus)",
        "texto": "A primeira pergunta: \"existe ALGUMA diferença entre os grupos?\" "
                 "A ANOVA responde isso. Ela NÃO diz quais grupos diferem — para "
                 "isso serve o pós-teste.",
    },
    {
        "titulo": "Pós-teste (comparações par a par)",
        "texto": "Depois de o teste global achar diferença, o pós-teste (Tukey, "
                 "Games-Howell ou Dunn) descobre EXATAMENTE quais pares de grupos "
                 "diferem entre si.",
    },
    {
        "titulo": "Letras de agrupamento (CLD)",
        "texto": "Um resumo visual: grupos que **compartilham uma letra** NÃO "
                 "diferem significativamente; grupos **sem letra em comum** "
                 "diferem. Não é um ranking — é um mapa de \"quem é igual a quem\".",
    },
    {
        "titulo": "Variância homogênea x heterogênea",
        "texto": "Se todos os grupos variam de forma parecida (DPs próximos), as "
                 "variâncias são \"homogêneas\" e usa-se ANOVA clássica + Tukey. Se "
                 "variam muito diferente, usa-se **Welch + Games-Howell**, que são "
                 "robustos a isso. O StatLab decide automaticamente.",
    },
]


# --------------------------------------------------------------------------- #
# Passo a passo de CADA seção do menu (chave = nome exato no menu do app)
# --------------------------------------------------------------------------- #
# Cada seção: o_que (o que é/para que serve) + passos (lista numerada) +
# dicas (lista de avisos/observações úteis).
SECOES: Dict[str, Dict[str, object]] = {
    "PROJETO": {
        "o_que": "Guarda a identificação do seu estudo (nome, pesquisador, "
                 "laboratório, descrição). Esses dados NÃO mudam a estatística; "
                 "servem para organizar e para constar no relatório. Aqui também "
                 "você salva e reabre um projeto inteiro.",
        "passos": [
            "Preencha Nome do projeto, Pesquisador, Laboratório e Descrição "
            "(todos opcionais).",
            "Para guardar tudo, clique em **Baixar projeto (.json)** — o arquivo "
            "contém os metadados, os dados, o delineamento e o último resultado.",
            "Para continuar depois, use **Reabrir projeto (.json)** e selecione o "
            "arquivo salvo.",
        ],
        "dicas": [
            "O arquivo .json é a forma de não perder seu trabalho: guarde-o no seu "
            "computador.",
        ],
    },
    "DADOS": {
        "o_que": "É por onde você informa seus números. Há três modos: (1) **Dados "
                 "brutos** = os valores individuais medidos (o recomendado); (2) "
                 "**Estatísticas resumidas** = quando você só tem Média, DP e n de "
                 "cada grupo; (3) **Documento** = enviar uma tese/artigo em PDF ou "
                 "Word para o programa achar as tabelas.",
        "passos": [
            "Escolha o tipo de dados no topo da tela.",
            "**Dados brutos → Opção 1 (arquivo):** clique em enviar e escolha um "
            "Excel, CSV, PDF ou Word. O programa lê a tabela e detecta se o decimal "
            "é vírgula ou ponto.",
            "**Dados brutos → Opção 2 (colar):** cole a tabela. Formato **largo** = "
            "uma coluna por grupo; formato **longo** = duas colunas (Grupo | Valor).",
            "**Estatísticas resumidas:** informe, para cada grupo, a Média, o DP e "
            "o n. Sem o DP e o n não é possível fazer o teste.",
            "**Documento:** envie o PDF/Word, clique em varrer, escolha a tabela "
            "detectada e confirme para carregar.",
            "Confira a **prévia** dos valores antes de seguir para a análise.",
        ],
        "dicas": [
            "Se o decimal for vírgula, ao colar separe as colunas por **ponto e "
            "vírgula (;)** ou **Tab** para não confundir com o decimal.",
            "Células vazias NUNCA viram zero — são contadas como ausentes.",
            "Se um arquivo tiver uma coluna de **Experimento/Ensaio** com vários "
            "valores, o programa separa os experimentos e você escolhe qual analisar.",
            "Tabela de **média ± DP** (ex.: \"61,4 ± 1,3\") é uma tabela RESUMIDA — "
            "use o modo Documento ou Estatísticas resumidas, não \"Dados brutos\".",
            "Fotos/imagens e gráficos NÃO são aceitos: extrair números de imagem é "
            "inseguro e o programa não inventa dados.",
        ],
    },
    "DELINEAMENTO": {
        "o_que": "Descreve a ESTRUTURA do seu experimento. É o que permite ao "
                 "programa escolher o teste certo e evitar erros graves (como "
                 "tratar medidas repetidas como se fossem grupos independentes).",
        "passos": [
            "Informe **quantos fatores** você está variando (ex.: só a potência = "
            "1 fator).",
            "Marque **se os grupos são independentes** (amostras diferentes em cada "
            "grupo). Deixe marcado na dúvida do caso mais comum.",
            "Marque **medidas repetidas / pareado / blocos** apenas se a MESMA "
            "unidade foi medida em várias condições (ex.: antes e depois no mesmo "
            "corpo de prova).",
            "Confirme se cada observação é uma **unidade independente** (evita "
            "pseudorreplicação).",
        ],
        "dicas": [
            "Independência depende do DELINEAMENTO, não dos números: o programa não "
            "consegue adivinhá-la sozinho — por isso ele pergunta.",
            "Caso simples e mais comum: 1 fator, grupos independentes, o resto "
            "desmarcado.",
        ],
    },
    "DESCRITIVA": {
        "o_que": "Mostra o \"retrato\" de cada grupo: média, mediana, desvio "
                 "padrão, erro padrão, intervalo de confiança, mínimo, máximo, "
                 "quartis, amplitude e coeficiente de variação.",
        "passos": [
            "Rode a análise antes (seção ANÁLISE).",
            "Volte aqui para ver a tabela com um resumo numérico de cada grupo.",
        ],
        "dicas": [
            "Use esta tela para checar se os dados fazem sentido (ex.: um grupo com "
            "DP enorme pode indicar erro de digitação ou um outlier).",
        ],
    },
    "PRESSUPOSTOS": {
        "o_que": "Verifica as \"condições\" que os testes assumem: se os grupos "
                 "variam de forma parecida (Levene, Brown-Forsythe, razão de "
                 "variâncias) e se os dados seguem aproximadamente a curva normal "
                 "(Shapiro-Wilk nos resíduos).",
        "passos": [
            "Rode a análise antes.",
            "Leia os p-valores dos testes: p pequeno em Levene/Brown-Forsythe "
            "sugere variâncias diferentes; p pequeno em Shapiro sugere fuga da "
            "normalidade.",
        ],
        "dicas": [
            "Nenhum desses testes é uma regra absoluta — o programa os usa em "
            "conjunto para escolher o método, e você pode inspecionar tudo aqui.",
            "Se as variâncias diferem muito, o programa já usa Welch/Games-Howell "
            "automaticamente.",
        ],
    },
    "ANÁLISE": {
        "o_que": "O coração do programa: executa o teste e mostra o resultado "
                 "principal. Ele **decide automaticamente** entre ANOVA clássica e "
                 "Welch (e o pós-teste correspondente) com base nos seus dados.",
        "passos": [
            "Defina o **α** (padrão 0,05), o **nível de confiança** do IC (padrão "
            "95%) e as casas decimais.",
            "Clique em **Analisar**.",
            "Leia o RESULTADO: o método escolhido, o valor de F, o **valor-p** e, se "
            "houver diferença, as **letras** de agrupamento.",
            "Se aparecer uma recusa em vermelho, leia a mensagem — ela diz o que "
            "corrigir nos dados (ex.: faltou o n, ou entrou texto numa coluna).",
        ],
        "dicas": [
            "Modo **Rápido** faz tudo sozinho. Modo **Avançado** deixa você forçar "
            "o método (ANOVA/Welch), forçar o pós-teste (Tukey/Games-Howell) ou "
            "escolher um teste **não-paramétrico** (Kruskal-Wallis → Dunn).",
            "No modo rápido, o pós-teste só roda se o teste global for "
            "significativo (fluxo cientificamente correto).",
            "O programa NUNCA fabrica dados nem escolhe o não-paramétrico sozinho a "
            "partir de um teste de normalidade.",
        ],
    },
    "PÓS-TESTES": {
        "o_que": "Mostra QUAIS pares de grupos diferem entre si, depois que o teste "
                 "global achou alguma diferença. Usa Tukey (variâncias iguais), "
                 "Games-Howell (variâncias desiguais) ou Dunn (não-paramétrico).",
        "passos": [
            "Rode a análise antes.",
            "Leia a tabela par a par: a coluna **p ajustado** e **Signif.** dizem "
            "se aquele par específico difere.",
        ],
        "dicas": [
            "Com apenas **dois grupos** não há pós-teste par a par — a própria "
            "comparação é o teste t, mostrado aqui.",
            "O \"p ajustado\" já corrige o fato de você fazer várias comparações de "
            "uma vez (senão a chance de falso positivo cresceria).",
        ],
    },
    "OUTLIERS": {
        "o_que": "Sinaliza valores atípicos (muito fora do padrão do grupo) pelo "
                 "método IQR (cerca) ou Grubbs. Serve para você INVESTIGAR — nunca "
                 "para excluir automaticamente.",
        "passos": [
            "Precisa de **dados brutos** (valores individuais).",
            "Escolha o método (IQR ou Grubbs) e veja os candidatos sinalizados.",
            "Se decidir excluir algum, selecione-o, **escreva o motivo "
            "(obrigatório)** e clique em excluir e comparar.",
            "Compare o resultado ANTES e DEPOIS da exclusão na tabela que aparece.",
        ],
        "dicas": [
            "Excluir dados é uma decisão científica sua e deve ser justificada — o "
            "programa apenas registra (valor, grupo, motivo, data) para "
            "transparência.",
            "Um valor atípico pode ser um erro de medição OU um achado real. Não "
            "exclua só porque \"ficou feio\".",
        ],
    },
    "GRÁFICOS": {
        "o_que": "Gera figuras científicas: boxplot, gráficos de média com barras "
                 "de erro (DP, EP ou IC) e diagnósticos (Q-Q dos resíduos, resíduos "
                 "vs. ajustados).",
        "passos": [
            "Rode a análise antes.",
            "Escolha o tipo de gráfico no seletor.",
            "A figura aparece na tela; use-a no seu relatório/artigo.",
        ],
        "dicas": [
            "Boxplot, Q-Q e resíduos precisam dos **dados brutos** (não funcionam "
            "só com estatísticas resumidas).",
            "As **letras** de agrupamento aparecem sobre as barras/caixas quando "
            "há pós-teste.",
        ],
    },
    "FATORIAL": {
        "o_que": "ANOVA de duas vias: quando você tem **dois fatores** ao mesmo "
                 "tempo (ex.: Potência e Material) e quer ver o efeito de cada um e "
                 "da **interação** entre eles.",
        "passos": [
            "Cole os dados em três colunas: **Fator A | Fator B | Valor**.",
            "Escolha o tipo de soma de quadrados (na dúvida, **Tipo II**).",
            "Rode e leia os efeitos: A, B e a interação A×B, cada um com seu p.",
        ],
        "dicas": [
            "Todas as combinações de níveis dos dois fatores precisam existir nos "
            "dados.",
            "Aceita delineamentos balanceados e desbalanceados.",
            "Interação significativa = o efeito de um fator DEPENDE do nível do "
            "outro (interprete os efeitos principais com cautela).",
        ],
    },
    "PAREADO": {
        "o_que": "Compara **duas condições medidas na MESMA unidade** (ex.: antes e "
                 "depois no mesmo corpo de prova). É o teste t pareado.",
        "passos": [
            "Dê nome às duas condições (ex.: Antes, Depois).",
            "Cole **duas colunas alinhadas par a par** (cada linha é a mesma "
            "unidade nas duas condições).",
            "Rode e leia a média das diferenças, o t, o p e o intervalo de "
            "confiança.",
        ],
        "dicas": [
            "NÃO use dados pareados como se fossem grupos independentes — isso "
            "muda o teste e pode dar conclusão errada.",
            "No modo Avançado há a opção não-paramétrica (Wilcoxon).",
        ],
    },
    "MEDIDAS REPETIDAS": {
        "o_que": "Para **3 ou mais condições** medidas na mesma unidade (ex.: a "
                 "mesma amostra medida em 3 tempos). Usa Friedman (global) e "
                 "Nemenyi (pós-teste). É não-paramétrico.",
        "passos": [
            "Cole uma tabela onde **cada linha é um sujeito/bloco** e **cada coluna "
            "é uma condição**.",
            "Rode e leia o resultado global (Friedman) e, se significativo, as "
            "comparações par a par (Nemenyi) com letras.",
        ],
        "dicas": [
            "Todas as condições precisam ter sido medidas em todos os blocos "
            "(delineamento completo).",
        ],
    },
    "CORRELAÇÃO": {
        "o_que": "Mede se **duas variáveis andam juntas** (ex.: temperatura e "
                 "resistência). Pearson mede relação **linear**; Spearman mede "
                 "relação **monotônica** (por postos).",
        "passos": [
            "Dê nome às duas variáveis (X e Y).",
            "Cole **duas colunas alinhadas** (uma medida de cada variável por "
            "unidade).",
            "Escolha Pearson ou Spearman e rode.",
            "Leia o **r** (de −1 a +1) e o p. r perto de ±1 = associação forte; "
            "perto de 0 = fraca.",
        ],
        "dicas": [
            "**Correlação não é causa!** Duas coisas andarem juntas não prova que "
            "uma causa a outra.",
            "Use Spearman se a relação não for uma reta ou houver valores extremos.",
        ],
    },
    "REGRESSÃO": {
        "o_que": "Ajusta uma equação que **prevê uma variável resposta (y)** a "
                 "partir de uma ou mais variáveis preditoras (x). Uma preditora = "
                 "regressão simples; várias = múltipla.",
        "passos": [
            "Cole a tabela com a **resposta (y) na ÚLTIMA coluna** e os preditores "
            "nas colunas anteriores.",
            "Escolha o nível de confiança e rode.",
            "Leia os coeficientes (o efeito de cada preditor), o p de cada um e o "
            "**R²** (quanto do y é explicado pelo modelo).",
        ],
        "dicas": [
            "O intercepto é incluído automaticamente.",
            "R² perto de 1 = o modelo explica bem; perto de 0 = explica pouco.",
        ],
    },
    "LOTE": {
        "o_que": "Analisa **várias variáveis de uma vez** com o mesmo delineamento "
                 "(ex.: comparar os grupos em Peso, Altura e pH simultaneamente). "
                 "Cada variável recebe seu próprio teste.",
        "passos": [
            "Cole uma tabela: primeira coluna **Grupo**, seguida de uma coluna por "
            "variável (Grupo | Var1 | Var2 | ...).",
            "Se quiser, escolha uma **correção de multiplicidade entre variáveis** "
            "(ex.: Holm, Benjamini-Hochberg).",
            "Rode e leia a tabela consolidada: método, p e p ajustado de cada "
            "variável.",
        ],
        "dicas": [
            "Testar muitas variáveis aumenta a chance de falso positivo; a correção "
            "de multiplicidade compensa isso.",
        ],
    },
    "RELATÓRIO": {
        "o_que": "Gera um relatório completo em **HTML** (abre em qualquer "
                 "navegador) com a descritiva, o teste, o pós-teste, as letras e a "
                 "trilha de reprodutibilidade.",
        "passos": [
            "Rode a análise antes.",
            "Clique em **Baixar relatório HTML** (ou veja a prévia na tela).",
        ],
        "dicas": [
            "Bom para anexar ao trabalho ou enviar ao orientador.",
        ],
    },
    "EXPORTAR": {
        "o_que": "Salva os resultados em vários formatos: **CSV**, **Excel "
                 "(.xlsx)**, além de arquivos JSON com a configuração de "
                 "reprodução e o resultado completo.",
        "passos": [
            "Rode a análise antes.",
            "Escolha o formato desejado e baixe.",
        ],
        "dicas": [
            "A **configuração de reprodução (JSON)** contém dados, α, método, "
            "delineamento e versões — suficiente para refazer a análise "
            "identicamente no futuro.",
        ],
    },
}


# --------------------------------------------------------------------------- #
# "Qual seção eu uso?" — um guia de decisão simples
# --------------------------------------------------------------------------- #
FLUXOGRAMA: List[Dict[str, str]] = [
    {"pergunta": "Comparar 2 ou mais grupos INDEPENDENTES (amostras diferentes)?",
     "va_para": "DADOS → DELINEAMENTO → ANÁLISE (ANOVA/Welch, com Tukey/Games-Howell)"},
    {"pergunta": "Comparar 2 condições na MESMA unidade (antes/depois)?",
     "va_para": "PAREADO"},
    {"pergunta": "Comparar 3+ condições na MESMA unidade (vários tempos)?",
     "va_para": "MEDIDAS REPETIDAS"},
    {"pergunta": "Tenho 2 fatores ao mesmo tempo (ex.: Potência e Material)?",
     "va_para": "FATORIAL"},
    {"pergunta": "Quero ver se duas variáveis andam juntas?",
     "va_para": "CORRELAÇÃO"},
    {"pergunta": "Quero prever uma variável a partir de outras?",
     "va_para": "REGRESSÃO"},
    {"pergunta": "Tenho várias variáveis para comparar de uma vez?",
     "va_para": "LOTE"},
    {"pergunta": "Quero só um resumo numérico dos grupos?",
     "va_para": "DESCRITIVA (após rodar a ANÁLISE)"},
]


# --------------------------------------------------------------------------- #
# Glossário visual (complementa o glossário curto do menu lateral)
# --------------------------------------------------------------------------- #
GLOSSARIO: Dict[str, str] = {
    "Média": "Valor típico: soma dos valores dividida por n.",
    "Desvio padrão (DP)": "O quanto os valores se espalham em torno da média.",
    "Erro padrão (EP)": "Incerteza da média = DP dividido pela raiz de n.",
    "Intervalo de confiança (IC)": "Faixa onde a verdadeira média provavelmente "
                                   "está (ex.: IC 95%).",
    "F": "Número que compara a variação ENTRE grupos com a variação DENTRO dos "
         "grupos. F grande sugere diferença.",
    "Valor-p": "Chance de a diferença ser só acaso. Abaixo de α (0,05) → "
               "significativa.",
    "α (alfa)": "Limite que você aceita para chamar algo de significativo "
                "(padrão 0,05).",
    "ANOVA": "Teste global: há alguma diferença entre as médias? Não diz quais.",
    "Welch": "Versão da ANOVA que funciona quando os grupos variam de forma "
             "diferente.",
    "Tukey / Tukey-Kramer": "Pós-teste que compara todos os pares (variâncias "
                            "iguais; Tukey-Kramer para n desiguais).",
    "Games-Howell": "Pós-teste par a par quando as variâncias/tamanhos são "
                    "desiguais.",
    "Kruskal-Wallis / Dunn": "Versão não-paramétrica (por postos) do teste global "
                             "e do pós-teste.",
    "Letras (CLD)": "Grupos com uma letra em comum NÃO diferem; sem letra em comum, "
                    "diferem. Não é ranking.",
    "η² / ω²": "Tamanho do efeito: o quão GRANDE é a diferença (não só se ela "
               "existe). ω² é menos enviesado.",
    "R²": "Na regressão, a fração da resposta explicada pelo modelo (0 a 1).",
    "Outlier": "Valor atípico, muito fora do padrão do grupo.",
}


# --------------------------------------------------------------------------- #
# Perguntas frequentes
# --------------------------------------------------------------------------- #
FAQ: List[Dict[str, str]] = [
    {"p": "Rodei a análise mas NÃO apareceram as letras (a, b, c). Por quê?",
     "r": "Há três motivos possíveis: (1) o teste global NÃO foi significativo "
          "(p ≥ 0,05) — como não há diferença entre os grupos, todos teriam a mesma "
          "letra, então no modo Rápido o pós-teste nem roda; (2) você tem apenas "
          "2 grupos — aí a comparação é o teste t e não há letras par a par; (3) a "
          "análise não foi concluída. Para forçar as letras mesmo sem significância, "
          "use o modo Avançado e marque 'Executar pós-teste mesmo se o teste global "
          "não for significativo'."},
    {"p": "Tenho os dados já tratados (Média, DP e n). Onde coloco?",
     "r": "Na seção DADOS, escolha 'Estatísticas resumidas (Média, DP, n)'. Você "
          "pode colar uma linha por grupo no formato 'Grupo, Média, DP, n' ou enviar "
          "um arquivo com essas colunas. Não precisa dos valores individuais."},
    {"p": "O que significa \"não significativo\"?",
     "r": "Que os dados não deram evidência suficiente de diferença. NÃO prova que "
          "os grupos são iguais — pode faltar dados (n pequeno)."},
    {"p": "Por que o programa escolheu Welch em vez de ANOVA?",
     "r": "Porque seus grupos têm variâncias (dispersões) muito diferentes. Nesse "
          "caso Welch é mais correto e evita falsos positivos."},
    {"p": "A análise foi recusada. O que faço?",
     "r": "Leia a mensagem em vermelho: ela diz a causa (ex.: falta o n, um grupo "
          "sem valores, texto numa coluna de números, ou variância zero). Corrija "
          "os dados e rode de novo."},
    {"p": "Colei uma tabela de média ± DP e deu erro. Por quê?",
     "r": "Isso é uma tabela RESUMIDA, não dados brutos. Use o modo \"Documento\" "
          "ou \"Estatísticas resumidas\" na seção DADOS."},
    {"p": "Posso enviar uma foto ou um gráfico?",
     "r": "Não. Extrair números de imagens/gráficos é impreciso e o StatLab não "
          "fabrica dados. Envie a tabela (Excel/CSV/PDF/Word) ou digite os valores."},
    {"p": "Preciso saber estatística para usar?",
     "r": "Não. Siga o Guia rápido: informe os dados, confirme o delineamento e "
          "clique em Analisar. O programa escolhe o teste e explica o resultado."},
]


# --------------------------------------------------------------------------- #
# Renderização na interface (Streamlit)
# --------------------------------------------------------------------------- #
def render(st) -> None:
    """Renderiza a seção MANUAL / AJUDA. Recebe o módulo ``streamlit`` como ``st``
    para não acoplar o conteúdo (testável) ao framework de UI."""
    st.header("📖 Manual / Ajuda")
    st.markdown(INTRO)

    st.info("**Dica:** você pode manter este manual aberto numa aba e o StatLab em "
            "outra, ou usar o índice abaixo para pular direto ao que precisa.")

    with st.expander("⭐ Como ler o valor-p (leia primeiro!)", expanded=True):
        st.markdown(COMO_LER_P)

    st.subheader("🚀 Guia rápido — do zero ao resultado em 6 passos")
    for i, passo in enumerate(QUICK_START, 1):
        st.markdown(f"**{i}.** {passo}")

    st.subheader("🧭 Qual seção eu uso?")
    for item in FLUXOGRAMA:
        st.markdown(f"- **{item['pergunta']}** → {item['va_para']}")

    st.subheader("💡 Conceitos essenciais (sem jargão)")
    for c in CONCEITOS:
        with st.expander(c["titulo"]):
            st.markdown(c["texto"])

    st.subheader("📚 Passo a passo de cada seção do programa")
    st.caption("Uma explicação para cada item do menu à esquerda.")
    for nome, info in SECOES.items():
        with st.expander(f"Seção {nome}"):
            st.markdown(f"**O que é / para que serve:** {info['o_que']}")
            st.markdown("**Como usar:**")
            for i, passo in enumerate(info.get("passos", []), 1):
                st.markdown(f"{i}. {passo}")
            dicas = info.get("dicas", [])
            if dicas:
                st.markdown("**Dicas e avisos:**")
                for d in dicas:
                    st.markdown(f"- {d}")

    st.subheader("📗 Glossário rápido")
    st.caption("Os termos mais comuns, em uma frase cada.")
    for termo, definicao in GLOSSARIO.items():
        st.markdown(f"- **{termo}** — {definicao}")

    st.subheader("❓ Perguntas frequentes")
    for item in FAQ:
        with st.expander(item["p"]):
            st.markdown(item["r"])

    st.caption("Princípio do StatLab: correção estatística acima de conveniência. O "
               "programa prefere recusar e explicar a entregar um número inválido — "
               "e nunca fabrica dados.")


# Nomes de seção que o manual DEVE cobrir (usado pelos testes para garantir que o
# manual acompanha o menu do app).
COVERED_SECTIONS = set(SECOES.keys())
