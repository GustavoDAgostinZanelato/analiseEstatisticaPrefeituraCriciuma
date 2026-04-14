# Análise Estatística — Portal da Transparência de Criciúma

Projeto de extensão universitária para a disciplina de **Estatística**.
Os dados foram obtidos do [Portal da Transparência da Prefeitura de Criciúma](https://transparencia.betha.cloud/#/n4W91vnHptoBkiHKAxioOA==/dados-abertos?esconderCabecalho=S&esconderMenu=S&esconderRodape=S
).

## Pergunta-problema

> *"Qual o impacto da competição (número de participantes) e do tipo de gasto (Secretaria/Programa) na economia gerada e na eficiência da execução financeira do município de Criciúma?"*

## Estrutura do projeto

```
analiseEstatísticaPrefeituraCriciuma/
│
├── script.py                  # Etapa 1 — pré-processa cada pasta baixada do portal
├── concatenacaoDados.py       # Etapa 2 — unifica todas as fontes em uma base final
├── calcularCorrelacoes.py     # Etapa 3 — análise de correlações com a variável alvo
│
├── dadosUnificados/           # Saída do script.py (CSVs intermediários por pasta/ano)
│   ├── Processos Licitatórios-2019/
│   ├── Processos Licitatórios Finalizados-2019/
│   ├── Dispensa de Licitação-2019/
│   ├── Inexigibilidade de Licitação-2019/
│   ├── Relação de Contratos-2019/
│   ├── Execução Detalhada de Despesas-2019/
│   ├── Fornecedores sancionados/
│   └── ... (espelhos de 2020)
│
├── baseFinalUnificada/
│   └── base_unificada_criciuma_v13.csv   # Base final — entrada do calcularCorrelacoes.py
│
├── correlacoesVariaveis/
│   ├── correlacoes_criciuma.csv          # Tabela de correlações exportada
│   └── grafico_correlacoes.png           # Gráfico de barras (Spearman)
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

- Processos Licitatórios
- Processos Licitatórios Finalizados
- Dispensa de Licitação
- Inexigibilidade de Licitação
- Relação de Contratos
- Execução Detalhada de Despesas
- Fornecedores Sancionados


### 3. Pré-processar as pastas (`script.py`)

Execute `script.py` apontando para cada pasta baixada. O script consolida os arquivos CSV de cada seção em arquivos unificados salvos em `dadosUnificados/`.

### 4. Gerar a base final (`concatenacaoDados.py`)

```bash
python concatenacaoDados.py
```

Lê os CSVs de `dadosUnificados/`, cruza todas as fontes e gera `baseFinalUnificada/base_unificada_criciuma_v13.csv`.

Para adicionar um novo ano, inclua uma entrada em `CONFIGURACAO_ANOS` no início do arquivo:

```python
{
    "ano": "2021",
    "processos_licitatorios": os.path.join(BASE_DIR, "Processos Licitatórios-2021"),
    ...
}
```

### 5. Calcular correlações (`calcularCorrelacoes.py`)

```bash
python calcularCorrelacoes.py
```

Gera a tabela `correlacoesVariaveis/correlacoes_criciuma.csv` e o gráfico `grafico_correlacoes.png`.

## Base final — `base_unificada_criciuma_v13.csv`

| Característica | Valor |
|---|---|
| Unidade de análise | 1 linha = 1 item vencedor de licitação |
| Total de registros | 21.895 |
| Total de colunas | 48 |
| Licitações únicas | 5.990 |
| Anos cobertos | 2019 e 2020 |
| Separador de campo | `;` |
| Separador decimal | `,` (padrão pt-BR, compatível com Excel) |
| Encoding | UTF-8 com BOM (`utf-8-sig`) |

### Dicionário de colunas

#### Identificação do item

| Coluna | Descrição |
|---|---|
| `chave_licitacao` | Chave única da licitação: `{numeroLicitacao}_{ano}` |
| `numero` | Número da licitação |
| `codigo` | Código de catálogo do item (0 = sem código atribuído pelo portal) |
| `descricao` | Descrição do item licitado |
| `cnpjCpfVencedor` | CNPJ/CPF do fornecedor vencedor |
| `participanteVencedor` | Razão social do fornecedor vencedor |
| `quantidade` | Quantidade licitada |
| `unidadeMedida` | Unidade de medida |
| `origem_arquivo` | UUID do arquivo-fonte no portal |
| `_fonte` | Pasta/ano de origem (`licit_2019`, `finalizado_2020`, etc.) |

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
| `economia_absoluta` | `valorEstimado − valorHomologado` (R$) |
| `economia_pct` | `economia_absoluta / valorEstimado × 100` (%) |
| `qtd_participantes` | Número de empresas participantes |
| `houve_disputa` | Flag: `1` se mais de 1 participante, `0` caso contrário |
| `dias_tramitacao` | Dias entre publicação e homologação |
| `log_dias_tramitacao` | `log(dias_tramitacao + 1)` |
| `interact_part_logval` | `qtd_participantes × log(valorEstimado + 1)` |
| `formaJulgamento_cod` | Codificação numérica de `formaJulgamento` |

#### Contratos vinculados

| Coluna | Descrição |
|---|---|
| `qtd_contratos` | Número de contratos derivados da licitação |
| `media_valorInicial` | Média dos valores iniciais dos contratos (R$) |
| `media_valorFinal` | Média dos valores finais dos contratos (R$) |
| `media_dias_vigencia` | Média dos dias de vigência dos contratos |
| `media_variacao_contr` | Variação percentual média dos contratos (aditivos) |

#### Execução financeira (empenhos)

| Coluna | Descrição |
|---|---|
| `soma_valorEmpenho` | Total empenhado vinculado à licitação (R$) |
| `soma_valorLiquidadoEmpenho` | Total liquidado (R$) |
| `soma_valorPagoEmpenho` | Total pago (R$) |
| `qtd_empenhos` | Número de empenhos gerados |
| `orgao_principal` | Secretaria/Órgão responsável pela despesa |
| `programa_principal` | Programa orçamentário principal |
| `funcao_principal` | Função orçamentária (saúde, educação, urbanismo, etc.) |
| `unidade_principal` | Unidade orçamentária |

#### Agregados de itens por licitação

| Coluna | Descrição |
|---|---|
| `media_desconto_item` | Média de `economia_item_pct` dos itens da licitação (após clamp) |
| `amplitude_desconto_item` | `max − min` de `economia_item_pct` por licitação (após clamp; máx. 200 p.p.) |

#### Risco

| Coluna | Descrição |
|---|---|
| `contratado_sancionado` | Flag: `1` se o vencedor consta na lista de fornecedores sancionados |

## Variável alvo da análise de correlações

**`razao_pago_homolog`** = `soma_valorPagoEmpenho / valorHomologado`

Mede a **eficiência da execução financeira**: proporção do valor contratado que foi efetivamente pago. Disponível para 424 licitações (das 5.990 com dados de empenho e homologação).

### Resultado das correlações (25 variáveis)

18 das 25 variáveis candidatas atingem o critério |Spearman| ≥ 0,3:

| # | Variável | Spearman | Interpretação |
|---|---|---|---|
| 01 | `soma_valorPagoEmpenho` | +0,55 | Total pago (componente do numerador) |
| 02 | `soma_valorLiquidadoEmpenho` | +0,53 | Total liquidado (estágio anterior ao pagamento) |
| 03 | `valor_por_item` | −0,49 | Contratos de alto valor unitário têm execução mais lenta |
| 04 | `log_valor_por_item` | −0,49 | idem (escala log) |
| 05 | `valorHomologado` | −0,44 | Contratos maiores têm menor taxa de execução |
| 06 | `log_valorHomologado` | −0,44 | idem (escala log) |
| 07 | `valorEstimado` | −0,44 | Correlacionado com valorHomologado |
| 08 | `log_valorEstimado` | −0,44 | idem (escala log) |
| 09 | `log_economia_absoluta` | −0,37 | Maior economia gerada → menor execução proporcional |
| 10 | `orgao_principal_cod` | −0,35 | Secretaria responsável afeta o ritmo de execução |
| 11 | `amplitude_desconto_item` | +0,34 | Maior heterogeneidade de preços → melhor execução |
| 12 | `n_vencedores` | +0,34 | Mais fornecedores distintos → execução mais fragmentada/completa |
| 13 | `log_n_vencedores` | +0,34 | idem (escala log) |
| 14 | `qtd_itens` | +0,34 | Processos com mais itens executam mais |
| 15 | `log_qtd_itens` | +0,34 | idem (escala log) |
| 16 | `economia_absoluta` | −0,32 | Maior economia → menor execução relativa |
| 17 | `soma_ref` | +0,31 | Soma dos preços de referência dos itens |
| 18 | `soma_venc` | +0,31 | Soma dos preços vencedores dos itens |

As 7 variáveis restantes (competição e tipo de gasto) ficaram abaixo de 0,3, mas são teoricamente relevantes para a pergunta-problema.

## Decisões metodológicas relevantes

- **Unidade de análise da base**: item vencedor (1 linha = 1 item). Para correlações, agrega-se ao nível de licitação.
- **`codigo == 0`**: esperado — o portal não atribui código de catálogo a contratos de uso de espaços (ex.: parques, centros culturais). Os valores financeiros são válidos.
- **Clamp de `economia_item_pct`**: limitado a [−100%, 100%] antes de calcular `media_desconto_item` e `amplitude_desconto_item`, pois itens com `valorTotalReferencia = 1,00` (placeholder do portal) geram percentuais de milhões de pontos.
- **Deduplicação entre "Processos Licitatórios" e "Processos Licitatórios Finalizados"**: o portal publica o mesmo conjunto de licitações em duas seções; o pipeline mantém apenas uma cópia priorizando a versão "Finalizada".
- **Separador decimal no CSV**: vírgula (`,`) para compatibilidade nativa com Excel em locale pt-BR.

## Dependências

```
pandas
scipy      # instalado como dependência do pandas ou separadamente
numpy      # instalado como dependência do pandas
matplotlib # para geração do gráfico
```

Instalar com:

```bash
pip install -r requirements.txt
```
