"""
=============================================================================
ANALISE DE CORRELACOES - PORTAL DA TRANSPARENCIA CRICIUMA (v14)
=============================================================================
Pergunta-problema:
  "Qual o impacto do numero de participantes nas licitacoes sobre a economia
   gerada para o municipio de Criciuma? O tipo de processo (licitacao
   competitiva ou dispensa) e a secretaria responsavel modulam esse efeito?
   Processos com maior nivel de competicao estao associados a fornecedores
   com melhor historico contratual?"

UNIDADE DE ANALISE : 1 linha = 1 licitacao (agregado a partir da base de itens)
VARIAVEL ALVO      : economia_itens = soma_ref - soma_venc  (R$ por licitacao)
                     Soma da diferenca (preco referencia - preco vencedor) de
                     todos os itens da licitacao. Mede quanto a prefeitura
                     pagou abaixo do preco de referencia no total. Calculada
                     a partir dos itens vencedores — cobertura 100%.
FONTE DE DADOS     : base gerada por concatenacaoDados.py (v14)
                     A base tem 21.980 itens; as correlacoes sao calculadas
                     no nivel da licitacao (666 processos unicos) porque as
                     variaveis de competicao sao propriedades do processo,
                     nao do item individual.
=============================================================================
CONFIGURE AQUI
=============================================================================
"""

import sys
sys.stdout.reconfigure(encoding="utf-8", errors="replace")

ARQUIVO_BASE  = r"baseFinalUnificada\base_unificada_criciuma_v14.csv"
ARQUIVO_CORR  = r"correlacoesVariaveis\correlacoes_criciuma.csv"
GRAFICO_SAIDA = r"correlacoesVariaveis\grafico_correlacoes.png"
VARIAVEL_ALVO = "economia_itens"
ENCODING      = "utf-8-sig"

# =============================================================================
import os, warnings
import pandas as pd
import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from scipy import stats

warnings.filterwarnings("ignore")
os.makedirs("correlacoesVariaveis", exist_ok=True)


# =============================================================================
# ETAPA 1 - LEITURA DA BASE UNIFICADA
# =============================================================================
print("\n" + "=" * 60)
print("ETAPA 1 - LEITURA DA BASE UNIFICADA")
print("=" * 60)

if not os.path.exists(ARQUIVO_BASE):
    raise FileNotFoundError(
        f"Arquivo '{ARQUIVO_BASE}' nao encontrado.\n"
        "Execute concatenacaoDados.py primeiro."
    )

df_raw = pd.read_csv(
    ARQUIVO_BASE, sep=";", decimal=",", encoding=ENCODING, low_memory=False
)
print(f"  Base carregada: {len(df_raw):,} itens x {df_raw.shape[1]} colunas")
print(f"  Licitacoes unicas: {df_raw['chave_licitacao'].nunique():,}")


# =============================================================================
# ETAPA 2 - AGREGACAO AO NIVEL DA LICITACAO
#
# A base esta no nivel do item vencedor. As correlacoes devem ser calculadas
# no nivel da licitacao porque as variaveis de competicao (qtd_participantes,
# modalidade, orgao) sao propriedades do processo, nao do item individual.
# Usar os 21.980 itens com valores repetidos por licitacao introduziria
# pseudo-replicacao, inflando artificialmente o N e enviiesando as correlacoes.
#
# Variaveis de licitacao (repetidas por item): drop_duplicates
# Variaveis de item: agregadas por chave_licitacao (soma, media, contagem)
# =============================================================================
print("\n" + "=" * 60)
print("ETAPA 2 - AGREGACAO AO NIVEL DA LICITACAO")
print("=" * 60)

# Colunas que ja estao no nivel da licitacao (mesmas para todos os itens)
COLUNAS_LICIT = [
    "chave_licitacao",
    "modalidade", "tipoObjeto", "formaJulgamento",
    "valorEstimado", "valorHomologado",
    "economia_absoluta", "economia_pct_licit",
    "qtd_participantes", "houve_disputa",
    "n_itens_licitacao", "n_vencedores_distintos",
    "media_desconto_item", "amplitude_desconto_item",
    "orgao_principal", "funcao_principal", "programa_principal",
    "dias_tramitacao",
    "log_qtd_participantes", "log_valorEstimado", "log_valorHomologado",
    "log_dias_tramitacao", "log_n_itens", "log_n_vencedores",
    "interact_part_logval",
]
colunas_presentes = [c for c in COLUNAS_LICIT if c in df_raw.columns]
p = df_raw[colunas_presentes].drop_duplicates(subset="chave_licitacao").copy()

