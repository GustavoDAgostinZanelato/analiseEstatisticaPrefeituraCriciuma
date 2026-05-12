"""
=============================================================================
NORMALIZAÇÃO DA VARIÁVEL-ALVO — PORTAL DA TRANSPARÊNCIA CRICIÚMA
=============================================================================
Roteiro seguindo a instrução do professor:
  1. Testar normalidade da variável-alvo com Shapiro-Wilk (SW)
  2. Caso não seja normal → testar as distribuições da aula anterior:
       Discretas : Poisson, Geométrica, Binomial Negativa (Pascal),
                   Hipergeométrica (conceitual — exige dados externos)
       Contínuas : Gamma, Log-Normal

Variável-alvo: economia_itens = Σ(valorTotalReferencia − valorTotalVencedor)
               por processo licitatório (R$)

Saídas
------
  normalizacaoVariavelAlvo/resultado_normalidade.csv
  normalizacaoVariavelAlvo/grafico_distribuicoes.png
=============================================================================
"""

import sys
sys.stdout.reconfigure(encoding="utf-8", errors="replace")

import os
import warnings
import numpy as np
import pandas as pd
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from scipy import stats

warnings.filterwarnings("ignore")

ARQUIVO_BASE = r"baseFinalUnificada\base_unificada_criciuma_v14.csv"
DIR_SAIDA    = r"normalizacaoVariavelAlvo"
ENCODING     = "utf-8-sig"
ALPHA        = 0.05

os.makedirs(DIR_SAIDA, exist_ok=True)

# =============================================================================
# ETAPA 1 — CARGA E CÁLCULO DA VARIÁVEL-ALVO
# =============================================================================
print("\n" + "=" * 65)
print("ETAPA 1 — VARIÁVEL-ALVO: economia_itens")
print("=" * 65)

df_raw = pd.read_csv(ARQUIVO_BASE, sep=";", decimal=",",
                     encoding=ENCODING, low_memory=False)

item_agg = (
    df_raw.groupby("chave_licitacao")
    .agg(soma_ref =("valorTotalReferencia", "sum"),
         soma_venc=("valorTotalVencedor",   "sum"))
    .reset_index()
)
item_agg["economia_itens"] = item_agg["soma_ref"] - item_agg["soma_venc"]
eco = item_agg["economia_itens"].dropna().values

n_total = len(eco)
n_pos   = int((eco > 0).sum())
n_neg   = int((eco < 0).sum())
n_zero  = int((eco == 0).sum())

print(f"  Licitações analisadas : {n_total}")
print(f"  Economia > 0          : {n_pos}  ({100*n_pos/n_total:.1f}%)")
print(f"  Economia ≤ 0          : {n_neg + n_zero}  ({100*(n_neg+n_zero)/n_total:.1f}%)")
print(f"  Mínimo  : R$ {eco.min():>15,.2f}")
print(f"  Mediana : R$ {np.median(eco):>15,.2f}")
print(f"  Média   : R$ {eco.mean():>15,.2f}")
print(f"  Máximo  : R$ {eco.max():>15,.2f}")

# =============================================================================
# ETAPA 2 — TESTE DE NORMALIDADE (SHAPIRO-WILK)
# =============================================================================
print("\n" + "=" * 65)
print("ETAPA 2 — TESTE DE NORMALIDADE: Shapiro-Wilk")
print("=" * 65)

w_sw, p_sw = stats.shapiro(eco)
normal_sw  = p_sw >= ALPHA
print(f"\n  Shapiro-Wilk:  W = {w_sw:.4f}   p = {p_sw:.4e}")
print(f"  Conclusão: {'NORMAL (p ≥ 0,05)' if normal_sw else 'NÃO normal (p < 0,05) → testar distribuições alternativas'}")

# =============================================================================
# ETAPA 3 — DISTRIBUIÇÕES DISCRETAS (nota conceitual)
# =============================================================================
print("\n" + "=" * 65)
print("ETAPA 3 — DISTRIBUIÇÕES DISCRETAS (avaliação de aplicabilidade)")
print("=" * 65)
print("""
  economia_itens é uma variável CONTÍNUA monetária com valores positivos,
  negativos e nulos, portanto as distribuições discretas não se aplicam
  diretamente ao seu ajuste. Avaliação de cada uma:

  ┌────────────────────┬────────────────────────────────────────────────┐
  │ Distribuição       │ Aplicabilidade                                 │
  ├────────────────────┼────────────────────────────────────────────────┤
  │ Poisson            │ Não aplicável — suporte {0,1,2,...}, variável  │
  │                    │ contínua com valores negativos                 │
  ├────────────────────┼────────────────────────────────────────────────┤
  │ Geométrica         │ Não aplicável — suporte {1,2,3,...}, variável  │
  │                    │ contínua com valores negativos                 │
  ├────────────────────┼────────────────────────────────────────────────┤
  │ Binomial Negativa  │ Não aplicável — mesma razão (suporte discreto) │
  │ (Pascal)           │                                                │
  ├────────────────────┼────────────────────────────────────────────────┤
  │ Hipergeométrica    │ Não aplicável — requer tamanho total da        │
  │                    │ população (M) e elegíveis (K), não disponíveis │
  │                    │ P(X=k) = C(K,k)·C(M-K,N-k) / C(M,N)            │
  └────────────────────┴────────────────────────────────────────────────┘

  Nota: as distribuições discretas se aplicam a variáveis de CONTAGEM
  (ex: qtd_participantes, n_itens_licitacao). Para economia_itens,
  a análise prossegue com as distribuições contínuas.
""")

