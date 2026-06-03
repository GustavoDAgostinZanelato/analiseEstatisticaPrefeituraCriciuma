"""
=============================================================================
PREVISAO COM O MODELO OLS — economia futura de novas licitacoes
=============================================================================
Pergunta-problema:
  "Qual o impacto do numero de participantes nas licitacoes sobre a economia
   gerada para o municipio de Criciuma?"

OBJETIVO:
  Usar o modelo OLS ja estimado (regressaoOLS.py) para PREVER a economia de
  novas licitacoes (ainda nao observadas) e fornecer o INTERVALO DE PREVISAO.

NOTA METODOLOGICA — "intervalo futuro":
  O modelo e TRANSVERSAL (nao tem variavel de tempo). Portanto "futuro" =
  uma NOVA licitacao, nao um ano a frente. O intervalo apropriado e o
  INTERVALO DE PREVISAO (prediction interval), que e mais largo que o
  intervalo de confianca da media porque soma duas fontes de incerteza:
    (1) incerteza na estimativa dos coeficientes (mesma do IC da media)
    (2) variabilidade aleatoria de uma observacao individual (residuo)

  Variavel alvo : log(economia_itens)  ->  retransformada para R$ via expm1()
  Cenarios      : variam qtd_participantes (baixa/tipica/alta competicao);
                  demais preditores fixados na MEDIANA da amostra.

Saidas:
  previsaoOLS/previsao_cenarios.csv
  previsaoOLS/grafico_previsao.png
=============================================================================
"""

import sys, os, warnings
sys.stdout.reconfigure(encoding="utf-8", errors="replace")
warnings.filterwarnings("ignore")

import numpy as np
import pandas as pd
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import statsmodels.api as sm

ARQUIVO_BASE = r"baseFinalUnificada\base_unificada_criciuma_v14.csv"
DIR_SAIDA    = "previsaoOLS"
CONFIANCA    = 0.95
os.makedirs(DIR_SAIDA, exist_ok=True)

# =============================================================================
# ETAPA 1 — REPRODUZIR A AMOSTRA E O MODELO DE regressaoOLS.py
# =============================================================================
print("\n" + "=" * 65)
print("ETAPA 1 — REESTIMACAO DO MODELO OLS")
print("=" * 65)

df_raw = pd.read_csv(ARQUIVO_BASE, sep=";", decimal=",",
                     encoding="utf-8-sig", low_memory=False)

COLUNAS_LICIT = [
    "chave_licitacao",
    "valorEstimado", "log_valorEstimado",
    "valorHomologado", "log_valorHomologado",
    "qtd_participantes", "log_qtd_participantes",
    "dias_tramitacao", "log_dias_tramitacao",
    "houve_disputa", "interact_part_logval",
    "economia_pct_licit", "media_desconto_item",
]
cols_ok = [c for c in COLUNAS_LICIT if c in df_raw.columns]
p = df_raw[cols_ok].drop_duplicates(subset="chave_licitacao").copy()

item_agg = (
    df_raw.groupby("chave_licitacao")
    .agg(
        soma_ref             = ("valorTotalReferencia",      "sum"),
        soma_venc            = ("valorTotalVencedor",        "sum"),
        media_ratio_itens    = ("ratio_vencedor_referencia", "mean"),
        pct_itens_abaixo_ref = ("ratio_vencedor_referencia",
                                 lambda x: (x < 1).mean() * 100),
    )
    .reset_index()
)
item_agg["economia_itens"] = item_agg["soma_ref"] - item_agg["soma_venc"]
item_agg["desconto_global_pct"] = np.where(
    item_agg["soma_ref"] > 0,
    (item_agg["economia_itens"] / item_agg["soma_ref"] * 100).clip(-100, 100),
    np.nan,
)
p = p.merge(item_agg, on="chave_licitacao", how="left")

# Alvo: log da economia positiva (mesmo log1p de regressaoOLS.py)
p["log_economia_itens"] = np.where(
    p["economia_itens"] > 0, np.log1p(p["economia_itens"]), np.nan
)

