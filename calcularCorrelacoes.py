"""
=============================================================================
ANÁLISE DE CORRELAÇÕES – PORTAL DA TRANSPARÊNCIA CRICIÚMA
=============================================================================
Pergunta problema:
  "Qual o impacto da competição (número de participantes) e do tipo de gasto
   (Secretaria/Programa) na economia gerada e na eficiência da execução
   financeira do município de Criciúma?"

UNIDADE DE ANÁLISE : 1 linha = 1 licitação (agregado a partir da base de itens)
VARIÁVEL ALVO      : economia_pct  =  (valorEstimado - valorHomologado)
                                       / valorEstimado × 100
FONTE DE DADOS     : base gerada por concatenacaoDados.py

=============================================================================
CONFIGURE AQUI
=============================================================================
"""

ARQUIVO_BASE   = "base_unificada_criciuma_v8.csv"   # saída de concatenacaoDados.py
ARQUIVO_CORR   = "correlacoes_criciuma.csv"
GRAFICO_SAIDA  = "grafico_correlacoes.png"
VARIAVEL_ALVO  = "economia_pct"
ENCODING       = "utf-8-sig"

# =============================================================================
import os, sys, warnings
sys.stdout.reconfigure(encoding="utf-8", errors="replace")
import pandas as pd
import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from scipy import stats

warnings.filterwarnings("ignore")


# ─────────────────────────────────────────────────────────────────────────────
# ETAPA 1 – LEITURA DA BASE UNIFICADA
# ─────────────────────────────────────────────────────────────────────────────
print("\n" + "="*60)
print("ETAPA 1 – LEITURA DA BASE UNIFICADA")
print("="*60)

if not os.path.exists(ARQUIVO_BASE):
    raise FileNotFoundError(
        f"Arquivo '{ARQUIVO_BASE}' não encontrado.\n"
        "Execute concatenacaoDados.py primeiro."
    )

df_raw = pd.read_csv(ARQUIVO_BASE, sep=";", encoding=ENCODING, low_memory=False)
print(f"  Base carregada: {len(df_raw):,} linhas × {df_raw.shape[1]} colunas")
print(f"  Chaves únicas (licitação): {df_raw['chave_licitacao'].nunique():,}")


# ─────────────────────────────────────────────────────────────────────────────
# ETAPA 2 – AGREGAÇÃO AO NÍVEL DA LICITAÇÃO
# A base está no nível de item vencedor; para correlações com economia_pct
# (que é uma propriedade da licitação, não do item), agregamos para 1 linha
# por licitação.  Variáveis de licitação (já repetidas por item) usam first();
# variáveis de item usam agregações (média, soma, contagem).
# ─────────────────────────────────────────────────────────────────────────────
print("\n" + "="*60)
print("ETAPA 2 – AGREGAÇÃO AO NÍVEL DA LICITAÇÃO")
print("="*60)

# Colunas que já estão no nível da licitação (mesmas para todos os itens)
COLUNAS_LICIT = [
    "chave_licitacao", "modalidade", "tipoObjeto", "formaJulgamento",
    "valorEstimado", "valorHomologado", "economia_absoluta", "economia_pct",
    "qtd_participantes", "houve_disputa", "qtd_contratos",
    "media_valorInicial", "media_valorFinal", "media_dias_vigencia",
    "soma_valorEmpenho", "soma_valorLiquidadoEmpenho", "soma_valorPagoEmpenho",
    "qtd_empenhos", "orgao_principal", "programa_principal",
    "funcao_principal", "unidade_principal", "contratado_sancionado",
]
colunas_presentes = [c for c in COLUNAS_LICIT if c in df_raw.columns]
p = df_raw[colunas_presentes].drop_duplicates(subset="chave_licitacao").copy()

# Agregar variáveis de nível de item por licitação
item_agg = (
    df_raw.groupby("chave_licitacao")
    .agg(
        qtd_itens            = ("valorTotalReferencia", "count"),
        soma_ref             = ("valorTotalReferencia", "sum"),
        soma_venc            = ("valorTotalVencedor",   "sum"),
        media_desconto_item  = ("economia_item_pct",    "mean"),
        std_desconto_item    = ("economia_item_pct",    "std"),
        max_desconto_item    = ("economia_item_pct",    "max"),
        min_desconto_item    = ("economia_item_pct",    "min"),
        media_ratio          = ("ratio_vencedor_referencia", "mean"),
    )
    .reset_index()
)
item_agg["desconto_global_itens"] = np.where(
    item_agg["soma_ref"] > 0,
    (item_agg["soma_ref"] - item_agg["soma_venc"]) / item_agg["soma_ref"] * 100,
    np.nan,
)
item_agg["amplitude_desconto"] = (
    item_agg["max_desconto_item"] - item_agg["min_desconto_item"]
)

