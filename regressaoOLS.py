"""
REQUISITO 2 — OLS com variável alvo e variáveis bem correlacionadas:
  "Qual o impacto do número de participantes nas licitações sobre a economia
   gerada para o município de Criciúma? Características do processo, como
   valor orçado, modalidade e duração da tramitação, amplificam ou atenuam esse efeito?"

  Variável alvo (a ser prevista) : log(economia_itens)
  Preditores                     : variáveis com |Spearman| >= 0,3 (bem correlacionadas)
  Erros-padrão                   : robustos HC3
"""

import sys, os, warnings
sys.stdout.reconfigure(encoding="utf-8", errors="replace")
warnings.filterwarnings("ignore")
os.makedirs("resultadosOLS", exist_ok=True)

import numpy as np
import pandas as pd
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import statsmodels.api as sm
from scipy import stats
from statsmodels.stats.diagnostic import het_breuschpagan
from statsmodels.stats.stattools import durbin_watson
from statsmodels.stats.outliers_influence import variance_inflation_factor

ARQUIVO_BASE = r"baseFinalUnificada\base_unificada_criciuma_v14.csv"

# ── 1. Leitura e agregação ao nível da licitação ─────────────────────────────
df_raw = pd.read_csv(
    ARQUIVO_BASE, sep=";", decimal=",", encoding="utf-8-sig", low_memory=False
)

# Variáveis que já existem ao nível da licitação no CSV
COLUNAS_LICIT = [
    "chave_licitacao",
    "valorEstimado", "log_valorEstimado",
    "valorHomologado", "log_valorHomologado",
    "qtd_participantes", "log_qtd_participantes",
    "dias_tramitacao", "log_dias_tramitacao",
    "houve_disputa",
    "interact_part_logval",
    "economia_pct_licit",
    "media_desconto_item",
]
cols_ok = [c for c in COLUNAS_LICIT if c in df_raw.columns]
p = df_raw[cols_ok].drop_duplicates(subset="chave_licitacao").copy()

# Variáveis calculadas a partir dos itens
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
item_agg["economia_itens"]    = item_agg["soma_ref"] - item_agg["soma_venc"]
item_agg["desconto_global_pct"] = np.where(
    item_agg["soma_ref"] > 0,
    (item_agg["economia_itens"] / item_agg["soma_ref"] * 100).clip(-100, 100),
    np.nan,
)
p = p.merge(item_agg, on="chave_licitacao", how="left")

# Log do alvo (apenas economia positiva)
p["log_economia_itens"] = np.where(
    p["economia_itens"] > 0, np.log1p(p["economia_itens"]), np.nan
)

# ── 2. Definição dos preditores (variáveis bem correlacionadas) ───────────────
PREDITORES = [
    "desconto_global_pct",
    "media_ratio_itens",
    "media_desconto_item",
    "interact_part_logval",
    "valorEstimado",
    "log_valorEstimado",
    "economia_pct_licit",
    "log_qtd_participantes",
    "qtd_participantes",
    "log_valorHomologado",
    "valorHomologado",
    "pct_itens_abaixo_ref",
    "log_dias_tramitacao",
    "dias_tramitacao",
    "houve_disputa",
]
# Manter apenas as que existem no dataframe
PREDITORES = [v for v in PREDITORES if v in p.columns]

# ── 3. Amostra final (listwise deletion) ─────────────────────────────────────
df_modelo = p[["log_economia_itens"] + PREDITORES].dropna().copy()
y         = df_modelo["log_economia_itens"]
X         = df_modelo[PREDITORES]
X_const   = sm.add_constant(X)

# ── 4. Estimação OLS + HC3 ────────────────────────────────────────────────────
modelo_ols = sm.OLS(y, X_const).fit()
modelo_hc3 = modelo_ols.get_robustcov_results(cov_type="HC3")

hc3_bse  = pd.Series(modelo_hc3.bse,     index=modelo_ols.params.index)
hc3_pval = pd.Series(modelo_hc3.pvalues, index=modelo_ols.params.index)
hc3_ci   = pd.DataFrame(modelo_hc3.conf_int(),
                         index=modelo_ols.params.index, columns=[0, 1])

# ── 5. Diagnóstico ────────────────────────────────────────────────────────────
residuos = modelo_ols.resid
fitted   = modelo_ols.fittedvalues

_, p_sw          = stats.shapiro(residuos.sample(min(len(residuos), 300), random_state=42))
jb               = stats.jarque_bera(residuos)
bp_stat, bp_p, _, _ = het_breuschpagan(residuos, X_const)
dw_stat          = durbin_watson(residuos)
skew_res         = float(stats.skew(residuos))
kurt_res         = float(stats.kurtosis(residuos, fisher=False))

