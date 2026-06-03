---
marp: true
title: Análise Estatística — Licitações da Prefeitura de Criciúma
paginate: true
---

# Análise Estatística das Licitações Públicas

## Portal da Transparência — Prefeitura de Criciúma

**Projeto de Extensão · Disciplina de Estatística**

Dados: Processos Licitatórios Finalizados e Dispensas de Licitação (2019–2020)

---

# Roteiro

1. A pergunta-problema
2. Trajetória de investigação dos dados
3. Correlação
4. Normalização dos dados
5. Estimativa pontual
6. O modelo de previsão (OLS)
7. As previsões futuras
8. Lições aprendidas

---

# 1. A Pergunta-Problema

> ## *"Qual o impacto do número de participantes nas licitações sobre a economia gerada para o município de Criciúma? Características do processo — como valor orçado, modalidade e duração da tramitação — amplificam ou atenuam esse efeito?"*

---

# 1. A Pergunta-Problema — decomposição

A pergunta tem **duas partes**:

| Parte | O que investiga |
|---|---|
| **Efeito principal** | Mais participantes (competição) → mais economia? |
| **Efeito moderador** | Valor orçado, modalidade e duração **amplificam ou atenuam** esse efeito? |

**Variável-alvo:** `economia_itens` = Σ (preço de referência − preço do vencedor) por licitação (R$)

**Variável de interesse principal:** `qtd_participantes`

**Moderadores:** `valorEstimado`, `modalidade`, `dias_tramitacao`

---

# 2. Trajetória de Investigação dos Dados

```
Portal da Transparência
        │
        ▼
[1] Coleta das fontes brutas (2019 + 2020)
        │
        ▼
[2] Pré-processamento por pasta ........... script.py
        │
        ▼
[3] Unificação e cruzamento das fontes .... concatenacaoDados.py
        │  (base_unificada_criciuma_v14.csv)
        ▼
[4] Definição da unidade de análise
        │
        ▼
[5] Definição da variável-alvo
        │
        ▼
[6] Cálculo amostral .................. calculo_amostra.py
        │
        ▼
[7] Correlações ....................... calcularCorrelacoes.py
        │
        ▼
[8] Normalização da variável-alvo ..... normalizacaoVariavelAlvo.py
        │
        ▼
[9] Estimativa e modelo de previsão ... estimativaPontualIntervalar.py
                                         regressaoOLS.py / previsaoOLS.py
```

---

# 2. Trajetória — Etapa 1: Coleta das fontes

Quatro seções do Portal da Transparência foram baixadas:

| Fonte | Tipo | Anos |
|---|---|---|
| Processos Licitatórios Finalizados | LICITAÇÃO | 2019, 2020 |
| Dispensa de Licitação | DISPENSA | 2019, 2020 |
| Fornecedores Sancionados | referência cruzada | — |

Cada seção vem fragmentada em vários CSVs relacionados por UUID
(`df_27`, `df_participantes`, `df_itensvencedores`, `df_despesas`…).

---

# 2. Trajetória — Etapa 3: Unificação (correções aplicadas)

A base final (v14) corrigiu erros de versões anteriores:

| Correção | Descrição |
|---|---|
| **FIX-01** | Participantes contados por UUID direto — antes só contava vencedores, ignorando quem perdeu |
| **FIX-02** | `valorHomologado` reconstruído pela soma dos itens quando ausente (concordância de 99,8 %) |
| **FIX-03** | `valorEstimado` retirado do filtro obrigatório (não compromete o alvo) |
| **FIX-04** | Secretaria vinculada por UUID — cobertura subiu de 33 % para quase total |

**Resultado:** `base_unificada_criciuma_v14.csv` → **21.980 itens × 63 colunas**

---

# 2. Trajetória — Etapa 4: A decisão crucial sobre o nível de análise

A base tem **21.980 linhas**, mas as análises usam **666 licitações**. Por quê?

- Cada linha = **1 item vencedor** (ex.: papel A4, caneta…)
- `qtd_participantes`, `valorEstimado` etc. são propriedades da **licitação**, não do item
- Se uma licitação tem 33 itens, o mesmo valor de participantes se repete 33×

> ⚠️ Usar os 21.980 itens infla artificialmente o N → **pseudo-replicação**

**Solução:** a base atende ao requisito de ≥ 20.000 registros, mas correlações, estimativas e regressão são calculadas **no nível da licitação (666 processos independentes)**.

---

# 2. Trajetória — Etapa 5: A variável-alvo

**`economia_itens`** = Σ (preço de referência − preço do vencedor)

| Característica | Valor |
|---|---|
| Significado | Quanto a Prefeitura pagou abaixo do preço de referência (R$) |
| Cobertura | **100 %** — calculada direto dos itens |