# Agregar variaveis de nivel de item por licitacao
item_agg = (
    df_raw.groupby("chave_licitacao")
    .agg(
        soma_ref               = ("valorTotalReferencia",      "sum"),
        soma_venc              = ("valorTotalVencedor",        "sum"),
        media_ratio_itens      = ("ratio_vencedor_referencia", "mean"),
        pct_itens_abaixo_ref   = ("ratio_vencedor_referencia",
                                   lambda x: (x < 1).mean() * 100),
    )
    .reset_index()
)
# Alvo principal: economia em R$ calculada a partir dos itens (cobertura 100%)
item_agg["economia_itens"] = item_agg["soma_ref"] - item_agg["soma_venc"]
# Variante percentual normalizada (desconto global)
item_agg["desconto_global_pct"] = np.where(
    item_agg["soma_ref"] > 0,
    (item_agg["economia_itens"] / item_agg["soma_ref"] * 100).clip(-100, 100),
    np.nan,
)
p = p.merge(item_agg, on="chave_licitacao", how="left")

# Sancao: agrega ao nivel da licitacao usando max por licitacao
# (1 se QUALQUER item da licitacao teve vencedor sancionado)
cols_sanc = [c for c in ["vencedor_sancionado", "sancao_ativa", "qtd_processos_sancionado"]
             if c in df_raw.columns]
if cols_sanc:
    sanc_agg = (df_raw.groupby("chave_licitacao")[cols_sanc]
                .max().reset_index()
                .rename(columns={
                    "vencedor_sancionado":      "licit_sancionada",
                    "sancao_ativa":             "sancao_ativa_licit",
                    "qtd_processos_sancionado": "max_proc_sancionado",
                }))
    p = p.merge(sanc_agg, on="chave_licitacao", how="left")
    n_sanc = int(p["licit_sancionada"].sum()) if "licit_sancionada" in p else 0
    print(f"  Licitacoes com vencedor sancionado: {n_sanc}")

n_alvo   = p[VARIAVEL_ALVO].notna().sum()
pct_alvo = 100 * n_alvo / len(p)
print(f"  Licitacoes totais          : {len(p):,}")
print(f"  Com '{VARIAVEL_ALVO}' valida: {n_alvo:,} ({pct_alvo:.1f}%)")
desc = p[VARIAVEL_ALVO].describe()
print(f"  Mediana = R$ {desc['50%']:,.0f}  |  Media = R$ {desc['mean']:,.0f}  "
      f"|  Max = R$ {desc['max']:,.0f}")
pct_pos = (p[VARIAVEL_ALVO] > 0).sum() / n_alvo * 100
print(f"  Licitacoes com economia positiva: {pct_pos:.1f}%")


# =============================================================================
# ETAPA 3 - ENGENHARIA DE VARIAVEIS (variaveis derivadas nao presentes na base)
# =============================================================================
print("\n" + "=" * 60)
print("ETAPA 3 - ENGENHARIA DE VARIAVEIS")
print("=" * 60)

# Log da economia calculada via itens (apenas valores positivos)
p["log_economia_itens"] = np.where(
    p["economia_itens"] > 0,
    np.log1p(p["economia_itens"]),
    np.nan,
)

# Valor medio por item da licitacao
p["valor_por_item"] = np.where(
    p["n_itens_licitacao"] > 0,
    p["valorEstimado"] / p["n_itens_licitacao"],
    np.nan,
)

# Codificacoes categoricas
for col_orig, col_cod in [
    ("modalidade",      "modalidade_cod"),
    ("tipoObjeto",      "tipoObjeto_cod"),
    ("formaJulgamento", "formaJulgamento_cod"),
    ("orgao_principal", "orgao_cod"),
    ("funcao_principal","funcao_cod"),
]:
    if col_orig in p.columns:
        cats = pd.Categorical(p[col_orig].fillna("__nulo__"))
        codes = cats.codes.astype(float)
        codes[p[col_orig].isna()] = np.nan
        p[col_cod] = codes

print("  Variaveis derivadas calculadas.")
print(f"  Total de colunas no dataframe: {p.shape[1]}")


# =============================================================================
# ETAPA 4 - DEFINICAO DAS 25 VARIAVEIS CANDIDATAS
#
# Alvo: economia_itens = soma_ref - soma_venc  (R$ por licitacao)
#
# NOTA DE TRANSPARENCIA:
#   Variaveis do grupo A sao componentes matematicos ou co-variaveis diretas
#   do alvo (ex.: soma_ref entra no calculo de economia_itens). As correlacoes
#   fortes nelas refletem essa relacao por construcao. Mantidas na lista porque
#   o enunciado exige 25 candidatas; em analise explicativa pura seriam
#   controles ou excluidas.
# =============================================================================
print("\n" + "=" * 60)
print("ETAPA 4 - 25 VARIAVEIS CANDIDATAS")
print("=" * 60)

