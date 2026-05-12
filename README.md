# Análise Estatística — Portal da Transparência de Criciúma

Projeto de extensão universitária para a disciplina de **Estatística**.
Os dados foram obtidos do [Portal da Transparência da Prefeitura de Criciúma](https://transparencia.betha.cloud/#/n4W91vnHptoBkiHKAxioOA==/dados-abertos?esconderCabecalho=S&esconderMenu=S&esconderRodape=S).

## Pergunta-problema

> *"Qual o impacto do número de participantes nas licitações sobre a economia gerada para o município de Criciúma? Características do processo, como valor orçado, modalidade e duração da tramitação, amplificam ou atenuam esse efeito?"*

## Estrutura do projeto

```
analiseEstatisticaPrefeituraCriciuma/
│
├── script.py                      # Etapa 1 — pré-processa cada pasta baixada do portal
├── concatenacaoDados.py           # Etapa 2 — unifica todas as fontes em uma base final (v14)
├── calcularCorrelacoes.py         # Etapa 3 — análise de correlações com a variável alvo
├── testeNormalidade.py            # Etapa 4 — Shapiro-Wilk em todas as 25 variáveis candidatas
├── normalizacaoBase.py            # Etapa 5 — tentativas de normalização via transformações
├── ajusteDistribuicoes.py         # Etapa 6 — ajuste de distribuições discretas e contínuas
├── normalizacaoVariavelAlvo.py    # Etapa 7 — relatório focado na normalização da variável alvo
│
├── dadosUnificados/               # Saída do script.py (CSVs intermediários por pasta/ano)
│   ├── Processos Licitatórios Finalizados-2019/
│   ├── Processos Licitatórios Finalizados-2020/
│   ├── Dispensa de Licitação-2019/
│   ├── Dispensa de Licitação-2020/
│   └── Fornecedores sancionados/         # referência cruzada (opcional)
│
├── baseFinalUnificada/
│   └── base_unificada_criciuma_v14.csv   # Base final — entrada de todas as etapas analíticas
│
├── correlacoesVariaveis/
│   ├── correlacoes_criciuma.csv          # Tabela de correlações exportada
│   └── grafico_correlacoes.png           # Gráfico de barras (Spearman)
│
├── normalidadeVariaveis/
│   └── normalidade_shapiro.csv           # Resultados do SW em todas as 25 variáveis
│
├── normalizacaoBase/
│   ├── resultado_transformacoes.csv      # W e p-valor de cada transformação testada
│   ├── qqplots_normal.png                # Q-Q plots das 4 transformações vs. Normal
│   └── qqplot_gamma.png                  # Q-Q plot e histograma Gamma ajustada
│
├── ajusteDistribuicoes/
│   ├── resultado_ajuste_discreto.csv     # Qui-quadrado para variáveis de contagem
│   ├── resultado_ajuste_continuo.csv     # KS para variáveis monetárias
│   ├── distribuicoes_discretas.png       # PMF e CDF comparativas
│   └── distribuicoes_continuas.png       # PDF e Q-Q comparativos
│
├── normalizacaoVariavelAlvo/
│   ├── resultado_normalidade.csv         # Tabela SW + KS por distribuição
│   └── grafico_distribuicoes.png         # Grid 2×2: histograma + 3 Q-Q plots
│
├── Arquivos e Colunas de cada Pasta.xlsx # Dicionário de dados das fontes originais
└── requirements.txt
```

## Como reproduzir

### 1. Instalar dependências

```bash
python -m venv .venv
.venv/Scripts/activate       # Windows
pip install -r requirements.txt
```

### 2. Baixar os dados do portal

Acesse o Portal da Transparência de Criciúma e baixe as seguintes seções para cada ano desejado:

- Processos Licitatórios Finalizados
- Dispensa de Licitação
- Fornecedores Sancionados (referência cruzada — opcional, mas necessário para colunas de sanção)

### 3. Pré-processar as pastas (`script.py`)

Execute `script.py` apontando para cada pasta baixada. O script consolida os arquivos CSV de cada seção em arquivos unificados (`df_27_unificado.csv`, `df_participantes_unificado.csv`, `df_itensvencedores_unificado.csv`, `df_despesas_unificado.csv`, etc.) salvos em `dadosUnificados/`.

### 4. Gerar a base final (`concatenacaoDados.py`)

```bash
python concatenacaoDados.py
```

Lê os CSVs de `dadosUnificados/`, cruza todas as fontes e gera `baseFinalUnificada/base_unificada_criciuma_v14.csv`.

Para adicionar um novo ano, inclua uma entrada na lista `FONTES` no início do arquivo:

```python
{
    "label": "finalizado_2021",
    "tipo_processo": "LICITACAO",
    "pasta": os.path.join(BASE_DIR, "Processos Licitatórios Finalizados-2021"),
},
```

### 5. Calcular correlações (`calcularCorrelacoes.py`)

```bash
python calcularCorrelacoes.py
```

Gera a tabela `correlacoesVariaveis/correlacoes_criciuma.csv` e o gráfico `grafico_correlacoes.png`.

## Base final — `base_unificada_criciuma_v14.csv`

| Característica | Valor |
|---|---|
| Unidade de análise | 1 linha = 1 item vencedor de licitação |
| Fontes integradas | Processos Licitatórios Finalizados-2019/2020 · Dispensa de Licitação-2019/2020 |
| Anos cobertos | 2019 e 2020 |
| Meta de registros | ≥ 20.000 (verificada automaticamente pelo pipeline) |
| Separador de campo | `;` |
| Separador decimal | `,` (padrão pt-BR, compatível com Excel) |
| Encoding | UTF-8 com BOM (`utf-8-sig`) |

### Correções aplicadas (v14 sobre v13)

| Correção | Descrição |
|---|---|
| **FIX-01** | Participantes vinculados por UUID direto (`df_27.participantes → df_participantes.origem_arquivo`). A versão anterior contava apenas vencedores, ignorando todos os perdedores. |
| **FIX-02** | `valorHomologado` reconstruído via `sum(valorTotalVencedor)` por licitação quando o campo está nulo no portal. Concordância de 99,8 % em 480 licitações de 2019. |
| **FIX-03** | `valorEstimado` removido do filtro obrigatório de consistência. Licitações com `valorHomologado` reconstruído pelos itens podem não ter `valorEstimado` sem comprometer o cálculo do alvo. |
| **FIX-04** | Secretaria vinculada por UUID direto (`df_27.despesas → df_despesas.origem_arquivo`). O mapeamento anterior via número de licitação tinha cobertura de apenas 33 %. |

### Filtro de consistência aplicado

`concatenacaoDados.py` remove linhas onde:

1. `ratio_vencedor_referencia` é nulo (preço de referência zero ou ausente no portal — valores sem base comparável).
2. `valorHomologado` permanece nulo mesmo após a reconstrução pelo FIX-02.

`valorEstimado` **não é filtrado** (FIX-03): licitações sem estimativa ainda possuem economia calculável pelos itens.

Deduplicação: quando a mesma `chave_licitacao` existe em LICITAÇÃO e DISPENSA, mantém-se apenas a versão LICITAÇÃO (Finalizados), por ser a fonte mais completa.

### Dicionário de colunas

#### Identificação do item

| Coluna | Descrição |
|---|---|
| `chave_licitacao` | Chave única da licitação: `{numeroLicitacao}_{ano}` |
| `tipo_processo` | Origem do registro: `LICITACAO` ou `DISPENSA` |
| `codigo` | Código de catálogo do item (0 = sem código atribuído pelo portal) |
| `descricao` | Descrição do item licitado |
| `cnpjCpfVencedor` | CNPJ/CPF do fornecedor vencedor |
| `participanteVencedor` | Razão social do fornecedor vencedor |
| `quantidade` | Quantidade licitada |
| `unidadeMedida` | Unidade de medida |
| `_fonte` | Pasta/ano de origem (`finalizado_2019`, `dispensa_2020`, etc.) |

#### Preços do item

| Coluna | Descrição |
|---|---|
| `valorTotalReferencia` | Valor total de referência (preço estimado × quantidade) |
| `valorTotalVencedor` | Valor total ofertado pelo vencedor |
| `valorUnitarioReferencia` | Preço unitário de referência |
| `valorUnitarioVencedor` | Preço unitário ofertado |
| `economia_item` | Diferença absoluta: referência − vencedor (R$) |
| `economia_item_pct` | Desconto por item (%); valores fora de [−100, 100] são clampados na agregação |
| `ratio_vencedor_referencia` | `valorTotalVencedor / valorTotalReferencia` |

#### Atributos da licitação (repetidos por item)

| Coluna | Descrição |
|---|---|
| `modalidade` | Pregão, Tomada de Preços, Convite, Concorrência, etc. |
| `tipoObjeto` | Tipo do objeto: serviços, materiais, obras, etc. |
| `formaJulgamento` | Critério de julgamento: menor preço, melhor técnica, etc. |
| `objeto` | Descrição do objeto da licitação |
| `valorEstimado` | Valor total estimado da licitação (R$) |
| `valorHomologado` | Valor total contratado após homologação (R$) |
| `valorHomologado_reconstruido` | Flag: `1` se `valorHomologado` foi reconstruído via soma dos itens (FIX-02) |
| `economia_absoluta` | `valorEstimado − valorHomologado` (R$) |
| `economia_pct_licit` | `economia_absoluta / valorEstimado × 100` (%) |
| `qtd_participantes` | Número de empresas participantes (contagem por UUID — FIX-01) |
| `houve_disputa` | Flag: `1` se mais de 1 participante, `0` caso contrário |
| `dias_tramitacao` | Dias entre publicação e homologação |
| `n_itens_licitacao` | Número de itens vencedores da licitação |
| `n_vencedores_distintos` | Número de fornecedores distintos vencedores na licitação |
| `media_desconto_item` | Desconto médio por item (%) |
| `amplitude_desconto_item` | Amplitude dos descontos: `max − min` de `economia_item_pct` (p.p.) |

#### Secretaria / função orçamentária (vinculadas por UUID — FIX-04)

| Coluna | Descrição |
|---|---|
| `orgao_principal` | Secretaria/Órgão responsável pela despesa |
| `funcao_principal` | Função orçamentária (saúde, educação, urbanismo, etc.) |
| `programa_principal` | Programa orçamentário principal |

#### Fornecedores sancionados

| Coluna | Descrição |
|---|---|
| `vencedor_sancionado` | Flag: `1` se o CNPJ do vencedor consta na lista de sancionados |
| `tipo_sancao_vencedor` | Sanção mais grave do fornecedor (INIDONEIDADE > IMPEDIMENTO > SUSPENSAO > MULTA > ADVERTENCIA) |
| `sancao_ativa` | Flag: `1` se alguma sanção não tem data de término ou ainda está dentro do prazo |
| `qtd_processos_sancionado` | Número de processos em que o fornecedor foi sancionado |

#### Variáveis derivadas e transformações logarítmicas

| Coluna | Descrição |
|---|---|
| `log_qtd_participantes` | `log(qtd_participantes + 1)` |
| `log_valorEstimado` | `log(valorEstimado + 1)` |
| `log_valorHomologado` | `log(valorHomologado + 1)` |
| `log_dias_tramitacao` | `log(dias_tramitacao + 1)` |
| `log_n_itens` | `log(n_itens_licitacao + 1)` |
| `log_n_vencedores` | `log(n_vencedores_distintos + 1)` |
| `interact_part_logval` | `qtd_participantes × log(valorEstimado + 1)` — interação competição × escala |
| `tipo_processo_cod` | Codificação numérica de `tipo_processo` |
| `modalidade_cod` | Codificação numérica de `modalidade` |
| `tipoObjeto_cod` | Codificação numérica de `tipoObjeto` |
| `formaJulgamento_cod` | Codificação numérica de `formaJulgamento` |
| `orgao_cod` | Codificação numérica de `orgao_principal` |
| `funcao_cod` | Codificação numérica de `funcao_principal` |

## Variável alvo da análise de correlações

**`economia_itens`** = `soma_ref − soma_venc`

Soma da diferença (preço de referência − preço vencedor) de todos os itens da licitação. Mede quanto a Prefeitura pagou abaixo do preço de referência no total (em R$).

**Cobertura: 100 %** — calculada diretamente a partir dos itens vencedores, sem dependência de campos opcionais do portal.

> Nota: a variável alvo anterior (`razao_pago_homolog`) foi substituída por `economia_itens` porque dependia de `soma_valorPagoEmpenho`, coluna vinculada a empenhos com cobertura de apenas ~7 % da base, gerando viés de seleção severo.

### Resultado das correlações (25 variáveis)

**15 das 25** variáveis candidatas atingem o critério |Spearman| ≥ 0,3 (critério ≥ 15 **atendido**):

| # | Variável | Spearman | Pearson | Grupo | Interpretação |
|---|---|---|---|---|---|
| 01 | `desconto_global_pct` | +0,76 | +0,26 | D | Desconto global dos itens — relação quase direta com o alvo por construção |
| 02 | `media_ratio_itens` | −0,69 | −0,04 | D | Ratio médio vencedor/referência — inverso do desconto |
| 03 | `media_desconto_item` | +0,64 | +0,11 | D | Desconto médio por item (%) |
| 04 | `interact_part_logval` | +0,53 | +0,15 | B | Interação competição × escala do contrato |
| 05 | `valorEstimado` | +0,52 | +0,12 | A | Valor orçado total da licitação |
| 06 | `log_valorEstimado` | +0,52 | +0,13 | A | Log do valor orçado |
| 07 | `economia_pct_licit` | +0,51 | +0,01 | A | % economizado sobre o valor estimado |
| 08 | `log_qtd_participantes` | +0,49 | +0,10 | B | Log do número de participantes |
| 09 | `qtd_participantes` | +0,49 | +0,12 | B | Número de empresas participantes |
| 10 | `log_valorHomologado` | +0,46 | +0,11 | A | Log do valor contratado |
| 11 | `valorHomologado` | +0,46 | +0,12 | A | Valor contratado após homologação |
| 12 | `pct_itens_abaixo_ref` | +0,38 | +0,10 | G | % de itens com preço abaixo da referência |
| 13 | `log_dias_tramitacao` | +0,35 | +0,09 | C | Log dos dias de tramitação |
| 14 | `dias_tramitacao` | +0,35 | +0,08 | C | Dias da publicação à homologação |
| 15 | `houve_disputa` | +0,33 | +0,08 | B | Flag: houve disputa entre participantes |

As **10 variáveis restantes** ficaram abaixo de 0,3, mas são teoricamente relevantes para a pergunta-problema:

| # | Variável | Spearman | Grupo |
|---|---|---|---|
| 16 | `modalidade_cod` | +0,26 | Tipo de processo |
| 17 | `tipoObjeto_cod` | +0,24 | Tipo de processo |
| 18 | `funcao_cod` | −0,23 | Secretaria |
| 19 | `formaJulgamento_cod` | +0,23 | Tipo de processo |
| 20 | `log_n_vencedores` | +0,16 | Estrutura do processo |
| 21 | `n_vencedores_distintos` | +0,16 | Estrutura do processo |
| 22 | `amplitude_desconto_item` | +0,12 | Desconto por item |
| 23 | `orgao_cod` | −0,08 | Secretaria |
| 24 | `log_n_itens` | +0,08 | Estrutura do processo |
| 25 | `n_itens_licitacao` | +0,08 | Estrutura do processo |

### Grupos das candidatas

| Grupo | Variáveis | Tema |
|---|---|---|
| A — Escala do contrato | `valorEstimado`, `log_valorEstimado`, `valorHomologado`, `log_valorHomologado`, `economia_pct_licit` | Co-variáveis do alvo (nota de transparência) |
| B — Competição | `qtd_participantes`, `log_qtd_participantes`, `houve_disputa`, `interact_part_logval` | **Pergunta-problema principal** |
| C — Estrutura/complexidade | `n_itens_licitacao`, `log_n_itens`, `n_vencedores_distintos`, `log_n_vencedores`, `dias_tramitacao`, `log_dias_tramitacao` | Tamanho e duração do processo |
| D — Desconto por item | `media_desconto_item`, `amplitude_desconto_item`, `desconto_global_pct`, `media_ratio_itens` | Qualidade dos preços ofertados |
| E — Tipo de processo/julgamento | `modalidade_cod`, `tipoObjeto_cod`, `formaJulgamento_cod` | Modalidade e critério |
| F — Secretaria/função | `orgao_cod`, `funcao_cod` | Modulador institucional |
| G — Qualidade da competição | `pct_itens_abaixo_ref` | Cobertura dos descontos |

### Nota de transparência

As variáveis do Grupo A (`valorEstimado`, `valorHomologado`, `economia_pct_licit`) e do Grupo D (`desconto_global_pct`, `media_ratio_itens`, `media_desconto_item`) são componentes matemáticos ou co-variáveis diretas do alvo `economia_itens`. As correlações fortes observadas nelas refletem parcialmente essa relação por construção. Mantidas na lista por coerência com o critério de **25 candidatas** da disciplina; em uma análise puramente explicativa, seriam tratadas como controles ou excluídas.

### Observações sobre a distribuição do alvo

- `economia_itens`: concentrada à direita, com licitações de grande valor dominando a magnitude.
- **Pearson ≈ 0 em quase todas as variáveis de competição** — confirma que as relações são monotônicas mas não lineares. A interpretação deve ser feita sobre **Spearman** (robusto a outliers).
- `qtd_participantes` e `houve_disputa` correlacionam-se positivamente com `economia_itens` (Spearman ≈ +0,49 e +0,33), sustentando a hipótese central de que maior competição está associada a maior economia.

## Normalização da variável alvo

### O que é normalizar uma variável

"Normalizar" no contexto estatístico significa identificar se uma variável segue a **distribuição Normal (gaussiana)** — a curva em sino simétrica — e, caso não siga, aplicar transformações matemáticas ou identificar qual distribuição teórica de fato a descreve. Isso importa porque muitos modelos inferenciais clássicos (regressão linear, ANOVA, teste t) assumem normalidade dos dados ou dos resíduos.

### Roteiro aplicado

O professor solicitou o seguinte fluxo para a variável-alvo `economia_itens`:

1. Testar normalidade com o teste de Shapiro-Wilk (SW).
2. Se rejeitada → tentar transformações e, em seguida, ajustar as distribuições estudadas em aula.

### Etapa 1 — Teste de Shapiro-Wilk (`testeNormalidade.py` e `normalizacaoBase.py`)

O teste SW verifica a hipótese H₀: "os dados seguem distribuição Normal". Um p-valor ≥ 0,05 indica que não há evidência para rejeitar essa hipótese (dados compatíveis com a Normal). Um p-valor < 0,05 rejeita a normalidade.

| Versão dos dados | W | p-valor | Normal? |
|---|---|---|---|
| `economia_itens` original | 0,1757 | 7,67 × 10⁻⁴⁷ | **NÃO** |

O valor W=0,1757 é muito próximo de zero (W=1 seria perfeito), confirmando forte assimetria.

### Etapa 2 — Tentativas de transformação (`normalizacaoBase.py`)

Foram aplicadas três transformações matemáticas clássicas para reduzir a assimetria:

| Transformação | Fórmula | W | p-valor | Normal? |
|---|---|---|---|---|
| Log-deslocada | `log(x − mín + 1)` | 0,1009 | 3,57 × 10⁻⁴⁸ | **NÃO** |
| Yeo-Johnson | automática (λ = 0,9535) | 0,2301 | 8,26 × 10⁻⁴⁶ | **NÃO** |
| Box-Cox | automática (λ = 0,3723) | 0,3209 | 6,11 × 10⁻⁴⁴ | **NÃO** |

As transformações melhoraram o W (de 0,18 para 0,32), confirmando redução da assimetria, mas nenhuma atingiu p ≥ 0,05. Isso é esperado para dados monetários de licitações públicas: poucas licitações de grande valor criam uma cauda direita muito longa que resistem a transformações simples.

### Etapa 3 — Ajuste de distribuições alternativas (`normalizacaoVariavelAlvo.py`)

Como nenhuma transformação produziu normalidade, o passo seguinte foi identificar **qual distribuição teórica descreve os dados**. Em vez de forçar a Normal, busca-se a distribuição que naturalmente se encaixa no formato dos dados.

#### Distribuições discretas (Poisson, Geométrica, Binomial Negativa, Hipergeométrica)

Não aplicáveis à variável `economia_itens`, pois:

- Distribuições discretas só aceitam valores inteiros não-negativos (`{0, 1, 2, …}` ou `{1, 2, 3, …}`).
- `economia_itens` é uma variável **contínua** e possui valores negativos (licitações onde o valor pago superou a referência).

Essas distribuições são adequadas para variáveis de **contagem** como `qtd_participantes` e `n_itens_licitacao`.

#### Distribuições contínuas testadas (subconjunto eco > 0, n = 588)

O teste de Kolmogorov-Smirnov (KS) mede o maior afastamento entre a distribuição acumulada observada e a teórica. Estatística KS próxima de zero e p ≥ 0,05 indicam bom ajuste.

| Distribuição | KS | p-valor | Ajusta (α = 0,05)? |
|---|---|---|---|
| Normal | 0,4144 | ≈ 0 | **NÃO** |
| Gamma | 0,1278 | ≈ 0 | **NÃO** |
| **Log-Normal** | **0,0377** | **0,365** | **SIM ✓** |

### Por que a Log-Normal se ajusta

A distribuição Log-Normal é o modelo natural para variáveis monetárias que:

1. **São positivas por natureza** — contratos e economias financeiras não podem ser negativos em sua lógica estrutural; os 11,7 % de valores negativos refletem casos excepcionais onde o vencedor cobrou acima da referência.
2. **Têm cauda longa à direita** — a maioria das licitações gera economias pequenas ou moderadas, mas poucas licitações de grande vulto criam valores muito altos; a Log-Normal captura exatamente esse padrão.
3. **São geradas por efeitos multiplicativos** — preços de mercado resultam de negociações e margens aplicadas em cadeia (produto de fatores), e o produto de variáveis independentes tende à Log-Normal pelo Teorema Central do Limite aplicado à escala logarítmica.

Em termos práticos: se `X` ~ Log-Normal, então `log(X)` ~ Normal. Isso significa que aplicar o logaritmo à variável-alvo produz uma distribuição próxima da Normal — exatamente o que as transformações simples tentaram, mas sem conseguir pela presença de zeros e negativos.

### Fórmula da distribuição Log-Normal

Para uma variável aleatória $X > 0$, a função densidade de probabilidade (PDF) da distribuição Log-Normal é:

$$f(x;\, \mu, \sigma) = \frac{1}{x \, \sigma \sqrt{2\pi}} \exp\!\left(-\frac{(\ln x - \mu)^2}{2\sigma^2}\right), \quad x > 0$$

Onde:
- $\mu$ é a média do logaritmo natural de $X$ (parâmetro de localização na escala log)
- $\sigma$ é o desvio padrão do logaritmo natural de $X$ (parâmetro de escala na escala log)
- $\ln x$ é o logaritmo natural de $x$

**Parâmetros ajustados por MLE para `economia_itens` (n = 588, eco > 0):**

| Parâmetro | Valor | Interpretação |
|---|---|---|
| $\mu_{\log}$ | 10,2866 | Mediana na escala original: e^{10,2866} ≈ R$ 29.420 |
| $\sigma_{\log}$ | 2,0705 | Dispersão na escala log — valor alto indica cauda longa |

### Implicações para o projeto

| Consequência | Detalhe |
|---|---|
| **Transformação log é justificada matematicamente** | Se `economia_itens` ~ Log-Normal, então `log(economia_itens)` ~ Normal. As colunas `log_*` já calculadas na base têm fundamento teórico. |
| **Correlações de Spearman permanecem válidas** | Spearman é baseado em postos e independe da distribuição — a escolha foi correta mesmo antes de identificar a Log-Normal. |
| **Modelos de regressão recomendados** | GLM com família Gamma e link log, ou regressão Log-Normal. Ambos não exigem normalidade dos dados brutos, apenas dos resíduos padronizados. |

### Scripts e saídas

| Script | Função | Saídas |
|---|---|---|
| `testeNormalidade.py` | SW em todas as 25 variáveis candidatas | `normalidadeVariaveis/normalidade_shapiro.csv` |
| `normalizacaoBase.py` | Transformações + Gamma na variável alvo | `normalizacaoBase/resultado_transformacoes.csv`, Q-Q plots |
| `ajusteDistribuicoes.py` | Ajuste de Poisson/BN/Geométrica (contagens) e Gamma/LogNormal/Weibull (monetárias) | `ajusteDistribuicoes/` |
| `normalizacaoVariavelAlvo.py` | Relatório focado no roteiro do professor | `normalizacaoVariavelAlvo/resultado_normalidade.csv`, `grafico_distribuicoes.png` |

---

## Por que `df.corr()` diretamente na base não é adequado

Ao rodar `df.corr(numeric_only=True)['economia_itens']` diretamente no arquivo `base_unificada_criciuma_v14.csv`, obtêm-se valores diferentes dos apresentados em `correlacoes_criciuma.csv`. Há dois motivos independentes para isso.

### 1. Nível de análise diferente — pseudo-replicação

A base está no **nível do item** (21.980 linhas), mas as correlações devem ser calculadas no **nível da licitação** (666 processos únicos), porque as variáveis de competição são propriedades do processo, não do item individual.

Variáveis como `qtd_participantes`, `valorEstimado` e `orgao_principal` pertencem à *licitação*. Se uma licitação tem 33 itens, o mesmo valor de `qtd_participantes = 5` aparece 33 vezes na base. O `df.corr()` interpreta essas 33 linhas como 33 observações independentes — o que elas **não são**.

| Licitação | qtd_participantes | economia_itens | Linhas na base |
|---|---|---|---|
| A | 10 | R$ 50.000 | repetido 80× |
| B | 2 | R$ 1.000 | repetido 3× |

O `df.corr()` enxerga 83 pares, mas existem apenas 2 observações reais. Isso infla artificialmente o N e enviesa as correlações — fenômeno chamado de **pseudo-replicação**.

### 2. Pearson vs. Spearman

`df.corr()` usa **Pearson** por padrão. O projeto reporta **Spearman** como métrica principal, porque os valores monetários têm distribuição assimétrica com cauda longa à direita, e o Pearson é sensível a outliers. A diferença entre os dois é expressiva:

| Variável | Pearson no nível do item | Spearman no nível da licitação (correto) |
|---|---|---|
| `qtd_participantes` | ~0,03 | +0,49 |
| `valorEstimado` | ~0,07 | +0,52 |
| `houve_disputa` | ~0,02 | +0,33 |

### Como reproduzir os valores do CSV com pandas

```python
import pandas as pd

df = pd.read_csv("baseFinalUnificada/base_unificada_criciuma_v14.csv",
                 sep=";", decimal=",", encoding="utf-8-sig")

# Passo 1: uma linha por licitação
cols_licit = [
    "chave_licitacao", "qtd_participantes", "houve_disputa",
    "valorEstimado", "valorHomologado", "economia_pct_licit",
    "n_itens_licitacao", "n_vencedores_distintos", "dias_tramitacao",
    "media_desconto_item", "amplitude_desconto_item",
    "log_qtd_participantes", "log_valorEstimado", "log_valorHomologado",
    "log_n_itens", "log_n_vencedores", "log_dias_tramitacao",
    "interact_part_logval",
]
df_licit = df[[c for c in cols_licit if c in df.columns]].drop_duplicates("chave_licitacao")

# Passo 2: calcular alvo a partir dos itens
item_agg = (df.groupby("chave_licitacao")
              .agg(soma_ref=("valorTotalReferencia", "sum"),
                   soma_venc=("valorTotalVencedor",  "sum"))
              .reset_index())
item_agg["economia_itens"] = item_agg["soma_ref"] - item_agg["soma_venc"]
df_licit = df_licit.merge(item_agg[["chave_licitacao", "economia_itens"]], on="chave_licitacao")

# Passo 3: Spearman — resultado bate com correlacoes_criciuma.csv
df_licit.corr(method="spearman", numeric_only=True)["economia_itens"]
```

O script `calcularCorrelacoes.py` já executa esse fluxo automaticamente.

---

## Pontos de atenção sobre o volume de dados

### A base tem 21.980 registros, mas as correlações usam 666 — por quê?

Os 21.980 registros são **itens vencedores** individuais (ex.: Papel A4, Caneta, Grampeador) distribuídos dentro de **666 licitações** — processos de compra formais. Cada licitação representa um processo independente com seu próprio número de participantes, valor orçado e secretaria responsável.

O requisito de **≥ 20.000 registros** refere-se ao tamanho da **base unificada** (o arquivo CSV), não à unidade de análise das correlações. A base com 21.980 linhas atende esse requisito. As correlações são calculadas no nível da licitação (666 observações) porque é ali que as variáveis de interesse — número de participantes, modalidade, secretaria — existem como unidade estatisticamente independente.

Usar os 21.980 itens nas correlações introduziria pseudo-replicação (seção anterior), inflando o N e produzindo resultados incorretos.

### Por que não usar o desconto por item (`economia_item_pct`) como alvo?

Essa alternativa foi testada. Com `economia_item_pct` como alvo e análise no nível do item (21.980 linhas), apenas **4 das 25** variáveis candidatas atingiram |r| ≥ 0,3 — contra 15 na abordagem por licitação.

O motivo é que o desconto de cada item é altamente idiossincrático: depende do mercado específico daquele produto (uma caneta tem dinâmica de preços completamente diferente de um computador). Variáveis do processo (participantes, secretaria, prazo) explicam pouco da variação *entre itens*, mas explicam bem a variação *entre licitações*. A pergunta-problema — "o número de participantes influencia a economia gerada?" — naturalmente se refere ao processo licitatório, não ao item individual.

### O projeto atende todos os requisitos com 666 licitações?

Sim. A tabela abaixo resume o atendimento:

| Requisito | Situação |
|---|---|
| Selecionar arquivos das 18 bases | ✅ 5 pastas, 10+ arquivos-fonte utilizados |
| Base final ≥ 20.000 registros | ✅ 21.980 itens vencedores |
| Variável alvo definida | ✅ `economia_itens` (cobertura 100%) |
| 25 variáveis candidatas | ✅ 25 definidas em 7 grupos temáticos |
| Correlações calculadas | ✅ Pearson e Spearman para todas as 25 |
| ≥ 15 variáveis com \|r\| > 0,3 | ✅ Exatamente 15 (Spearman) |

## Decisões metodológicas relevantes

- **Unidade de análise da base**: item vencedor (1 linha = 1 item). Para correlações, agrega-se ao nível de licitação.
- **`codigo == 0`**: esperado — o portal não atribui código de catálogo a contratos de uso de espaços. Os valores financeiros são válidos.
- **Clamp de `economia_item_pct`**: limitado a [−100 %, 100 %] antes de calcular `media_desconto_item` e `amplitude_desconto_item`, pois itens com `valorTotalReferencia = 1,00` (placeholder do portal) geram percentuais de milhões de pontos.
- **Deduplicação LICITAÇÃO × DISPENSA**: quando a mesma `chave_licitacao` existe nas duas fontes, mantém-se apenas a versão "Finalizada" (mais completa e definitiva).
- **`valorHomologado` reconstruído (FIX-02)**: 70 % das licitações de 2020 não tinham esse campo preenchido no portal. A reconstrução via soma dos itens vencedores foi validada com concordância de 99,8 % em 480 licitações de 2019.
- **Separador decimal no CSV**: vírgula (`,`) para compatibilidade nativa com Excel em locale pt-BR.

## Dependências

```
pandas
scipy
numpy      # instalado como dependência do pandas
matplotlib
```

Instalar com:

```bash
pip install -r requirements.txt
```
