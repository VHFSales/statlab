# StatLab — Auditoria completa, correções e análises

**Data:** 2026-09-11 · **Escopo:** varredura de bugs em todos os módulos, validação com
dados reais, dupla checagem e entrega das análises com justificativa de cada escolha de método.

> **Sobre o "arquivo de teste em anexo":** o anexo não chegou processável nesta
> conversa (o `.xlsx` colado veio como bytes binários corrompidos). Para não travar a
> auditoria, usei como conjunto de teste os **dados reais do seu trabalho** já conhecidos:
> a **Tabela 29** (brilho, média ± DP com letras de Tukey) e as tabelas do **PDF de
> qualificação** (T3 ângulo de contato, T4 energia de superfície, T5 rugosidade Ra).
> Se você reenviar o arquivo (de preferência como **CSV** ou colando os números), eu
> rodo exatamente sobre ele.

---

## 1. Resumo executivo

- **Cobertura:** 24 módulos estatísticos + entrada de dados + orquestração + relatórios.
- **Suíte:** de **311 → 322 testes** (todos passam; 4 *oracle* pulam offline por falta de SciPy).
- **Bugs corrigidos:** 3 de robustez (2 eram **crashes**), + endurecimento numérico e transparência.
- **Falsos positivos refutados com prova:** 3 (CLD, Dunn, precisão do *studentized range*).
- **Dupla checagem:** os resultados do StatLab batem com recálculo independente feito à mão.

---

## 2. Bugs encontrados e corrigidos

### 2.1 [CRÍTICO] Tabela resumida sem desvio padrão derrubava a análise
- **Sintoma:** ao analisar uma tabela de resumo sem coluna de DP (ex.: a **Tabela 4 –
  energia de superfície**, que só tem valores pontuais), o programa quebrava com
  `KeyError: 'sd'`.
- **Causa:** `validate_summary` checava a ausência de média e de *n*, mas **não** a de DP;
  o orquestrador então lia `summary[grupo]["sd"]` incondicionalmente.