> A alvo anterior (`razao_pago_homolog`) foi **abandonada**: dependia de empenhos com cobertura de apenas ~7 %, gerando forte viés de seleção.

**Etapa 6 — Tamanho amostral:** método de Green (1991) + G*Power confirmaram que as 666 licitações **superam o N mínimo** exigido para o modelo de regressão.

---

# 3. Correlação — Metodologia

- Métrica principal: **Spearman** (postos), não Pearson
- Motivo: valores monetários têm **cauda longa à direita** → Pearson é distorcido por outliers
- Critério da disciplina: **≥ 15 das 25 variáveis** candidatas com |r| ≥ 0,3

> **Pearson ≈ 0 em quase tudo** confirma que as relações são **monotônicas, mas não lineares** — exatamente onde Spearman é a métrica correta.

✅ **Resultado: 15 das 25 variáveis atingiram |Spearman| ≥ 0,3 — critério atendido.**

---

# 3. Correlação — As 15 variáveis relevantes

| # | Variável | Spearman | Grupo |
|---|---|:---:|---|
| 1 | `desconto_global_pct` | **+0,76** | Desconto |
| 2 | `media_ratio_itens` | **−0,69** | Desconto |
| 3 | `media_desconto_item` | **+0,64** | Desconto |
| 4 | `interact_part_logval` | **+0,53** | **Competição** |
| 5 | `valorEstimado` | **+0,52** | Escala |
| 6 | `log_valorEstimado` | **+0,52** | Escala |
| 7 | `economia_pct_licit` | **+0,51** | Escala |
| 8 | `log_qtd_participantes` | **+0,49** | **Competição** |

---

# 3. Correlação — As 15 variáveis relevantes (cont.)

| # | Variável | Spearman | Grupo |
|---|---|:---:|---|
| 9 | `qtd_participantes` | **+0,49** | **Competição** |
| 10 | `log_valorHomologado` | **+0,46** | Escala |
| 11 | `valorHomologado` | **+0,46** | Escala |
| 12 | `pct_itens_abaixo_ref` | **+0,38** | Qualidade |
| 13 | `log_dias_tramitacao` | **+0,35** | Duração |
| 14 | `dias_tramitacao` | **+0,35** | Duração |
| 15 | `houve_disputa` | **+0,33** | **Competição** |

---

# 3. Correlação — Resposta à pergunta-problema

**Efeito principal — competição gera economia:** ✅

- `qtd_participantes` → **Spearman +0,49**
- `houve_disputa` → **+0,33**

> Quanto mais empresas participam, maior a economia gerada. A hipótese central se sustenta.

**Moderadores confirmados:**
- Valor orçado (`valorEstimado` +0,52) e duração (`dias_tramitacao` +0,35)
- `interact_part_logval` (+0,53): o efeito da competição **muda conforme a escala** do contrato

---

# 3. Correlação — Nota de transparência

> As variáveis dos grupos **Escala** e **Desconto** (`desconto_global_pct`, `media_ratio_itens`, `valorEstimado`…) são **componentes matemáticos ou co-variáveis diretas** do alvo.
>
> Suas correlações altíssimas (0,64–0,76) refletem parte dessa relação **por construção**.

As variáveis que respondem à pergunta de forma **limpa** são as do **Grupo Competição**:
`qtd_participantes` · `houve_disputa` · `interact_part_logval`

---

# 4. Normalização da Variável-Alvo

### O que é normalizar?

Verificar se a variável segue a **distribuição Normal (gaussiana)** — exigência de muitos
modelos clássicos (regressão linear, ANOVA, teste t).

### Roteiro aplicado (orientação do professor)

1. Testar normalidade com **Shapiro-Wilk (SW)**
2. Se rejeitada → tentar **transformações**
3. Se ainda rejeitada → **ajustar distribuições teóricas** (discretas e contínuas)

---

# 4. Normalização — Etapa 1: Shapiro-Wilk

Hipótese H₀: "os dados seguem a distribuição Normal".

| Variável | W | p-valor | Normal? |
|---|:---:|:---:|:---:|
| `economia_itens` original | **0,1757** | 7,67 × 10⁻⁴⁷ | **NÃO** |

- W = 0,1757 está muito longe de 1 (ajuste perfeito) → **forte assimetria**
- p ≪ 0,05 → rejeita-se a normalidade

---

# 4. Normalização — Etapa 2: Transformações

Tentativas clássicas de reduzir a assimetria:

| Transformação | W | p-valor | Normal? |
|---|:---:|:---:|:---:|
| Log-deslocada | 0,1009 | 3,57 × 10⁻⁴⁸ | **NÃO** |
| Yeo-Johnson (λ=0,95) | 0,2301 | 8,26 × 10⁻⁴⁶ | **NÃO** |
| Box-Cox (λ=0,37) | 0,3209 | 6,11 × 10⁻⁴⁴ | **NÃO** |

> As transformações **melhoraram** o W (0,18 → 0,32), mas nenhuma atingiu p ≥ 0,05.
> Esperado: poucas licitações de grande valor criam uma cauda direita teimosa.

---

# 4. Normalização — Etapa 3: Ajuste de distribuições

Em vez de **forçar** a Normal, identificar **qual distribuição descreve os dados**.

**Discretas (Poisson, Geométrica, Binomial Negativa, Hipergeométrica):**
❌ Não aplicáveis — `economia_itens` é **contínua** e tem valores negativos.

**Contínuas (subconjunto positivo, n = 588) — teste de Kolmogorov-Smirnov:**

| Distribuição | KS | p-valor | Ajusta? |
|---|:---:|:---:|:---:|
| Normal | 0,4144 | ≈ 0 | **NÃO** |
| Gamma | 0,1278 | ≈ 0 | **NÃO** |
| **Log-Normal** | **0,0377** | **0,365** | **SIM ✓** |

---

# 4. Normalização — Por que Log-Normal?

A Log-Normal é o modelo natural para valores monetários porque eles:

1. **São positivos por natureza** — economias não são negativas na lógica estrutural
2. **Têm cauda longa à direita** — muitas economias pequenas, poucas enormes
3. **Resultam de efeitos multiplicativos** — preços = produto de margens e negociações

**Parâmetros ajustados (MLE, n = 588):**

| Parâmetro | Valor | Interpretação |
|---|:---:|---|
| μ_log | 10,2866 | mediana ≈ e^10,29 ≈ **R$ 29.420** |
| σ_log | 2,0705 | dispersão alta → cauda longa |

> Conclusão central: se `X ~ Log-Normal`, então `log(X) ~ Normal`.
> **A transformação log é a chave para todo o resto da análise.**

---

# 5. Estimativa Pontual

### O conceito

A **estimativa pontual** resume em **um único número** o parâmetro de interesse:
*qual a economia típica gerada por uma licitação?*

### Por que não a média simples?

Como a variável é **Log-Normal** (cauda longa), a média aritmética é **enganosa**:

| Medida | Valor | Representa a licitação típica? |
|---|:---:|:---:|
| Média aritmética | R$ 192.449 | ❌ puxada por poucas licitações gigantes |
| **Mediana (média geométrica)** | **R$ 29.336** | ✅ |

> A estimativa correta vem da **escala log**, onde os dados são normais.

---

# 5. Estimativa Pontual e Intervalar

**Método:** t-Student na escala log → retransformação para R$ (n = 588, economia > 0)

| Grandeza | Valor |
|---|:---:|
| μ_log (escala log) | 10,2866 |
| IC 95% na escala log | [10,1187 ; 10,4544] |
| **Estimativa pontual (economia típica)** | **R$ 29.335,59** |
| **IC 95% em R$** | **[R$ 24.802,93 ; R$ 34.696,58]** |

> A economia **típica** por licitação é **R$ 29,3 mil**, com 95 % de confiança de estar
> entre **R$ 24,8 mil e R$ 34,7 mil**.
>
> ✅ Coincide com a mediana observada (R$ 30.001) → método validado.

---

# 6. O Modelo de Previsão (OLS)

### Especificação

| Item | Definição |
|---|---|
| **Variável dependente** | `log(economia_itens)` (escala normalizada) |
| **Preditores** | as variáveis bem correlacionadas (\|Spearman\| ≥ 0,3) |
| **Estimação** | Mínimos Quadrados Ordinários (OLS) |
| **Erros-padrão** | **robustos HC3** (corrige heterocedasticidade) |

**Desempenho:** R² = **0,657** · n = **386 licitações**

> O modelo explica ~66 % da variância da economia (escala log).

---

# 6. O Modelo de Previsão — Coeficientes significativos

Preditores estatisticamente significativos (p < 0,05, erros HC3):

| Variável | β | p-valor | Sig. |
|---|:---:|:---:|:---:|
| `log_valorHomologado` | +0,4783 | < 0,001 | *** |
| `desconto_global_pct` | +0,0612 | < 0,001 | *** |
| `pct_itens_abaixo_ref` | +0,0183 | < 0,001 | *** |
| `economia_pct_licit` | +0,0003 | 0,036 | * |

> A escala do contrato e a qualidade dos descontos dominam a previsão.
> Por que `qtd_participantes` perde significância individual? **Multicolinearidade**
> (ver Lições Aprendidas).

---

# 6. O Modelo de Previsão — Diagnóstico