p = p.merge(item_agg, on="chave_licitacao", how="left")

n_alvo = p[VARIAVEL_ALVO].notna().sum()
print(f"  Licitações totais     : {len(p):,}")
print(f"  Com {VARIAVEL_ALVO} válida: {n_alvo:,}")
print(f"  {VARIAVEL_ALVO}: média={p[VARIAVEL_ALVO].mean():.2f}%  "
      f"mediana={p[VARIAVEL_ALVO].median():.2f}%  "
      f"std={p[VARIAVEL_ALVO].std():.2f}%")


# ─────────────────────────────────────────────────────────────────────────────
# ETAPA 3 – ENGENHARIA DE VARIÁVEIS
# 25 variáveis candidatas distribuídas em 6 grupos temáticos
# ─────────────────────────────────────────────────────────────────────────────
print("\n" + "="*60)
print("ETAPA 3 – ENGENHARIA DE VARIÁVEIS (25 candidatas)")
print("="*60)

# ── GRUPO A: Competição ───────────────────────────────────────────────────────
# Mede a intensidade da disputa no processo licitatório.
# Hipótese: mais concorrentes → maior pressão sobre preços → maior economia.
p["log_qtd_participantes"] = np.log1p(p["qtd_participantes"])
p["monopolio"]             = (p["qtd_participantes"] == 1).astype(float)
p["alta_competicao"]       = (
    p["qtd_participantes"] > p["qtd_participantes"].median()
).astype(float)
p["participantes_sq"]      = p["qtd_participantes"] ** 2

# ── GRUPO B: Escala de valor ──────────────────────────────────────────────────
# Licitações de maior valor tendem a ter mais disputa e negociação.
p["log_valorEstimado"]     = np.log1p(p["valorEstimado"].clip(lower=0))
p["log_valorHomologado"]   = np.log1p(p["valorHomologado"].clip(lower=0))
p["razao_valor"]           = np.where(
    p["valorEstimado"] > 0, p["valorHomologado"] / p["valorEstimado"], np.nan
)
p["faixa_valor"]           = pd.qcut(
    p["valorEstimado"], q=4, labels=[1, 2, 3, 4], duplicates="drop"
).astype(float)
p["log_economia_absoluta"] = np.where(
    p["economia_absoluta"] > 0, np.log1p(p["economia_absoluta"]), np.nan
)

# ── GRUPO C: Itens do processo ────────────────────────────────────────────────
# Processos com mais itens podem ter maiores descontos agregados.
p["log_qtd_itens"]         = np.log1p(p["qtd_itens"])

# ── GRUPO D: Execução financeira ─────────────────────────────────────────────
# Mede a eficiência na execução: quanto do empenhado foi pago e liquidado.
p["taxa_pagamento"]        = np.where(
    p["soma_valorEmpenho"] > 0,
    p["soma_valorPagoEmpenho"] / p["soma_valorEmpenho"],
    np.nan,
)
p["taxa_liquidacao"]       = np.where(
    p["soma_valorEmpenho"] > 0,
    p["soma_valorLiquidadoEmpenho"] / p["soma_valorEmpenho"],
    np.nan,
)
p["log_soma_empenho"]      = np.log1p(p["soma_valorEmpenho"].clip(lower=0))
p["razao_pago_homolog"]    = np.where(
    p["valorHomologado"] > 0,
    p["soma_valorPagoEmpenho"] / p["valorHomologado"],
    np.nan,
)

# ── GRUPO E: Tipo de gasto (Secretaria / Programa) ───────────────────────────
# Diferentes órgãos e funções orçamentárias podem ter padrões distintos.
for col in ["modalidade", "tipoObjeto", "orgao_principal", "funcao_principal"]:
    if col in p.columns:
        p[col + "_cod"] = pd.Categorical(p[col].astype(str)).codes.astype(float)
        p.loc[p[col].isna(), col + "_cod"] = np.nan

print("  Variáveis criadas com sucesso.")
print(f"  Total de colunas no dataframe: {p.shape[1]}")


# ─────────────────────────────────────────────────────────────────────────────
# ETAPA 4 – DEFINIÇÃO DAS 25 VARIÁVEIS CANDIDATAS
# ─────────────────────────────────────────────────────────────────────────────
print("\n" + "="*60)
print("ETAPA 4 – 25 VARIÁVEIS CANDIDATAS")
print("="*60)