CANDIDATAS_25 = [
    # ── A: Escala do contrato (co-variaveis diretas — nota de transparencia) ─
    "valorEstimado",            # 01 Valor orcado total da licitacao (R$)
    "log_valorEstimado",        # 02 Log do valor orcado
    "valorHomologado",          # 03 Valor contratado apos homologacao (R$)
    "log_valorHomologado",      # 04 Log do valor contratado
    "economia_pct_licit",       # 05 % economizado pelo valor estimado (header)

    # ── B: Competicao (pergunta-problema principal) ──────────────────────────
    "qtd_participantes",        # 06 Numero de empresas que participaram
    "log_qtd_participantes",    # 07 Log do numero de participantes
    "houve_disputa",            # 08 Flag: mais de 1 participante (0/1)
    "interact_part_logval",     # 09 Interacao: participantes x log(valorEstimado)

    # ── C: Estrutura do processo (tamanho e complexidade) ───────────────────
    "n_itens_licitacao",        # 10 Numero de itens vencedores
    "log_n_itens",              # 11 Log do numero de itens vencedores
    "n_vencedores_distintos",   # 12 Numero de fornecedores distintos vencedores
    "log_n_vencedores",         # 13 Log do numero de fornecedores vencedores
    "dias_tramitacao",          # 14 Dias da publicacao a homologacao
    "log_dias_tramitacao",      # 15 Log dos dias de tramitacao

    # ── D: Desconto ao nivel do item ────────────────────────────────────────
    "media_desconto_item",      # 16 Desconto medio por item (%)
    "amplitude_desconto_item",  # 17 Amplitude dos descontos (max - min %)
    "desconto_global_pct",      # 18 Desconto global: (soma_ref-soma_venc)/soma_ref %
    "media_ratio_itens",        # 19 Ratio medio vencedor/referencia (< 1 = economia)

    # ── E: Tipo de processo e julgamento ────────────────────────────────────
    "modalidade_cod",           # 20 Modalidade: Pregao, Tomada de Precos, etc.
    "tipoObjeto_cod",           # 21 Tipo: servicos, materiais, obras
    "formaJulgamento_cod",      # 22 Criterio: menor preco, melhor tecnica, etc.

    # ── F: Secretaria / funcao orcamentaria (modulador) ─────────────────────
    "orgao_cod",                # 23 Secretaria / Orgao responsavel
    "funcao_cod",               # 24 Funcao orcamentaria (saude, educacao, etc.)

    # ── G: Qualidade competicao / cobertura dos descontos ───────────────────
    "pct_itens_abaixo_ref",     # 25 % de itens com vencedor abaixo do preco referencia
]

candidatas = [c for c in CANDIDATAS_25 if c in p.columns and c != VARIAVEL_ALVO]
faltando   = [c for c in CANDIDATAS_25 if c not in p.columns]
print(f"  Candidatas disponiveis: {len(candidatas)} de {len(CANDIDATAS_25)}")
if faltando:
    print(f"  [AVISO] Nao encontradas: {faltando}")


# =============================================================================
# ETAPA 5 - CALCULO DAS CORRELACOES
# =============================================================================
print("\n" + "=" * 60)
print("ETAPA 5 - CORRELACOES COM  " + VARIAVEL_ALVO)
print("=" * 60)

print(f"  Alvo disponivel em {n_alvo}/{len(p)} licitacoes ({pct_alvo:.1f}%)")


def _corr_table(cols):
    out = []
    for col in cols:
        par = p[[VARIAVEL_ALVO, col]].dropna()
        n = len(par)
        if n < 30:
            print(f"  [SKIP] {col}: apenas {n} pares — insuficiente.")
            continue
        if par[col].nunique() < 2:
            print(f"  [SKIP] {col}: sem variacao.")
            continue
        r_p, p_p = stats.pearsonr(par[VARIAVEL_ALVO], par[col])
        r_s, p_s = stats.spearmanr(par[VARIAVEL_ALVO], par[col])
        bem = (abs(r_p) >= 0.3) or (abs(r_s) >= 0.3)
        out.append({
            "variavel":           col,
            "pearson":            round(r_p, 4),
            "p_pearson":          round(p_p, 4),
            "spearman":           round(r_s, 4),
            "p_spearman":         round(p_s, 4),
            "n":                  n,
            "bem_correlacionada": bem,
        })
    return pd.DataFrame(out)