PREDITORES = [
    "desconto_global_pct", "media_ratio_itens", "media_desconto_item",
    "interact_part_logval", "valorEstimado", "log_valorEstimado",
    "economia_pct_licit", "log_qtd_participantes", "qtd_participantes",
    "log_valorHomologado", "valorHomologado", "pct_itens_abaixo_ref",
    "log_dias_tramitacao", "dias_tramitacao", "houve_disputa",
]
PREDITORES = [v for v in PREDITORES if v in p.columns]

df_modelo = p[["log_economia_itens"] + PREDITORES].dropna().copy()
y       = df_modelo["log_economia_itens"]
X       = df_modelo[PREDITORES]
X_const = sm.add_constant(X)

modelo_ols = sm.OLS(y, X_const).fit()
print(f"  N (licitacoes usadas) : {int(modelo_ols.nobs)}")
print(f"  k (preditores)        : {int(modelo_ols.df_model)}")
print(f"  R^2                   : {modelo_ols.rsquared:.3f}")
print(f"  Erro-padrao residual  : {np.sqrt(modelo_ols.scale):.4f} (escala log)")

# =============================================================================
# ETAPA 2 — CONSTRUIR CENARIOS FUTUROS (variando a competicao)
# =============================================================================
print("\n" + "=" * 65)
print("ETAPA 2 — CENARIOS DE NOVAS LICITACOES")
print("=" * 65)

# Base do cenario: mediana de todos os preditores na amostra
base = X.median()

# Niveis de competicao realistas (percentis observados de qtd_participantes)
q_baixa = int(round(X["qtd_participantes"].quantile(0.10)))
q_tipica = int(round(X["qtd_participantes"].median()))
q_alta  = int(round(X["qtd_participantes"].quantile(0.90)))
# Garante valores distintos e minimo 1
q_baixa = max(1, q_baixa)
niveis = sorted(set([q_baixa, max(q_tipica, q_baixa + 1), max(q_alta, q_tipica + 1)]))

log_val_est_mediano = float(base["log_valorEstimado"])

cenarios = []
nomes = ["Baixa competicao", "Competicao tipica", "Alta competicao"]
for nome, qtd in zip(nomes, niveis):
    linha = base.copy()
    # Atualiza de forma CONSISTENTE todos os termos ligados a participantes
    linha["qtd_participantes"]     = qtd
    linha["log_qtd_participantes"] = np.log1p(qtd)
    linha["houve_disputa"]         = 1 if qtd > 1 else 0
    linha["interact_part_logval"]  = qtd * log_val_est_mediano
    linha["_nome"]   = nome
    linha["_qtd"]    = qtd
    cenarios.append(linha)
    print(f"  {nome:<20}: qtd_participantes = {qtd}")

df_cenarios = pd.DataFrame(cenarios)
X_novo = sm.add_constant(df_cenarios[PREDITORES], has_constant="add")

# =============================================================================
# ETAPA 3 — PREVISAO + INTERVALO DE PREVISAO (95%)
# =============================================================================
print("\n" + "=" * 65)
print(f"ETAPA 3 — PREVISAO E INTERVALO DE PREVISAO ({int(CONFIANCA*100)}%)")
print("=" * 65)

pred = modelo_ols.get_prediction(X_novo)
sf   = pred.summary_frame(alpha=1 - CONFIANCA)
# Colunas: mean, mean_ci_lower/upper (IC da media), obs_ci_lower/upper (previsao)

def to_reais(v):
    """Retransforma log1p -> R$ (inverso de np.log1p e np.expm1)."""
    return float(np.expm1(v))

resultados = []
print(f"\n  {'Cenario':<20} {'Part.':>5}  {'Previsao R$':>14}  "
      f"{'IC previsao 95% (R$)':>30}")