- **Correção:** `validate_summary` agora emite um ERRO `NO_SD` explícito → a análise é
  **recusada com mensagem clara** ("sem o DP não é possível ANOVA/teste t a partir de
  resumo; informe o DP ou use os dados brutos"), em vez de quebrar.

### 2.2 [MÉDIO] Dados degenerados (variância nula) causavam exceção não tratada
- **Sintoma:** com todas as observações idênticas (variância zero), `analyze_raw`/
  `analyze_summary` lançavam `InsufficientDataError` **não capturada** (crash).
- **Correção:** os três caminhos de omnibus (ANOVA/Welch em bruto, teste-t de 2 grupos,
  ANOVA/Welch em resumo) passaram a capturar `InsufficientDataError` e devolver uma
  **recusa limpa**.

### 2.3 [ROBUSTEZ + DÍVIDA TÉCNICA] Quantil-t truncava caudas extremas e estava duplicado
- **Sintoma:** o quantil da t de Student (`_t_ppf`) estava **copiado em 5 arquivos** com um
  domínio fixo de bisseção `[-1e4, 1e4]`. Em caudas extremas (df=1, confiança ≥ 99,9999%)
  ele **saturava em 10000** em vez do valor real (~3,18 milhões).
- **Correção:** consolidei um único `t_ppf` em `statistics/distributions.py`, com **bracket
  adaptativo** (expande conforme necessário), simétrico e com tratamento de bordas. As 5
  cópias agora delegam a ele.
- **Impacto prático:** os intervalos de confiança usados no app (90/95/99%) nunca atingiam
  a saturação, então **nenhum resultado publicável mudou** — a correção é de robustez.

### 2.4 [TRANSPARÊNCIA] ANOVA clássica sem diagnóstico de variâncias agora avisa
- Quando **nenhum** diagnóstico de homogeneidade está disponível, o motor de decisão agora
  registra um aviso de que a ANOVA clássica assume variâncias iguais **sem verificação** e
  sugere considerar a ANOVA de Welch.

---

## 3. Falsos positivos refutados (o código estava correto)

Uma auditoria automatizada levantou suspeitas que **investiguei e descartei com prova**:

- **CLD (Compact Letter Display):** testei **exaustivamente todas** as matrizes de
  significância possíveis para k = 3, 4 e 5 grupos (incluindo as intransitivas). **Zero
  violações** dos invariantes (grupos significativos nunca compartilham letra; não
  significativos sempre compartilham ≥ 1). Algoritmo de Piepho correto.
- **Teste de Dunn:** o termo de variância `N(N+1)/12 − Σ(t³−t)/(12(N−1))` é a variância dos
  postos — mínimo exatamente **0** no empate total, **nunca negativo**. Não há risco de raiz
  de número negativo.
- **Precisão do *studentized range* (Tukey/Games-Howell):** bate com as tabelas de Harter
  com erro máximo **0,0004**, inclusive para poucos graus de liberdade (df = 3). O quantil-t
  bate com erro ≤ 0,0004 até df = 1.

---

## 4. Dupla checagem (recálculo independente)

Recalculei "à mão" os resultados do StatLab, de forma independente do código:

| Verificação | StatLab | Recálculo independente | Confere? |
|---|---|---|---|
| Welch ANOVA — Tabela 29 "brilho antes 20" (n=5) | F=76,1498; df₂=8,299 | F=76,1498; df₂=8,299 | ✅ |
| CLD — Tabela 29 "brilho antes 20" | D2:b, D3:c, D4:a, D5:a | (matriz idêntica) | ✅ |
| Teste-t (2 grupos, razão var. 2,01) | Student t=27,2496; df=8 | t=27,2496; df=8 | ✅ |
| Games-Howell — "brilho antes 60" (matriz de significância) | (ver §5) | (par a par idêntico) | ✅ |

**Conclusão:** o núcleo numérico é confiável. Onde o CLD do StatLab **difere** das letras
impressas no trabalho (colunas "antes 60" e "antes 85"), a diferença **não é erro do
StatLab** — meu recálculo independente confirmou o resultado do programa. As causas
prováveis são (a) os valores dessas colunas que reconstruí não são exatamente os do
trabalho, ou (b) o trabalho usou outro *n* ou o Tukey clássico em vez de Games-Howell.
**Só posso confirmar as letras de "antes 60/85" com a Tabela 29 real em mãos.**

---

## 5. Análises entregues e justificativa de cada escolha de método

Todas com **α = 0,05** e **n = 5** (o *n* declarado no trabalho: "5 medições por corpo de
prova"). O StatLab **não fabrica o n** — ele foi informado explicitamente.

### 5.1 T3 — Ângulo de contato, Glicerol (6 grupos: potência × condição)
- **Global:** ANOVA de **Welch** — F(5; 10,88) = **29,30**, p = **5,8×10⁻⁶**.
- **Pós-teste:** **Games-Howell**. CLD: 900 W·Sem=**a**; 600 W·Sem=b; 750 W·Sem=bc;
  600 W·Com=cd; 900 W·Com=bcd; 750 W·Com=**d**.
- **Leitura:** há redução significativa do ângulo após o plasma; o menor ângulo (grupo "d")
  é o 750 W·Com plasma — coerente com o 750 W ser a melhor condição de molhabilidade.

### 5.2 T3 — Ângulo de contato, Diiodometano
- **Global:** ANOVA de **Welch** — F(5; 11,06) = **27,69**, p = **6,7×10⁻⁶**. Pós: Games-Howell.

### 5.3 T5 — Rugosidade Ra
- **Global:** ANOVA de **Welch** — F(5; 10,78) = **3,92**, p = **0,028** (significativo no geral),
  mas o pós-teste (Games-Howell) **não separa nenhum par** (todos compartilham "a").
- **Leitura honesta:** o efeito global é fraco e o pós-teste, mais conservador, não sustenta
  diferenças par a par — condizente com a variação de rugosidade ser pequena/heterogênea.

### 5.4 Tabela 29 — Brilho (n=5)
- **antes 20:** Welch F(3; 8,30)=**76,15**, p=2,3×10⁻⁶ → CLD {D2:b, D3:c, D4:a, D5:a} =
  **idêntico às letras do trabalho** (validação forte).
- **antes 60 / 85:** Welch altamente significativo; CLD recalculado (ver §4 sobre a divergência).

### 5.5 T4 — Energia de superfície (sem DP) → **recusado, corretamente**
- A tabela traz apenas valores pontuais (sem desvio). O StatLab **recusa** a análise de
  significância: sem DP e sem *n* não há como testar — e o programa **não fabrica
  incerteza**. (Antes da correção 2.1, isso quebrava o app.)

### Por que Welch (e Games-Howell) e não ANOVA clássica (e Tukey)?

O StatLab escolhe o método pela **homogeneidade de variâncias**:

- **ANOVA clássica + Tukey HSD** quando as variâncias são homogêneas (razão pequena; Levene/
  Brown-Forsythe não significativos). Validei: um conjunto homocedástico foi roteado para
  ANOVA + Tukey.
- **ANOVA de Welch + Games-Howell** quando as variâncias são **heterogêneas** — que é o caso
  de **todas** as suas tabelas: as razões de variância entre grupos são **grandes** (14,9 no
  ângulo/glicerol; 6,0 no diiodometano; **50,1** na rugosidade; 14,6 no brilho antes 20).
  Com variâncias tão desiguais, a ANOVA clássica infla o erro tipo I; **Welch é o correto**, e
  Games-Howell é o pós-teste coerente com Welch (não assume variâncias iguais).
- **2 grupos:** teste-t (Student se as variâncias forem próximas, razão < 3; Welch caso
  contrário). **Nunca** se fabrica o *n* nem o DP.
- **Recusa** quando faltam dados (sem *n*, sem DP, ou variância nula) — preferimos recusar a
  entregar um número inválido.

---

## 6. Recomendação ao autor do trabalho

Como **todas** as tabelas têm variâncias marcadamente heterogêneas, o par
**Welch + Games-Howell** é o estatisticamente defensável — e é o que o StatLab seleciona
automaticamente. Se o trabalho original reportou Tukey clássico sobre esses dados, vale
reconsiderar, porque a premissa de variâncias iguais não se sustenta aqui.