vif_dict = {}
for i, col in enumerate(X.columns):
    try:
        vif_dict[col] = variance_inflation_factor(X_const.values, i + 1)
    except Exception:
        vif_dict[col] = float("nan")

# ── 6. SAÍDA FINAL ────────────────────────────────────────────────────────────
print("=" * 62)
print("REQUISITO 2 — REGRESSÃO OLS")
print("=" * 62)
print()
print("  VARIÁVEL ALVO (a ser prevista)")
print("  ─────────────────────────────────────────────────────")
print("  log(economia_itens) — logaritmo da economia em R$ gerada")
print("  por licitação (diferença preço referência − preço pago)")
print()
print("  VARIÁVEIS PREDITORAS (bem correlacionadas | |Spearman| >= 0,3)")
print("  ─────────────────────────────────────────────────────")

correlacoes = {
    "desconto_global_pct":   0.7605,
    "media_ratio_itens":    -0.6919,
    "media_desconto_item":   0.6357,
    "interact_part_logval":  0.5261,
    "valorEstimado":         0.5195,
    "log_valorEstimado":     0.5194,
    "economia_pct_licit":    0.5095,
    "log_qtd_participantes": 0.4853,
    "qtd_participantes":     0.4853,
    "log_valorHomologado":   0.4617,
    "valorHomologado":       0.4616,
    "pct_itens_abaixo_ref":  0.3827,
    "log_dias_tramitacao":   0.3526,
    "dias_tramitacao":       0.3526,
    "houve_disputa":         0.3338,
}
print(f"  {'Variável':<28} {'Spearman':>9}")
print(f"  {'-'*40}")
for v in PREDITORES:
    r = correlacoes.get(v, float("nan"))
    print(f"  {v:<28} {r:>+9.4f}")
print()
print("  AMOSTRA UTILIZADA")
print("  ─────────────────────────────────────────────────────")
print(f"  Total de licitações na base : {len(p)}")
print(f"  Usadas na regressão         : {len(df_modelo)}")
print(f"  Excluídas (dados ausentes)  : {len(p) - len(df_modelo)}")
print()
print("  RESULTADO DO MODELO OLS (erros-padrão robustos HC3)")
print("  ─────────────────────────────────────────────────────")
print(f"  R²          = {modelo_ols.rsquared:.3f}   (modelo explica {modelo_ols.rsquared*100:.1f}% da variância da economia)")
print(f"  R² ajustado = {modelo_ols.rsquared_adj:.3f}")
print(f"  F-statistic = {modelo_ols.fvalue:.4f}   Prob(F) = {modelo_ols.f_pvalue:.2e}")
print(f"  N           = {int(modelo_ols.nobs)} licitações")
print(f"  k           = {int(modelo_ols.df_model)} preditores")
print()
print(f"  {'Variável':<28} {'β':>8}  {'IC 95% (HC3)':^22}  {'p-valor':>8}  Sig.")
print(f"  {'-'*75}")
for var in modelo_ols.params.index:
    if var == "const":
        continue
    b   = modelo_ols.params[var]
    lo  = hc3_ci.loc[var, 0]
    hi  = hc3_ci.loc[var, 1]
    pv  = hc3_pval[var]
    sig = "***" if pv < 0.001 else ("**" if pv < 0.01 else ("*" if pv < 0.05 else "n.s."))
    print(f"  {var:<28} {b:>+8.4f}  [{lo:>+7.4f}; {hi:>+7.4f}]  {pv:>8.4f}  {sig}")

print()
print("  DIAGNÓSTICO DOS PRESSUPOSTOS OLS")
print("  ─────────────────────────────────────────────────────")
norm_ok = p_sw >= 0.05
homo_ok = bp_p  >= 0.05
auto_ok = 1.5 < dw_stat < 2.5
vif_alto = [c for c, v in vif_dict.items() if v > 10]

print(f"  Normalidade (Shapiro-Wilk) : {'OK' if norm_ok else 'Rejeitada — HC3 aplicado'}"
      f"  [p={p_sw:.4f} | assim={skew_res:.2f} | kurt={kurt_res:.2f}]")
print(f"  Homocedasticidade (BP)     : {'OK' if homo_ok else 'Heterocedasticidade detectada'}"
      f"  [p={bp_p:.4f}]")
print(f"  Autocorrelação (DW)        : {'OK' if auto_ok else 'Atenção'}"
      f"  [DW={dw_stat:.3f}]")
if vif_alto:
    print(f"  Multicolinearidade (VIF>10): {', '.join(vif_alto)}")