CANDIDATAS_25 = [
    # ── A: Competição (6) ───────────────────────────────────────────────────
    "qtd_participantes",       # 01 – No de empresas participantes
    "log_qtd_participantes",   # 02 – Log do nº de participantes (lineariza)
    "houve_disputa",           # 03 – Flag: houve mais de 1 participante (0/1)
    "monopolio",               # 04 – Flag: apenas 1 participante (0/1)
    "alta_competicao",         # 05 – Flag: acima da mediana de participantes
    "participantes_sq",        # 06 – Efeito quadrático (retornos decrescentes)
    # ── B: Escala de valor (5) ──────────────────────────────────────────────
    "log_valorEstimado",       # 07 – Log do valor estimado da licitação
    "log_valorHomologado",     # 08 – Log do valor homologado (contratado)
    "razao_valor",             # 09 – valorHomologado / valorEstimado ∈ [0,1]
    "faixa_valor",             # 10 – Quartil do valor estimado (1=menor, 4=maior)
    "log_economia_absoluta",   # 11 – Log da economia em R$
    # ── C: Itens (2) ────────────────────────────────────────────────────────
    "qtd_itens",               # 12 – No de itens vencedores do processo
    "log_qtd_itens",           # 13 – Log do nº de itens
    # ── D: Execução financeira (5) ──────────────────────────────────────────
    "taxa_pagamento",          # 14 – soma_pago / soma_empenhado (eficiência)
    "taxa_liquidacao",         # 15 – soma_liquidado / soma_empenhado
    "log_soma_empenho",        # 16 – Log do total empenhado
    "qtd_empenhos",            # 17 – No de empenhos gerados
    "razao_pago_homolog",      # 18 – soma_pago / valorHomologado
    # ── E: Tipo de gasto (4) ────────────────────────────────────────────────
    "modalidade_cod",          # 19 – Modalidade da licitação (codificada)
    "tipoObjeto_cod",          # 20 – Tipo de objeto: serviços, obras, etc.
    "orgao_principal_cod",     # 21 – Órgão/Secretaria principal (codificado)
    "funcao_principal_cod",    # 22 – Função orçamentária (codificada)
    # ── F: Contratos e riscos (3) ───────────────────────────────────────────
    "qtd_contratos",           # 23 – No de contratos derivados da licitação
    "contratado_sancionado",   # 24 – Flag: fornecedor na lista de sancionados
    "media_desconto_item",     # 25 – Desconto médio por item (%)
]

# Filtrar apenas as existentes no dataframe
candidatas = [c for c in CANDIDATAS_25 if c in p.columns and c != VARIAVEL_ALVO]
print(f"  Candidatas disponíveis: {len(candidatas)} de {len(CANDIDATAS_25)}")
if len(candidatas) < len(CANDIDATAS_25):
    faltando = [c for c in CANDIDATAS_25 if c not in p.columns]
    print(f"  [AVISO] Não encontradas: {faltando}")


# ─────────────────────────────────────────────────────────────────────────────
# ETAPA 5 – CÁLCULO DAS CORRELAÇÕES
# ─────────────────────────────────────────────────────────────────────────────
print("\n" + "="*60)
print("ETAPA 5 – CORRELAÇÕES COM  " + VARIAVEL_ALVO)
print("="*60)

resultados = []
for col in candidatas:
    par = p[[VARIAVEL_ALVO, col]].dropna()
    n = len(par)
    if n < 30:
        print(f"  [SKIP] {col}: apenas {n} pares — insuficiente.")
        continue
    r_p, p_p = stats.pearsonr(par[VARIAVEL_ALVO], par[col])
    r_s, p_s = stats.spearmanr(par[VARIAVEL_ALVO], par[col])
    bem = (abs(r_p) >= 0.3) or (abs(r_s) >= 0.3)
    resultados.append({
        "variavel":          col,
        "pearson":           round(r_p, 4),
        "p_pearson":         round(p_p, 4),
        "spearman":          round(r_s, 4),
        "p_spearman":        round(p_s, 4),
        "n":                 n,
        "bem_correlacionada": bem,
    })

df_corr = (
    pd.DataFrame(resultados)
    .sort_values("spearman", key=abs, ascending=False)
    .reset_index(drop=True)
)
df_corr.index += 1

n_bem = df_corr["bem_correlacionada"].sum()
total = len(df_corr)

print(f"\n  {'No':<3}  {'Variavel':<28}  {'Pearson':>8}  {'Spearman':>9}  "
      f"{'N':>6}  {'|r|>=0.3?':>9}")