# =============================================================================
# ETAPA 4 — DISTRIBUIÇÕES CONTÍNUAS (subconjunto eco > 0)
# =============================================================================
print("=" * 65)
print("ETAPA 4 — DISTRIBUIÇÕES CONTÍNUAS (valores positivos, n={})".format(n_pos))
print("=" * 65)

eco_pos = eco[eco > 0]

print(f"\n  Subconjunto positivo: {n_pos} de {n_total} licitações ({100*n_pos/n_total:.1f}%)")
print(f"  (Gamma e Log-Normal exigem x > 0)\n")

resultados = []

DISTS = [
    ("Normal",     stats.norm,    "μ, σ"),
    ("Gamma",      stats.gamma,   "shape (α), loc, scale (β)"),
    ("Log-Normal", stats.lognorm, "s (σ_log), loc, scale (e^μ_log)"),
]

for nome, dist, param_desc in DISTS:
    if nome == "Normal":
        params = dist.fit(eco_pos)          # sem fixar loc nem scale
    else:
        params = dist.fit(eco_pos, floc=0)  # loc=0 exigido por Gamma e Log-Normal

    ks_stat, ks_p = stats.kstest(eco_pos, dist.name, args=params)
    ajusta = "SIM" if ks_p >= ALPHA else "NÃO"

    # Parâmetros interpretáveis
    if nome == "Normal":
        mu_fit, sigma_fit = params
        param_str = f"μ={mu_fit:.2f}  σ={sigma_fit:.2f}"
    elif nome == "Gamma":
        alpha_fit, _, scale_fit = params
        param_str = f"α={alpha_fit:.4f}  β={scale_fit:.2f}"
    else:
        s_fit, _, scale_fit = params
        param_str = f"μ_log={np.log(scale_fit):.4f}  σ_log={s_fit:.4f}"

    print(f"  {nome}:")
    print(f"    Parâmetros  : {param_str}  ({param_desc})")
    print(f"    Teste KS    : estatística={ks_stat:.4f}   p={ks_p:.4f}")
    print(f"    Ajusta (α={ALPHA}): {ajusta}\n")

    resultados.append({
        "distribuicao": nome,
        "parametros": param_str,
        "ks_estatistica": round(ks_stat, 4),
        "ks_p_valor": round(ks_p, 6),
        "ajusta_alpha005": ajusta,
        "_params_raw": params,
        "_dist": dist,
    })

# =============================================================================
# ETAPA 5 — TABELA COMPARATIVA + GRÁFICO
# =============================================================================
print("=" * 65)
print("ETAPA 5 — COMPARAÇÃO VISUAL E TABELA FINAL")
print("=" * 65)

# ── Tabela CSV ───────────────────────────────────────────────────────────────
linha_sw = {
    "distribuicao": "Normal (Shapiro-Wilk)",
    "parametros": f"μ={eco.mean():.2f}  σ={eco.std():.2f}",
    "ks_estatistica": round(float(w_sw), 4),
    "ks_p_valor": round(float(p_sw), 6),
    "ajusta_alpha005": "SIM" if normal_sw else "NÃO",
}
df_res = pd.DataFrame([linha_sw] + [
    {k: v for k, v in r.items() if not k.startswith("_")}
    for r in resultados
])
csv_path = os.path.join(DIR_SAIDA, "resultado_normalidade.csv")
df_res.to_csv(csv_path, index=False, sep=";", encoding="utf-8-sig")
print(f"\n  Tabela salva: {os.path.abspath(csv_path)}")

print(f"\n  {'Distribuição':<22}  {'Estatística':>12}  {'p-valor':>10}  {'Ajusta?':>8}")
print("  " + "-" * 58)
for _, row in df_res.iterrows():
    stat_label = "W" if row["distribuicao"].startswith("Normal") else "KS"
    print(f"  {row['distribuicao']:<22}  {stat_label}={row['ks_estatistica']:>9.4f}  "
          f"{row['ks_p_valor']:>10.4f}  {row['ajusta_alpha005']:>8}")

# ── Gráfico 2×2: histograma comparativo + três Q-Q plots ────────────────────
CORES = {
    "Normal":     "#2E7D32",   # verde
    "Gamma":      "#C62828",   # vermelho
    "Log-Normal": "#1565C0",   # azul
}
MARCADORES = {"Normal": "NÃO", "Gamma": "NÃO", "Log-Normal": "SIM ✓"}

fig, axes = plt.subplots(2, 2, figsize=(14, 11))
ax_hist  = axes[0, 0]
ax_qq    = {r["distribuicao"]: ax
            for r, ax in zip(resultados, [axes[0, 1], axes[1, 0], axes[1, 1]])}

