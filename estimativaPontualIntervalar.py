"""
=============================================================================
ESTIMATIVA PONTUAL E INTERVALAR — economia_itens
=============================================================================
Pergunta-problema:
  "Qual o impacto do numero de participantes nas licitacoes sobre a economia
   gerada para o municipio de Criciuma?"

Variavel-alvo: economia_itens = soma(valorTotalReferencia - valorTotalVencedor)
               por licitacao (R$)

METODO: t-Student na escala logaritmica.
  A etapa de normalizacao (normalizacaoVariavelAlvo.py) concluiu que
  economia_itens segue distribuicao LOG-NORMAL (KS p=0,365). Ou seja, a
  variavel bruta NAO e normal, mas log(economia_itens) E aproximadamente
  normal. Por isso a estimativa e feita na escala log (onde o pressuposto de
  normalidade do t-Student e valido) e depois retransformada para reais.

  Na escala log estima-se a media mu_log; exp(mu_log) = MEDIA GEOMETRICA, que
  para uma Log-Normal corresponde a MEDIANA na escala original (R$).

UNIDADE DE ANALISE: 1 linha = 1 licitacao (666 processos).
  Log exige x > 0 -> usa-se o subconjunto de economia positiva.

Saidas:
  estimativaPontualIntervalar/estimativa_economia.csv
  estimativaPontualIntervalar/grafico_estimativa.png
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
from scipy import stats

ARQUIVO_BASE = r"baseFinalUnificada\base_unificada_criciuma_v14.csv"
DIR_SAIDA    = "estimativaPontualIntervalar"
ENCODING     = "utf-8-sig"
CONFIANCA    = 0.95

os.makedirs(DIR_SAIDA, exist_ok=True)

# =============================================================================
# ETAPA 1 — CARGA E AGREGACAO AO NIVEL DA LICITACAO
# =============================================================================
print("\n" + "=" * 65)
print("ETAPA 1 — VARIAVEL-ALVO: economia_itens (nivel da licitacao)")
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
eco_pos = eco[eco > 0]
n_pos   = len(eco_pos)

print(f"  Licitacoes totais          : {n_total}")
print(f"  Com economia positiva (>0) : {n_pos}  ({100*n_pos/n_total:.1f}%)")
print(f"  Excluidas (<= 0, sem log)  : {n_total - n_pos}")

# =============================================================================
# ETAPA 2 — ESTIMATIVA PONTUAL
# =============================================================================
print("\n" + "=" * 65)
print("ETAPA 2 — ESTIMATIVA PONTUAL")
print("=" * 65)

# --- Escala original (referencia) ---
media_aritmetica = float(np.mean(eco_pos))
mediana_amostral = float(np.median(eco_pos))

# --- Escala log (onde os dados sao normais) ---
log_eco   = np.log(eco_pos)            # ln(economia)
mu_log    = float(np.mean(log_eco))    # estimativa pontual de mu_log
s_log     = float(np.std(log_eco, ddof=1))
n         = len(log_eco)

# Retransformacao: exp(mu_log) = media geometrica = mediana estimada (R$)
media_geometrica = float(np.exp(mu_log))

print(f"  --- Escala log (ln) ---")
print(f"  Media do log (mu_log)      : {mu_log:.4f}")
print(f"  Desvio-padrao do log       : {s_log:.4f}")
print(f"  n                          : {n}")
print(f"  --- Escala original (R$) ---")
print(f"  Estimativa pontual (media geometrica = mediana Log-Normal):")
print(f"    exp(mu_log)              = R$ {media_geometrica:,.2f}")
print(f"  (Referencia) media aritmetica simples: R$ {media_aritmetica:,.2f}")
print(f"  (Referencia) mediana amostral        : R$ {mediana_amostral:,.2f}")

# =============================================================================
# ETAPA 3 — ESTIMATIVA INTERVALAR (t-Student no log)
# =============================================================================
print("\n" + "=" * 65)
print(f"ETAPA 3 — ESTIMATIVA INTERVALAR (IC {CONFIANCA*100:.0f}%, t-Student no log)")
print("=" * 65)

alpha     = 1 - CONFIANCA
gl        = n - 1                       # graus de liberdade
t_crit    = float(stats.t.ppf(1 - alpha/2, gl))
erro_pad  = s_log / np.sqrt(n)          # erro-padrao da media (escala log)
margem    = t_crit * erro_pad

ic_log_inf = mu_log - margem
ic_log_sup = mu_log + margem

# Retransformacao do IC para a escala original (R$)
ic_inf = float(np.exp(ic_log_inf))
ic_sup = float(np.exp(ic_log_sup))

print(f"  Graus de liberdade (n-1)   : {gl}")
print(f"  t critico (bicaudal)       : {t_crit:.4f}")
print(f"  Erro-padrao (escala log)   : {erro_pad:.5f}")
print(f"  Margem de erro (escala log): +/- {margem:.5f}")
print()
print(f"  IC {CONFIANCA*100:.0f}% na escala log : [{ic_log_inf:.4f} ; {ic_log_sup:.4f}]")
print(f"  IC {CONFIANCA*100:.0f}% em R$ (exp)   : [R$ {ic_inf:,.2f} ; R$ {ic_sup:,.2f}]")
print()
print(f"  >> A economia tipica (mediana) por licitacao e estimada em")
print(f"     R$ {media_geometrica:,.2f}, com {CONFIANCA*100:.0f}% de confianca de estar")
print(f"     entre R$ {ic_inf:,.2f} e R$ {ic_sup:,.2f}.")

# =============================================================================
# ETAPA 4 — EXPORTACAO DA TABELA
# =============================================================================
print("\n" + "=" * 65)
print("ETAPA 4 — EXPORTACAO")
print("=" * 65)

tabela = pd.DataFrame([
    {"grandeza": "n (economia > 0)",                 "escala": "-",   "valor": n},
    {"grandeza": "media do log (mu_log)",            "escala": "log", "valor": round(mu_log, 4)},
    {"grandeza": "desvio-padrao do log",             "escala": "log", "valor": round(s_log, 4)},
    {"grandeza": "erro-padrao da media",             "escala": "log", "valor": round(erro_pad, 5)},
    {"grandeza": "t critico (gl={})".format(gl),     "escala": "log", "valor": round(t_crit, 4)},
    {"grandeza": "IC inferior",                      "escala": "log", "valor": round(ic_log_inf, 4)},
    {"grandeza": "IC superior",                      "escala": "log", "valor": round(ic_log_sup, 4)},
    {"grandeza": "estimativa pontual (mediana)",     "escala": "R$",  "valor": round(media_geometrica, 2)},
    {"grandeza": "IC inferior",                      "escala": "R$",  "valor": round(ic_inf, 2)},
    {"grandeza": "IC superior",                      "escala": "R$",  "valor": round(ic_sup, 2)},
    {"grandeza": "media aritmetica (referencia)",    "escala": "R$",  "valor": round(media_aritmetica, 2)},
    {"grandeza": "mediana amostral (referencia)",    "escala": "R$",  "valor": round(mediana_amostral, 2)},
])
csv_path = os.path.join(DIR_SAIDA, "estimativa_economia.csv")
tabela.to_csv(csv_path, index=False, sep=";", decimal=",", encoding="utf-8-sig")
print(f"  Tabela salva: {os.path.abspath(csv_path)}")

# =============================================================================
# ETAPA 5 — GRAFICO
# =============================================================================
fig, axes = plt.subplots(1, 2, figsize=(14, 5.5))

# --- Painel 1: histograma do log com Normal ajustada + media e IC ---
ax = axes[0]
ax.hist(log_eco, bins=40, density=True, color="#BBDEFB",
        alpha=0.75, edgecolor="white", label=f"log(economia) (n={n})")
x_curve = np.linspace(log_eco.min(), log_eco.max(), 300)
ax.plot(x_curve, stats.norm.pdf(x_curve, mu_log, s_log),
        color="#1565C0", lw=2.2, label="Normal ajustada")
ax.axvline(mu_log, color="#1B5E20", lw=2, label=f"media = {mu_log:.2f}")
ax.axvspan(ic_log_inf, ic_log_sup, color="#1B5E20", alpha=0.15,
           label=f"IC {CONFIANCA*100:.0f}%")
ax.set_title("Escala log — onde o t-Student e valido\n(log(economia) ~ Normal)",
             fontsize=10)
ax.set_xlabel("ln(economia_itens)")
ax.set_ylabel("Densidade")
ax.legend(fontsize=8)
ax.grid(alpha=0.3)

# --- Painel 2: estimativa pontual e intervalar em R$ ---
ax = axes[1]
ax.errorbar(media_geometrica, 0,
            xerr=[[media_geometrica - ic_inf], [ic_sup - media_geometrica]],
            fmt="o", color="#1B5E20", markersize=11, capsize=8,
            elinewidth=2.5, capthick=2.5, label="Estimativa pontual + IC 95%")
ax.axvline(media_aritmetica, color="#C62828", ls="--", lw=1.5,
           label=f"media aritmetica (R$ {media_aritmetica:,.0f})")
ax.text(media_geometrica, 0.08, f"R$ {media_geometrica:,.0f}",
        ha="center", fontsize=10, fontweight="bold", color="#1B5E20")
ax.text(ic_inf, -0.10, f"R$ {ic_inf:,.0f}", ha="center", fontsize=8, color="#1B5E20")
ax.text(ic_sup, -0.10, f"R$ {ic_sup:,.0f}", ha="center", fontsize=8, color="#1B5E20")
ax.set_ylim(-0.3, 0.3)
ax.set_yticks([])
ax.set_title("Economia tipica por licitacao (mediana Log-Normal)\n"
             f"IC {CONFIANCA*100:.0f}% retransformado para R$", fontsize=10)
ax.set_xlabel("economia_itens (R$)")
ax.legend(fontsize=8, loc="upper right")
ax.grid(alpha=0.3, axis="x")

fig.suptitle(
    "Estimativa pontual e intervalar de economia_itens — Criciuma\n"
    f"t-Student na escala log  |  n={n} licitacoes  |  "
    f"pontual=R$ {media_geometrica:,.0f}  IC95%=[R$ {ic_inf:,.0f}; R$ {ic_sup:,.0f}]",
    fontsize=12, fontweight="bold")
plt.tight_layout()
graf_path = os.path.join(DIR_SAIDA, "grafico_estimativa.png")
plt.savefig(graf_path, dpi=150, bbox_inches="tight")
plt.close()
print(f"  Grafico salvo: {os.path.abspath(graf_path)}")

print("\n" + "=" * 65)
print("CONCLUIDO")
print("=" * 65)
