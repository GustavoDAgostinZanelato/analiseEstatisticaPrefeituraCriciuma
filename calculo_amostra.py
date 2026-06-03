"""
REQUISITO 1 — Cálculo do tamanho amostral indicado para responder a pergunta-problema:
  "Qual o impacto do número de participantes nas licitações sobre a economia
   gerada para o município de Criciúma? Características do processo, como
   valor orçado, modalidade e duração da tramitação, amplificam ou atenuam esse efeito?"
"""

import sys, warnings
sys.stdout.reconfigure(encoding="utf-8", errors="replace")
warnings.filterwarnings("ignore")

import pandas as pd
import numpy as np
from scipy.stats import f as f_dist, ncf

# ── Carregar base e agregar ao nível de licitação ────────────────────────────
df_itens = pd.read_csv(
    "baseFinalUnificada/base_unificada_criciuma_v14.csv",
    sep=";", decimal=",", encoding="utf-8-sig",
)
df = (
    df_itens[["chave_licitacao", "modalidade", "economia_absoluta"]]
    .drop_duplicates(subset="chave_licitacao")
    .reset_index(drop=True)
)

# ── Definir k (número de preditores do modelo de regressão) ──────────────────
# O modelo para responder a pergunta-problema exige:
#   1 VI principal  + controles (log_valor, dummies de modalidade, log_dias)
#   + termos de interação (VI × cada controle)
n_modalidades = df["modalidade"].nunique()
k_principal  = 1
k_controles  = 1 + (n_modalidades - 1) + 1
k_interacoes = 1 + (n_modalidades - 1) + 1
k_total      = k_principal + k_controles + k_interacoes

# ── Calcular n mínimo (Green, 1991 + G*Power exato) ──────────────────────────
alpha, poder, f2 = 0.05, 0.80, 0.15   # α=5%, poder=80%, efeito médio

n_green = 50 + 8 * k_total            # Fórmula de Green (1991)

def calc_n_exato(k, alpha, poder, f2):
    for n in range(k + 2, 5000):
        df1, df2 = k, n - k - 1
        if df2 < 1:
            continue
        crit = f_dist.ppf(1 - alpha, df1, df2)
        pot  = 1 - ncf.cdf(crit, df1, df2, f2 * n)
        if pot >= poder:
            return n
    return None

n_exato     = calc_n_exato(k_total, alpha, poder, f2)
n_minimo    = max(n_green, n_exato)
n_disponivel = df["economia_absoluta"].notna().sum()

# ── SAÍDA FINAL ───────────────────────────────────────────────────────────────
print("=" * 62)
print("REQUISITO 1 — TAMANHO AMOSTRAL INDICADO")
print("=" * 62)
print()
print(f"  Pergunta-problema     : impacto de participantes na economia")
print(f"  Método estatístico    : Regressão múltipla com moderação")
print(f"  Número de preditores  : k = {k_total}")
print(f"    - VI principal      : {k_principal}  (log_qtd_participantes)")
print(f"    - Controles         : {k_controles}  (log_valor + {n_modalidades-1} dummies modal + log_dias)")
print(f"    - Interações        : {k_interacoes}  (VI × cada controle)")
print()
print(f"  Cálculo do n mínimo (α=0,05 | poder=80% | efeito médio f²=0,15):")
print(f"    Green (1991): 50 + 8×{k_total}       = {n_green}")
print(f"    G*Power exato (dist. F não-central) = {n_exato}")
print(f"    → Amostra mínima indicada           = {n_minimo}  licitações")
print()
print(f"  Base disponível       : {len(df)} licitações no total")
print(f"  Com variável alvo     : {n_disponivel} licitações (economia_absoluta válida)")
print()
if n_disponivel >= n_minimo:
    excedente = n_disponivel - n_minimo
    pct = (n_disponivel / n_minimo - 1) * 100
    print(f"  CONCLUSÃO: base SUFICIENTE.")
    print(f"  As {n_disponivel} licitações disponíveis superam o mínimo indicado")
    print(f"  de {n_minimo} em {excedente} observações (+{pct:.0f}%).")
    print(f"  Não é necessário coletar dados adicionais.")
else:
    faltam = n_minimo - n_disponivel
    print(f"  CONCLUSÃO: base INSUFICIENTE.")
    print(f"  Faltam {faltam} licitações para atingir o mínimo indicado de {n_minimo}.")
print()
print("=" * 62)