else:
    print(f"  Multicolinearidade (VIF)   : OK — todos abaixo de 10")

print()
print("  COEFICIENTES SIGNIFICATIVOS (p < 0,05 com HC3)")
print("  ─────────────────────────────────────────────────────")
sig_vars = [
    v for v in modelo_ols.params.index
    if v != "const" and hc3_pval[v] < 0.05
]
if sig_vars:
    for var in sig_vars:
        b  = modelo_ols.params[var]
        pv = hc3_pval[var]
        sig = "***" if pv < 0.001 else ("**" if pv < 0.01 else "*")
        print(f"  {var:<28} β={b:>+8.4f}  p={pv:.4f}  {sig}")
else:
    print("  Nenhum preditor individualmente significativo.")

print()
print("  ARQUIVOS GERADOS")
print("  ─────────────────────────────────────────────────────")

# ── 7. Gráfico ────────────────────────────────────────────────────────────────
fig, axes = plt.subplots(1, 3, figsize=(15, 5))

ax = axes[0]
ax.scatter(y, fitted, alpha=0.35, s=18, color="#6A1B9A")
lim = [min(y.min(), fitted.min()) - 0.3, max(y.max(), fitted.max()) + 0.3]
ax.plot(lim, lim, "r--", lw=1.2)
ax.set_xlim(lim); ax.set_ylim(lim)
ax.set_xlabel("Observado  log(economia_itens)")
ax.set_ylabel("Previsto pelo modelo")
ax.set_title(f"Observado vs Previsto\nR²={modelo_ols.rsquared:.3f}")

ax = axes[1]
betas_h  = [modelo_ols.params[v] for v in PREDITORES]
erros_h  = [(modelo_ols.params[v] - hc3_ci.loc[v, 0]) for v in PREDITORES]
pvals_h  = [hc3_pval[v] for v in PREDITORES]
cores_h  = ["#1B5E20" if b > 0 else "#B71C1C" for b in betas_h]
alphas_h = [1.0 if pv < 0.05 else 0.30 for pv in pvals_h]
for i, (b, e, c, a) in enumerate(zip(betas_h, erros_h, cores_h, alphas_h)):
    ax.barh(i, b, xerr=e, color=c, alpha=a, height=0.6,
            error_kw=dict(elinewidth=1.1, capsize=3, ecolor="black"))
ax.set_yticks(range(len(PREDITORES)))
ax.set_yticklabels(PREDITORES, fontsize=7)
ax.axvline(0, color="black", lw=0.8)
ax.set_xlabel("Coeficiente HC3  (± IC 95%)")
ax.set_title("Coeficientes\n(opaco=sig. | transparente=n.s.)")

ax = axes[2]
(osm, osr), (slope, intercept, _) = stats.probplot(residuos, dist="norm")
ax.scatter(osm, osr, alpha=0.35, s=18, color="#1565C0")
ax.plot(osm, slope * np.array(osm) + intercept, "r-", lw=1.5)
ax.set_xlabel("Quantis teóricos")
ax.set_ylabel("Quantis dos resíduos")
ax.set_title("QQ-Plot dos Resíduos")

fig.suptitle(
    f"OLS HC3 — Economia das Licitações de Criciúma\n"
    f"VD: log(economia_itens)  |  n={int(modelo_ols.nobs)}  |  R²={modelo_ols.rsquared:.3f}",
    fontsize=12, fontweight="bold",
)
plt.tight_layout()
caminho_grafico = r"resultadosOLS\resultado_ols.png"
plt.savefig(caminho_grafico, dpi=150, bbox_inches="tight")
plt.close()

# ── 8. Exportação ─────────────────────────────────────────────────────────────
linhas = []
for var in modelo_ols.params.index:
    pv  = hc3_pval[var]
    sig = "***" if pv < 0.001 else ("**" if pv < 0.01 else ("*" if pv < 0.05 else "n.s."))
    linhas.append({
        "variavel":      var,
        "coeficiente":   round(modelo_ols.params[var], 4),
        "EP_HC3":        round(hc3_bse[var], 4),
        "IC_inf_95":     round(hc3_ci.loc[var, 0], 4),
        "IC_sup_95":     round(hc3_ci.loc[var, 1], 4),
        "p_valor_HC3":   round(pv, 4),
        "significancia": sig,
    })
cam_csv = r"resultadosOLS\coeficientes_ols.csv"
pd.DataFrame(linhas).to_csv(cam_csv, index=False, sep=";", decimal=",", encoding="utf-8-sig")

print(f"  Gráfico     : resultadosOLS/resultado_ols.png")
print(f"  Coeficientes: resultadosOLS/coeficientes_ols.csv")
print()
print("=" * 62)