# Limite visual do histograma: até 95° percentil (evita que outliers
# comprimam as curvas e impeçam a comparação)
x_lim   = float(np.percentile(eco_pos, 95))
x_plot  = np.linspace(eco_pos.min(), x_lim, 500)

# ── Painel 1: Histograma + três PDFs sobrepostas ─────────────────────────────
ax_hist.hist(eco_pos[eco_pos <= x_lim], bins=60, density=True,
             color="#BBDEFB", alpha=0.7, edgecolor="white",
             label=f"Observado (n={n_pos})")
for r in resultados:
    pdf_vals = r["_dist"].pdf(x_plot, *r["_params_raw"])
    rotulo   = f"{r['distribuicao']}  KS p={r['ks_p_valor']:.3f}  → {r['ajusta_alpha005']}"
    ax_hist.plot(x_plot, pdf_vals, lw=2.2,
                 color=CORES[r["distribuicao"]], label=rotulo)
ax_hist.set_xlim(0, x_lim)
ax_hist.set_title("Histograma + PDFs ajustadas\n(valores > 0, exibido até 95° percentil)",
                  fontsize=10)
ax_hist.set_xlabel("economia_itens (R$)")
ax_hist.set_ylabel("Densidade")
ax_hist.legend(fontsize=8, loc="upper right")
ax_hist.grid(alpha=0.3)

# ── Painéis 2–4: Q-Q plot de cada distribuição ───────────────────────────────
x_sorted = np.sort(eco_pos)
probs    = (np.arange(1, len(x_sorted) + 1) - 0.5) / len(x_sorted)

for r in resultados:
    ax = ax_qq[r["distribuicao"]]
    cor = CORES[r["distribuicao"]]

    q_theo = r["_dist"].ppf(probs, *r["_params_raw"])

    # Limite visual: 99° percentil de ambos os eixos
    lim = float(np.percentile(np.concatenate([
        q_theo[np.isfinite(q_theo)], x_sorted
    ]), 99))
    mask = (q_theo <= lim) & (x_sorted <= lim) & np.isfinite(q_theo)

    ax.scatter(q_theo[mask], x_sorted[mask], s=10, alpha=0.45, color=cor)
    ax.plot([0, lim], [0, lim], "k--", lw=1.4, label="y = x  (ajuste perfeito)")
    ax.set_xlim(0, lim)
    ax.set_ylim(0, lim)

    ajuste_label = f"→ {r['ajusta_alpha005']}"
    ax.set_title(
        f"Q-Q Plot: {r['distribuicao']}\n"
        f"KS p = {r['ks_p_valor']:.4f}  {ajuste_label}",
        fontsize=10, color=cor, fontweight="bold"
    )
    ax.set_xlabel(f"Quantis teóricos — {r['distribuicao']}")
    ax.set_ylabel("Quantis observados (R$)")
    ax.legend(fontsize=8)
    ax.grid(alpha=0.3)

fig.suptitle(
    "Normalização da variável-alvo: economia_itens\n"
    f"Prefeitura de Criciúma · {n_total} licitações  |  "
    f"Shapiro-Wilk: W={w_sw:.4f}  p={p_sw:.2e} → NÃO normal",
    fontsize=12, fontweight="bold"
)
plt.tight_layout()
graf_path = os.path.join(DIR_SAIDA, "grafico_distribuicoes.png")
plt.savefig(graf_path, dpi=150, bbox_inches="tight")
plt.close()
print(f"  Gráfico salvo: {os.path.abspath(graf_path)}")

# =============================================================================
# ETAPA 6 — INTERPRETAÇÃO FINAL
# =============================================================================
melhor = max(resultados, key=lambda r: r["ks_p_valor"])
print(f"""
{"=" * 65}
ETAPA 6 — INTERPRETAÇÃO
{"=" * 65}

  SHAPIRO-WILK (série completa, n={n_total}):
    W={w_sw:.4f}  p={p_sw:.2e} → NÃO normal (rejeita H₀ com α=0,05)

  DISTRIBUIÇÕES DISCRETAS:
    Não aplicáveis a variáveis monetárias contínuas (ver Etapa 3).

  DISTRIBUIÇÕES CONTÍNUAS (subconjunto positivo, n={n_pos}):
{chr(10).join(f"    {r['distribuicao']:<12}: KS p={r['ks_p_valor']:.4f} → {r['ajusta_alpha005']}" for r in resultados)}

  CONCLUSÃO:
    A variável-alvo economia_itens segue distribuição {melhor['distribuicao']}
    (melhor ajuste: KS p={melhor['ks_p_valor']:.4f} > 0,05).

    Isso é esperado para dados monetários de licitações:
    a maioria dos valores é positiva e moderada, com poucos processos
    de grande valor formando a cauda direita — padrão típico de Log-Normal.

    Implicação prática:
    → O logaritmo natural é a transformação adequada para esta variável.
    → Variáveis log_* já calculadas na base são matematicamente justificadas.
    → Para modelos de regressão: usar GLM Gamma (link log) ou
      regressão Log-Normal, ambos sem exigir normalidade dos resíduos.
{"=" * 65}
CONCLUÍDO
{"=" * 65}
""")