print("  " + "-" * 74)
for i, row in df_cenarios.reset_index(drop=True).iterrows():
    media_log = sf["mean"].iloc[i]
    obs_lo    = sf["obs_ci_lower"].iloc[i]
    obs_hi    = sf["obs_ci_upper"].iloc[i]
    mci_lo    = sf["mean_ci_lower"].iloc[i]
    mci_hi    = sf["mean_ci_upper"].iloc[i]

    prev_rs   = to_reais(media_log)
    pi_lo_rs  = to_reais(obs_lo)
    pi_hi_rs  = to_reais(obs_hi)
    ci_lo_rs  = to_reais(mci_lo)
    ci_hi_rs  = to_reais(mci_hi)

    resultados.append({
        "cenario":            row["_nome"],
        "qtd_participantes":  int(row["_qtd"]),
        "previsao_log":       round(float(media_log), 4),
        "previsao_R$":        round(prev_rs, 2),
        "IC_media_inf_R$":    round(ci_lo_rs, 2),
        "IC_media_sup_R$":    round(ci_hi_rs, 2),
        "IC_previsao_inf_R$": round(pi_lo_rs, 2),
        "IC_previsao_sup_R$": round(pi_hi_rs, 2),
    })
    print(f"  {row['_nome']:<20} {int(row['_qtd']):>5}  R$ {prev_rs:>11,.0f}  "
          f"[R$ {pi_lo_rs:>9,.0f}; R$ {pi_hi_rs:>10,.0f}]")

df_res = pd.DataFrame(resultados)

print("\n  Observacao: o INTERVALO DE PREVISAO (obs_ci) e mais largo que o")
print("  IC da media (mean_ci) porque inclui a variabilidade de uma nova")
print("  licitacao individual, nao apenas a incerteza do valor medio previsto.")

# =============================================================================
# ETAPA 4 — EXPORTACAO
# =============================================================================
print("\n" + "=" * 65)
print("ETAPA 4 — EXPORTACAO")
print("=" * 65)

csv_path = os.path.join(DIR_SAIDA, "previsao_cenarios.csv")
df_res.to_csv(csv_path, index=False, sep=";", decimal=",", encoding="utf-8-sig")
print(f"  Tabela salva: {os.path.abspath(csv_path)}")

# =============================================================================
# ETAPA 5 — GRAFICO
# =============================================================================
fig, ax = plt.subplots(figsize=(11, 6))

xpos = np.arange(len(df_res))
prev = df_res["previsao_R$"].values
pi_lo = df_res["IC_previsao_inf_R$"].values
pi_hi = df_res["IC_previsao_sup_R$"].values
ci_lo = df_res["IC_media_inf_R$"].values
ci_hi = df_res["IC_media_sup_R$"].values

# Intervalo de previsao (largo, claro)
ax.errorbar(xpos, prev,
            yerr=[prev - pi_lo, pi_hi - prev],
            fmt="none", ecolor="#90CAF9", elinewidth=12, alpha=0.6,
            capsize=0, label="Intervalo de PREVISAO 95% (nova licitacao)")
# IC da media (estreito, escuro)
ax.errorbar(xpos, prev,
            yerr=[prev - ci_lo, ci_hi - prev],
            fmt="none", ecolor="#1B5E20", elinewidth=3,
            capsize=8, capthick=2, label="IC da MEDIA 95%")
# Ponto de previsao
ax.scatter(xpos, prev, color="#0D47A1", s=90, zorder=5,
           label="Previsao pontual (R$)")

for i, v in enumerate(prev):
    ax.text(xpos[i] + 0.06, v, f"R$ {v:,.0f}", va="center", fontsize=9,
            fontweight="bold", color="#0D47A1")

ax.set_xticks(xpos)
ax.set_xticklabels([f"{r['cenario']}\n({r['qtd_participantes']} participantes)"
                    for _, r in df_res.iterrows()], fontsize=9)
ax.set_ylabel("economia_itens prevista (R$)")
ax.set_title(
    "Previsao do modelo OLS para novas licitacoes\n"
    f"VD: log(economia_itens) retransformada para R$  |  "
    f"R^2={modelo_ols.rsquared:.3f}  |  n={int(modelo_ols.nobs)}",
    fontsize=11, fontweight="bold")
ax.legend(fontsize=8, loc="upper left")
ax.grid(alpha=0.3, axis="y")
plt.tight_layout()
graf_path = os.path.join(DIR_SAIDA, "grafico_previsao.png")
plt.savefig(graf_path, dpi=150, bbox_inches="tight")
plt.close()
print(f"  Grafico salvo: {os.path.abspath(graf_path)}")

print("\n" + "=" * 65)
print("CONCLUIDO")
print("=" * 65)