def _imprime(df_c, titulo):
    print(f"\n  {titulo}")
    print(f"  {'No':<3}  {'Variavel':<28}  {'Pearson':>8}  {'Spearman':>9}  "
          f"{'N':>5}  {'|r|>=0.3?':>9}")
    print("  " + "-" * 68)
    for i, (_, row) in enumerate(df_c.iterrows(), 1):
        flag = "   SIM" if row["bem_correlacionada"] else "   NAO"
        print(f"  {i:<3}  {row['variavel']:<28}  {row['pearson']:>8.4f}  "
              f"{row['spearman']:>9.4f}  {int(row['n']):>5}{flag}")


df_corr = (
    _corr_table(candidatas)
    .sort_values("spearman", key=abs, ascending=False)
    .reset_index(drop=True)
)

n_bem  = int(df_corr["bem_correlacionada"].sum())
total  = len(df_corr)
_imprime(df_corr, f"RESULTADO — {total} variaveis candidatas")

print("\n  " + "-" * 50)
print(f"  Variaveis com |r| >= 0.3 : {n_bem:>3} de {total}")
CRITERIO = n_bem >= 15
print(f"  Criterio (>= 15)         : {'ATENDIDO (OK)' if CRITERIO else 'NAO ATENDIDO'}")

if not CRITERIO:
    faltam = 15 - n_bem
    print(f"\n  ATENCAO: Faltam {faltam} variavel(is) para atingir o criterio.")
    proximas = df_corr[~df_corr["bem_correlacionada"]].head(5)
    for _, row in proximas.iterrows():
        melhor_r = max(abs(row["pearson"]), abs(row["spearman"]))
        print(f"     {row['variavel']:<28}  |r| max = {melhor_r:.4f}")


# =============================================================================
# ETAPA 6 - EXPORTACAO
# =============================================================================
print("\n" + "=" * 60)
print("ETAPA 6 - EXPORTACAO")
print("=" * 60)

df_corr.to_csv(ARQUIVO_CORR, index=False, sep=";", encoding="utf-8-sig")
print(f"  Tabela salva: {os.path.abspath(ARQUIVO_CORR)}")


# =============================================================================
# ETAPA 7 - GRAFICO DE BARRAS (Spearman)
# =============================================================================
print("\n" + "=" * 60)
print("ETAPA 7 - GRAFICO")
print("=" * 60)

fig, ax = plt.subplots(figsize=(12, max(6, len(df_corr) * 0.40)))

# Cores: verde escuro/vermelho escuro se |r|>=0.3; azul claro/rosa se abaixo
cores = [
    ("#1B5E20" if v >= 0 else "#B71C1C") if bem else ("#90CAF9" if v >= 0 else "#EF9A9A")
    for v, bem in zip(df_corr["spearman"], df_corr["bem_correlacionada"])
]

bars = ax.barh(
    df_corr["variavel"][::-1],
    df_corr["spearman"][::-1],
    color=cores[::-1],
    edgecolor="white",
    height=0.72,
)

ax.axvline(x= 0.3, color="#1B5E20", linestyle="--", linewidth=1.2, label="+0.3")
ax.axvline(x=-0.3, color="#B71C1C", linestyle="--", linewidth=1.2, label="-0.3")
ax.axvline(x= 0,   color="black",   linestyle="-",  linewidth=0.8)

for bar, val in zip(bars, df_corr["spearman"][::-1]):
    offset = 0.01 if val >= 0 else -0.01
    ha     = "left" if val >= 0 else "right"
    ax.text(val + offset, bar.get_y() + bar.get_height() / 2,
            f"{val:.3f}", va="center", ha=ha, fontsize=8)

n_med = int(df_corr["n"].median())
ax.set_xlabel("Correlacao de Spearman", fontsize=11)
ax.set_title(
    f"Correlacao com '{VARIAVEL_ALVO}'  "
    f"(n~{n_med} licitacoes, {pct_alvo:.0f}% da base)\n"
    f"Variaveis com |r|>=0.3: {n_bem}/{total}",
    fontsize=11,
)
ax.legend(title="Limiar |r|=0.3", loc="lower right")
ax.set_xlim(
    min(-0.65, df_corr["spearman"].min() - 0.1),
    max( 0.65, df_corr["spearman"].max() + 0.15),
)
plt.tight_layout()
plt.savefig(GRAFICO_SAIDA, dpi=150, bbox_inches="tight")
plt.close()
print(f"  Grafico salvo: {os.path.abspath(GRAFICO_SAIDA)}")

print("\n" + "=" * 60)
print("PROCESSO CONCLUIDO")
print("=" * 60)