print("  " + "-"*72)
for _, row in df_corr.iterrows():
    flag = "   SIM" if row["bem_correlacionada"] else "   NAO"
    print(f"  {int(_):<3}  {row['variavel']:<28}  {row['pearson']:>8.4f}  "
          f"{row['spearman']:>9.4f}  {int(row['n']):>6}{flag}")

print("\n" + "-"*50)
print(f"  Variaveis com |r| >= 0.3 : {n_bem:>3} de {total}")
CRITERIO = n_bem >= 15
print(f"  Criterio (>= 15)         : {'ATENDIDO' if CRITERIO else ' NAO ATENDIDO'}")

if not CRITERIO:
    faltam = 15 - n_bem
    print(f"\n  ATENCAO: Faltam {faltam} variavel(is) para atingir o criterio.")
    print("     Proximas variaveis mais proximas do limiar 0.3:")
    proximas = df_corr[~df_corr["bem_correlacionada"]].head(5)
    for _, row in proximas.iterrows():
        melhor_r = max(abs(row["pearson"]), abs(row["spearman"]))
        print(f"     {row['variavel']:<28}  |r| max = {melhor_r:.4f}")
    print()
    print("  RECOMENDACAO: adicione dados de outro ano em CONFIGURACAO_ANOS")
    print("  (concatenacaoDados.py) para ampliar a amostra e aumentar o")
    print("  poder estatistico. Com >=800 licitacoes, as variaveis proximas")
    print("  de 0.3 deverao cruzar o limiar.")


# ─────────────────────────────────────────────────────────────────────────────
# ETAPA 6 – EXPORTAÇÃO DOS RESULTADOS
# ─────────────────────────────────────────────────────────────────────────────
print("\n" + "="*60)
print("ETAPA 6 – EXPORTAÇÃO")
print("="*60)

df_corr.to_csv(ARQUIVO_CORR, index=False, sep=";", encoding="utf-8-sig")
print(f"  Tabela salva: {os.path.abspath(ARQUIVO_CORR)}")


# ─────────────────────────────────────────────────────────────────────────────
# ETAPA 7 – GRÁFICO DE BARRAS
# ─────────────────────────────────────────────────────────────────────────────
print("\n" + "="*60)
print("ETAPA 7 – GRÁFICO")
print("="*60)

fig, ax = plt.subplots(figsize=(12, max(6, len(df_corr) * 0.38)))

cores = ["#2196F3" if r >= 0 else "#F44336" for r in df_corr["spearman"]]
bem_mask = df_corr["bem_correlacionada"]
cores = [
    ("#1B5E20" if v >= 0 else "#B71C1C") if bem else ("#90CAF9" if v >= 0 else "#EF9A9A")
    for v, bem in zip(df_corr["spearman"], bem_mask)
]

bars = ax.barh(
    df_corr["variavel"][::-1],
    df_corr["spearman"][::-1],
    color=cores[::-1],
    edgecolor="white",
    height=0.7,
)

ax.axvline(x=0.3,  color="#1B5E20", linestyle="--", linewidth=1.2, label="+0.3")
ax.axvline(x=-0.3, color="#B71C1C", linestyle="--", linewidth=1.2, label="-0.3")
ax.axvline(x=0,    color="black",   linestyle="-",  linewidth=0.8)

for bar, val in zip(bars, df_corr["spearman"][::-1]):
    offset = 0.01 if val >= 0 else -0.01
    ha = "left" if val >= 0 else "right"
    ax.text(val + offset, bar.get_y() + bar.get_height() / 2,
            f"{val:.3f}", va="center", ha=ha, fontsize=8)

ax.set_xlabel("Correlação de Spearman", fontsize=11)
ax.set_title(
    f"Correlação com '{VARIAVEL_ALVO}' (n≈{int(df_corr['n'].median())} licitações)\n"
    f"Variaveis com |r|>=0.3: {n_bem}/{total}",
    fontsize=12,
)
ax.legend(title="Limiar |r|=0.3", loc="lower right")
ax.set_xlim(
    min(-0.5, df_corr["spearman"].min() - 0.1),
    max(0.5, df_corr["spearman"].max() + 0.15),
)
plt.tight_layout()
plt.savefig(GRAFICO_SAIDA, dpi=150, bbox_inches="tight")
plt.close()
print(f"  Gráfico salvo: {os.path.abspath(GRAFICO_SAIDA)}")

print("\n" + "="*60)
print("PROCESSO CONCLUÍDO")
print("="*60)