Por que **erros robustos HC3** e não OLS clássico?

- **Resíduos não-normais** — herança da cauda Log-Normal do alvo (Shapiro rejeita)
- **Heterocedasticidade** — variância dos resíduos não é constante (Breusch-Pagan)
- **HC3** corrige os erros-padrão sem exigir normalidade, tornando os testes confiáveis

> A normalização (Seção 4) **fundamenta** essa escolha: sabendo que o alvo é
> Log-Normal, já se esperava heterocedasticidade e cauda pesada nos resíduos.

---

# 7. As Previsões Futuras

### Prevendo a economia de novas licitações

> ⚠️ O modelo é **transversal** (sem variável de tempo). "Futuro" = uma **nova
> licitação** ainda não observada — não um ano à frente.

**Dois intervalos diferentes:**

| Intervalo | O que mede | Largura |
|---|---|---|
| IC da média | incerteza do valor **médio** previsto | estreito |
| **Intervalo de previsão** | incerteza de uma **licitação individual** nova | **largo** |

> O intervalo de previsão é maior: soma a incerteza dos coeficientes **+** a
> variabilidade aleatória de uma nova observação.

---

# 7. As Previsões Futuras — Cenários de competição

Variando `qtd_participantes` (demais preditores fixados na mediana):

| Cenário | Participantes | Previsão | Intervalo de previsão 95% |
|---|:---:|:---:|:---:|
| Baixa competição | 1 | R$ 14.680 | [R$ 1.166 ; R$ 184.671] |
| Competição típica | 3 | R$ 18.698 | [R$ 1.514 ; R$ 230.805] |
| Alta competição | 8 | R$ 22.023 | [R$ 1.751 ; R$ 276.933] |

> **Mais participantes → maior economia prevista** (R$ 14,7 mil → R$ 22,0 mil),
> reforçando a resposta à pergunta-problema.

---

# 7. As Previsões Futuras — Leitura crítica

- A **tendência** confirma a hipótese: competição eleva a economia esperada.
- Os **intervalos de previsão são largos** (R$ 1 mil a ~R$ 280 mil) — esperado:
  - a economia individual varia muito entre licitações (cauda Log-Normal)
  - na escala log, o erro residual é alto (≈ 1,27)
- **Implicação honesta:** o modelo prevê bem a **direção e a média**, mas a economia
  de **uma licitação específica** carrega grande incerteza individual.

---

# 8. Lições Aprendidas

### Sobre os dados

1. **Nível de análise importa** — confundir item com licitação gera
   *pseudo-replicação* e correlações infladas. Definir a unidade certa foi decisivo.
2. **Cobertura antes de tudo** — a 1ª variável-alvo (`razao_pago_homolog`) tinha só
   7 % de cobertura. Trocar por `economia_itens` (100 %) eliminou viés de seleção.
3. **Joins por UUID** (FIX-01 a 04) recuperaram participantes e secretarias que o
   mapeamento ingênuo perdia.

---

# 8. Lições Aprendidas

### Sobre a estatística

4. **Normalizar ≠ tornar normal** — é *identificar a distribuição*. Descobrir a
   Log-Normal foi mais útil que forçar transformações que nunca convergiam.
5. **Spearman > Pearson** em dados assimétricos — relações monotônicas não-lineares.
6. **A média mente em cauda longa** — a mediana (R$ 29 mil) descreve a realidade;
   a média (R$ 192 mil) não.
7. **Multicolinearidade mascara efeitos** — preditores quase-derivados do alvo
   roubam a significância de `qtd_participantes`; daí a *nota de transparência*.
8. **Intervalo de previsão ≫ IC da média** — ser honesto sobre a incerteza de uma
   previsão individual é parte do rigor estatístico.

---

# Conclusão

- **Pergunta:** mais participantes → mais economia? ✅ **Sim** (Spearman +0,49)
- **Trajetória:** Portal → unificação (v14, FIX-01 a 04) → 666 licitações → análise
- **Correlação:** 15/25 variáveis com |Spearman| ≥ 0,3 — critério atendido
- **Normalização:** alvo segue **Log-Normal**, justificando a transformação logarítmica
- **Estimativa:** economia típica de **R$ 29,3 mil/licitação** (IC 95%: R$ 24,8–34,7 mil)
- **Modelo OLS:** R² = 0,66, com erros robustos HC3
- **Previsões:** alta competição → R$ 22,0 mil vs. R$ 14,7 mil na baixa competição

### A competição nas licitações está associada a maior economia para o município de Criciúma.

---

# Obrigado!


Repositório: `analiseEstatisticaPrefeituraCriciuma`

Dados: Portal da Transparência da Prefeitura de Criciúma
