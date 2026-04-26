"""
=============================================================================
UNIFICACAO DE BASES - PORTAL DA TRANSPARENCIA CRICIUMA (v14)
=============================================================================
Pergunta-problema:
  "O numero de participantes nos processos de aquisicao publica influencia a
   economia gerada pela Prefeitura de Criciuma? O tipo de processo (licitacao
   competitiva ou dispensa) e a secretaria responsavel modulam esse efeito?
   Processos com maior nivel de competicao estao associados a fornecedores
   com melhor historico contratual?"

Fontes:
  - Processos Licitatorios Finalizados-2019
  - Processos Licitatorios Finalizados-2020
  - Dispensa de Licitacao-2019
  - Dispensa de Licitacao-2020
  - Fornecedores sancionados (referencia cruzada)

Correcoes aplicadas (sobre v13):
  [FIX-01] Participantes: join direto via UUID
           df_27['participantes'] -> df_participantes['origem_arquivo']
           Motivo: o mapeamento anterior (CNPJ->contrato) contava apenas
           vencedores, ignorando todos os participantes que perderam.

  [FIX-02] valorHomologado reconstruido via sum(valorTotalVencedor) por licitacao
           quando o campo esta nulo no df_27.
           Validacao: concordancia de 99,8% em 480 licitacoes de 2019.
           Motivo: 70% das licitacoes de 2020 nao tinham valorHomologado,
           bloqueando ~7.600 itens validos.

  [FIX-03] valorEstimado removido do filtro obrigatorio de consistencia.
           Motivo: licitacoes com valorHomologado reconstruido pelos itens
           podem nao ter valorEstimado sem comprometer o calculo do alvo.

  [FIX-04] Secretaria vinculada via UUID direto
           df_27['despesas'] -> df_despesas['origem_arquivo']
           Motivo: o mapeamento anterior (empenhos -> numero licitacao) tinha
           cobertura de apenas 33%.

Unidade de analise: 1 linha = 1 item vencedor de licitacao.
=============================================================================
"""

import os
import warnings
import pandas as pd
import numpy as np

warnings.filterwarnings("ignore")

# =============================================================================
# CONFIGURACAO
# =============================================================================

BASE_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "dadosUnificados")

FONTES = [
    {
        "label": "finalizado_2019",
        "tipo_processo": "LICITACAO",
        "pasta": os.path.join(BASE_DIR, "Processos Licitatórios Finalizados-2019"),
    },
    {
        "label": "finalizado_2020",
        "tipo_processo": "LICITACAO",
        "pasta": os.path.join(BASE_DIR, "Processos Licitatórios Finalizados-2020"),
    },
    {
        "label": "dispensa_2019",
        "tipo_processo": "DISPENSA",
        "pasta": os.path.join(BASE_DIR, "Dispensa de Licitação-2019"),
    },
    {
        "label": "dispensa_2020",
        "tipo_processo": "DISPENSA",
        "pasta": os.path.join(BASE_DIR, "Dispensa de Licitação-2020"),
    },
]

PASTA_SANCIONADOS = os.path.join(BASE_DIR, "Fornecedores sancionados")
ARQUIVO_SAIDA     = "baseFinalUnificada/base_unificada_criciuma_v14.csv"


# =============================================================================
# FUNCOES AUXILIARES
# =============================================================================

def ler_csv(pasta, nome_arquivo, label=""):
    """Le um CSV da pasta com deteccao automatica de encoding/separador."""
    path = os.path.join(pasta, nome_arquivo)
    if not os.path.exists(path):
        print(f"  [AVISO] Nao encontrado: {nome_arquivo} em {os.path.basename(pasta)}")
        return pd.DataFrame()
    try:
        df = pd.read_csv(
            path, sep=None, engine="python",
            on_bad_lines="skip", dtype=str, encoding="utf-8-sig",
        )
        df.columns = [c.lstrip("﻿").strip() for c in df.columns]
        print(f"  OK {nome_arquivo} ({label}): {len(df):,} linhas")
        return df
    except Exception as exc:
        print(f"  [ERRO] {nome_arquivo}: {exc}")
        return pd.DataFrame()


def para_float(serie):
    """Converte coluna string para float, suportando formatos BR e EN."""
    s = serie.astype(str).str.strip()
    resultado = pd.to_numeric(s, errors="coerce")
    if resultado.notna().mean() >= 0.5:
        return resultado
    # Fallback: formato BR (ponto como milhar, virgula como decimal)
    s_br = (s
            .str.replace(r"\.", "", regex=True)
            .str.replace(",", ".", regex=False))
    return pd.to_numeric(s_br, errors="coerce")


def codificar(serie):
    """Codifica serie categorica como float (-1 substituido por NaN)."""
    cats = pd.Categorical(serie.fillna("__nulo__"))
    codes = cats.codes.astype(float)
    codes[serie.isna()] = np.nan
    return codes


def moda_serie(x):
    """Retorna a moda de uma serie ignorando nulos; None se vazia."""
    vals = x.dropna()
    if vals.empty:
        return None
    return vals.mode().iloc[0]


# =============================================================================
# ETAPA 1 — PROCESSAR CADA FONTE
# =============================================================================

print("\n" + "=" * 60)
print("ETAPA 1 — CARREGAMENTO E PROCESSAMENTO DAS FONTES")
print("=" * 60)

frames_itens = []

for fonte in FONTES:
    label        = fonte["label"]
    tipo_proc    = fonte["tipo_processo"]
    pasta        = fonte["pasta"]

    if not os.path.isdir(pasta):
        print(f"\n[AVISO] Pasta nao encontrada: {pasta}")
        continue

    print(f"\n--- {label} ({tipo_proc}) ---")

    # -------------------------------------------------------------------------
    # 1A. Carregar arquivos da pasta
    # -------------------------------------------------------------------------
    df27 = ler_csv(pasta, "df_27_unificado.csv",              label)
    dfp  = ler_csv(pasta, "df_participantes_unificado.csv",   label)
    dfiv = ler_csv(pasta, "df_itensvencedores_unificado.csv", label)
    dfd  = ler_csv(pasta, "df_despesas_unificado.csv",        label)

    if df27.empty or dfiv.empty:
        print(f"  [AVISO] Arquivos principais ausentes em {label}. Pulando.")
        continue

    # -------------------------------------------------------------------------
    # 1B. Converter valores monetarios de df_27
    # -------------------------------------------------------------------------
    for col in ["valorEstimado", "valorHomologado"]:
        if col in df27.columns:
            df27[col] = para_float(df27[col])

    # -------------------------------------------------------------------------
    # 1C. Chave de licitacao: prefere numeroLicitacao/anoLicitacao
    # -------------------------------------------------------------------------
    chave_criada = False
    for col_num, col_ano in [
        ("numeroLicitacao", "anoLicitacao"),
        ("numeroProcesso",  "anoProcesso"),
    ]:
        if col_num in df27.columns and col_ano in df27.columns:
            num = df27[col_num].astype(str).str.strip().str.split(".").str[0]
            ano = df27[col_ano].astype(str).str.strip().str.split(".").str[0]
            df27["chave_licitacao"] = num + "_" + ano
            chave_criada = True
            break

    if not chave_criada:
        df27["chave_licitacao"] = pd.RangeIndex(len(df27)).astype(str) + "_" + label

    # -------------------------------------------------------------------------
    # 1D. [FIX-01] Contar participantes via UUID direto
    # -------------------------------------------------------------------------
    df27["qtd_participantes"] = 0

    if not dfp.empty and "origem_arquivo" in dfp.columns and "participantes" in df27.columns:
        contagem = (dfp.groupby("origem_arquivo")
                    .size()
                    .reset_index(name="qtd_participantes"))
        df27 = df27.merge(
            contagem.rename(columns={"origem_arquivo": "participantes"}),
            on="participantes", how="left",
        )
        # Resolver conflito de coluna se merge criou _x/_y
        if "qtd_participantes_y" in df27.columns:
            df27["qtd_participantes"] = df27["qtd_participantes_y"].fillna(0)
            df27 = df27.drop(columns=["qtd_participantes_x", "qtd_participantes_y"])
        else:
            df27["qtd_participantes"] = df27["qtd_participantes"].fillna(0)

    df27["qtd_participantes"] = df27["qtd_participantes"].astype(int)
    cob_part = (df27["qtd_participantes"] > 0).sum()
    print(f"  [FIX-01] Participantes: total={df27['qtd_participantes'].sum():.0f} | "
          f"{cob_part}/{len(df27)} licitacoes com dados")

    # -------------------------------------------------------------------------
    # 1E. [FIX-04] Secretaria via UUID direto
    # -------------------------------------------------------------------------
    if not dfd.empty and "origem_arquivo" in dfd.columns and "despesas" in df27.columns:
        for col_orig, col_dest in [
            ("orgao",    "orgao_principal"),
            ("funcao",   "funcao_principal"),
            ("programa", "programa_principal"),
        ]:
            if col_orig not in dfd.columns:
                df27[col_dest] = None
                continue
            agg = (dfd.groupby("origem_arquivo")[col_orig]
                   .agg(moda_serie)
                   .reset_index()
                   .rename(columns={"origem_arquivo": "despesas", col_orig: col_dest}))
            # Remove coluna preexistente para evitar sufixo _x/_y no merge
            df27 = df27.drop(columns=[col_dest], errors="ignore")
            df27 = df27.merge(agg, on="despesas", how="left")

        cob_org = df27["orgao_principal"].notna().sum() if "orgao_principal" in df27.columns else 0
        print(f"  [FIX-04] Secretaria: {cob_org}/{len(df27)} licitacoes com orgao")
    else:
        for col in ["orgao_principal", "funcao_principal", "programa_principal"]:
            df27[col] = None
        print("  [FIX-04] Secretaria: df_despesas ausente ou sem coluna despesas")

    # -------------------------------------------------------------------------
    # 1F. Dias de tramitacao
    # -------------------------------------------------------------------------
    for col in ["dataPublicacao", "dataHomologacao"]:
        if col in df27.columns:
            df27[col] = pd.to_datetime(df27[col], errors="coerce")

    if {"dataPublicacao", "dataHomologacao"}.issubset(df27.columns):
        df27["dias_tramitacao"] = (
            (df27["dataHomologacao"] - df27["dataPublicacao"])
            .dt.days.clip(lower=0)
        )
    else:
        df27["dias_tramitacao"] = np.nan

    # -------------------------------------------------------------------------
    # 1G. Tipo de processo
    # -------------------------------------------------------------------------
    df27["tipo_processo"] = tipo_proc

    # -------------------------------------------------------------------------
    # 1H. Converter colunas monetarias de dfiv
    # -------------------------------------------------------------------------
    for col in ["valorTotalReferencia", "valorTotalVencedor",
                "valorUnitarioReferencia", "valorUnitarioVencedor", "quantidade"]:
        if col in dfiv.columns:
            dfiv[col] = para_float(dfiv[col])

    # Valor de referencia zero = placeholder do portal, tratar como nulo
    if "valorTotalReferencia" in dfiv.columns:
        dfiv.loc[dfiv["valorTotalReferencia"] == 0, "valorTotalReferencia"] = np.nan

    # -------------------------------------------------------------------------
    # 1I. Economia e ratio no nivel do item
    # -------------------------------------------------------------------------
    if {"valorTotalReferencia", "valorTotalVencedor"}.issubset(dfiv.columns):
        dfiv["economia_item"] = dfiv["valorTotalReferencia"] - dfiv["valorTotalVencedor"]
        dfiv["economia_item_pct"] = np.where(
            dfiv["valorTotalReferencia"].notna(),
            (dfiv["economia_item"] / dfiv["valorTotalReferencia"] * 100).clip(-100, 100),
            np.nan,
        )
        dfiv["ratio_vencedor_referencia"] = np.where(
            dfiv["valorTotalReferencia"].notna(),
            dfiv["valorTotalVencedor"] / dfiv["valorTotalReferencia"],
            np.nan,
        )

    # -------------------------------------------------------------------------
    # 1J. Agregados de itens por UUID de licitacao (para enriquecer df_27)
    # -------------------------------------------------------------------------
    if "origem_arquivo" in dfiv.columns:
        agg_dict = {"n_itens_licitacao": ("origem_arquivo", "count")}
        if "cnpjCpfVencedor" in dfiv.columns:
            agg_dict["n_vencedores_distintos"] = ("cnpjCpfVencedor", "nunique")
        if "economia_item_pct" in dfiv.columns:
            agg_dict["media_desconto_item"]     = ("economia_item_pct", "mean")
            agg_dict["amplitude_desconto_item"] = (
                "economia_item_pct",
                lambda x: (x.max() - x.min()) if x.notna().any() else np.nan,
            )

        agg_itens = (dfiv.groupby("origem_arquivo")
                     .agg(**agg_dict)
                     .reset_index()
                     .rename(columns={"origem_arquivo": "itensVencedores"}))

        if "itensVencedores" in df27.columns:
            df27 = df27.merge(agg_itens, on="itensVencedores", how="left")
        else:
            for col in agg_itens.columns[1:]:
                df27[col] = np.nan

    # -------------------------------------------------------------------------
    # 1K. [FIX-02] Reconstruir valorHomologado onde ausente
    # -------------------------------------------------------------------------
    df27["valorHomologado_reconstruido"] = 0

    if "itensVencedores" in df27.columns and "valorTotalVencedor" in dfiv.columns:
        soma_iv = (dfiv.groupby("origem_arquivo")["valorTotalVencedor"]
                   .sum()
                   .reset_index(name="_soma_venc")
                   .rename(columns={"origem_arquivo": "itensVencedores"}))

        df27 = df27.merge(soma_iv, on="itensVencedores", how="left")

        mask_rec = df27["valorHomologado"].isna() & df27["_soma_venc"].notna()
        df27.loc[mask_rec, "valorHomologado"]              = df27.loc[mask_rec, "_soma_venc"]
        df27.loc[mask_rec, "valorHomologado_reconstruido"] = 1
        df27 = df27.drop(columns=["_soma_venc"])

        n_rec = mask_rec.sum()
        print(f"  [FIX-02] valorHomologado reconstruido: {n_rec} licitacoes")

    # -------------------------------------------------------------------------
    # 1L. Economia ao nivel da licitacao
    # -------------------------------------------------------------------------
    if {"valorEstimado", "valorHomologado"}.issubset(df27.columns):
        df27["economia_absoluta"] = np.where(
            df27["valorEstimado"].notna() & df27["valorHomologado"].notna(),
            df27["valorEstimado"] - df27["valorHomologado"],
            np.nan,
        )
        df27["economia_pct_licit"] = np.where(
            df27["valorEstimado"].notna() & (df27["valorEstimado"] > 0),
            df27["economia_absoluta"] / df27["valorEstimado"] * 100,
            np.nan,
        )
    else:
        df27["economia_absoluta"]  = np.nan
        df27["economia_pct_licit"] = np.nan

    # -------------------------------------------------------------------------
    # 1M. Montar base no nivel do item (join dfiv <- df_27)
    # -------------------------------------------------------------------------
    if "itensVencedores" not in df27.columns:
        print(f"  [AVISO] Coluna itensVencedores ausente em {label}. Pulando fonte.")
        continue

    colunas_df27 = [c for c in [
        "chave_licitacao",
        "tipo_processo",
        "modalidade",            # ausente em Dispensa — ok, sera None
        "tipoObjeto",
        "formaJulgamento",       # ausente em Dispensa — ok, sera None
        "objeto",
        "valorEstimado",
        "valorHomologado",
        "valorHomologado_reconstruido",
        "economia_absoluta",
        "economia_pct_licit",
        "qtd_participantes",
        "dias_tramitacao",
        "n_itens_licitacao",
        "n_vencedores_distintos",
        "media_desconto_item",
        "amplitude_desconto_item",
        "orgao_principal",
        "funcao_principal",
        "programa_principal",
        "itensVencedores",
    ] if c in df27.columns]

    base_fonte = dfiv.merge(
        df27[colunas_df27],
        left_on="origem_arquivo",
        right_on="itensVencedores",
        how="inner",
    )
    base_fonte["_fonte"] = label
    frames_itens.append(base_fonte)
    print(f"  -> {len(base_fonte):,} itens exportados")


# =============================================================================
# ETAPA 2 — CONCATENAR TODAS AS FONTES
# =============================================================================

print("\n" + "=" * 60)
print("ETAPA 2 — CONCATENACAO")
print("=" * 60)

if not frames_itens:
    raise RuntimeError("Nenhum item carregado. Verifique os caminhos das pastas.")

base_final = pd.concat(frames_itens, ignore_index=True)
print(f"  Total bruto: {len(base_final):,} itens")

# Deduplicar: quando a mesma chave_licitacao existe em LICITACAO e DISPENSA,
# manter apenas a versao LICITACAO (Finalizados e a fonte mais completa/definitiva)
chaves_licitacao = set(
    base_final.loc[base_final["tipo_processo"] == "LICITACAO", "chave_licitacao"]
)
mask_dup = (
    (base_final["tipo_processo"] == "DISPENSA")
    & (base_final["chave_licitacao"].isin(chaves_licitacao))
)
n_dup = mask_dup.sum()
if n_dup > 0:
    base_final = base_final[~mask_dup].copy()
    print(f"  Deduplicacao: {n_dup:,} itens DISPENSA removidos "
          f"(chave_licitacao ja presente em LICITACAO)")
print(f"  Total apos deduplicacao: {len(base_final):,} itens")

# Garantir que colunas opcionais existam mesmo que uma fonte nao as tenha
for col, fill in [
    ("modalidade",        None),
    ("formaJulgamento",   None),
    ("orgao_principal",   None),
    ("funcao_principal",  None),
    ("programa_principal",None),
]:
    if col not in base_final.columns:
        base_final[col] = fill


# =============================================================================
# ETAPA 3 — FORNECEDORES SANCIONADOS
#   Colunas criadas:
#     vencedor_sancionado      — 1 se o CNPJ do vencedor consta na lista
#     tipo_sancao_vencedor     — sancao mais grave registrada para esse fornecedor
#                                (INIDONEIDADE > IMPEDIMENTO > SUSPENSAO >
#                                 MULTA > ADVERTENCIA)
#     sancao_ativa             — 1 se alguma sancao nao tem data de termino ou
#                                ainda esta dentro do prazo de vigencia
#     qtd_processos_sancionado — quantas licitacoes o fornecedor ja participou
#                                (conforme registrado no portal)
# =============================================================================

print("\n" + "=" * 60)
print("ETAPA 3 — FORNECEDORES SANCIONADOS")
print("=" * 60)

# Inicializar colunas com valores neutros
for col, val in [
    ("vencedor_sancionado",       0),
    ("tipo_sancao_vencedor",      None),
    ("sancao_ativa",              0),
    ("qtd_processos_sancionado",  0),
]:
    base_final[col] = val

if not os.path.isdir(PASTA_SANCIONADOS):
    print(f"  [AVISO] Pasta nao encontrada: {PASTA_SANCIONADOS}")
else:
    # ------------------------------------------------------------------
    # 3A. Carregar os tres arquivos de sancionados
    # ------------------------------------------------------------------
    df_sanc   = ler_csv(PASTA_SANCIONADOS, "df_27_unificado.csv",        "sancionados")
    df_penal  = ler_csv(PASTA_SANCIONADOS, "df_penalidades_unificado.csv","penalidades")
    df_procs  = ler_csv(PASTA_SANCIONADOS, "df_processos_unificado.csv",  "proc_sanc")

    if df_sanc.empty or "cnpjCpf" not in df_sanc.columns:
        print("  [AVISO] df_27_unificado de sancionados vazio ou sem cnpjCpf.")
    else:
        df_sanc["cnpjCpf"] = df_sanc["cnpjCpf"].astype(str).str.strip()

        # ------------------------------------------------------------------
        # 3B. vencedor_sancionado — flag binaria pelo CNPJ
        # ------------------------------------------------------------------
        col_cnpj = next(
            (c for c in ["cnpjCpfVencedor", "cnpjCpf"] if c in base_final.columns),
            None,
        )
        if col_cnpj:
            sancionados_set = set(df_sanc["cnpjCpf"])
            base_final["vencedor_sancionado"] = (
                base_final[col_cnpj].astype(str).str.strip()
                .isin(sancionados_set).astype(int)
            )
            n_sanc = base_final["vencedor_sancionado"].sum()
            print(f"  vencedor_sancionado: {n_sanc:,} itens ({100*n_sanc/len(base_final):.1f}%)")
        else:
            print("  [AVISO] Coluna CNPJ nao encontrada na base final.")

        # ------------------------------------------------------------------
        # 3C. tipo_sancao_vencedor e sancao_ativa — via df_penalidades
        # ------------------------------------------------------------------
        if not df_penal.empty and "origem_arquivo" in df_penal.columns and "penalidades" in df_sanc.columns:
            # Juntar: df_sanc['penalidades'] UUID -> df_penal['origem_arquivo']
            sanc_penal = df_sanc[["cnpjCpf", "penalidades"]].merge(
                df_penal.rename(columns={"origem_arquivo": "penalidades"}),
                on="penalidades", how="left",
            )

            # Severidade das sancoes para encontrar a mais grave por fornecedor
            GRAU = {
                "INIDONEIDADE": 5,
                "IMPEDIMENTO":  4,
                "SUSPENSAO":    3,
                "MULTA":        2,
                "ADVERTENCIA":  1,
            }

            def tipo_mais_grave(tipos):
                melhor_grau, melhor_tipo = 0, None
                for t in tipos.dropna():
                    t_upper = str(t).upper().strip()
                    for nome, grau in GRAU.items():
                        if nome in t_upper and grau > melhor_grau:
                            melhor_grau, melhor_tipo = grau, t_upper
                return melhor_tipo

            tipo_lookup = (sanc_penal.groupby("cnpjCpf")["tipoSancao"]
                           .agg(tipo_mais_grave)
                           .reset_index()
                           .rename(columns={"tipoSancao": "tipo_sancao_vencedor"}))

            # Sancao ativa: sem data de termino (permanente) OU prazo ainda vigente
            hoje = pd.Timestamp("2026-04-26")
            sanc_penal["dataVigenciaFinal"] = pd.to_datetime(
                sanc_penal["dataVigenciaFinal"], errors="coerce"
            )
            sanc_penal["_ativa"] = (
                sanc_penal["dataVigenciaFinal"].isna()
                | (sanc_penal["dataVigenciaFinal"] > hoje)
            )
            ativa_lookup = (sanc_penal.groupby("cnpjCpf")["_ativa"]
                            .any()
                            .astype(int)
                            .reset_index()
                            .rename(columns={"_ativa": "sancao_ativa"}))

            print(f"  tipo_sancao_vencedor: {tipo_lookup['tipo_sancao_vencedor'].notna().sum()} fornecedores mapeados")
            print(f"  sancao_ativa: {ativa_lookup['sancao_ativa'].sum()} fornecedores com sancao ativa")
        else:
            tipo_lookup  = pd.DataFrame(columns=["cnpjCpf", "tipo_sancao_vencedor"])
            ativa_lookup = pd.DataFrame(columns=["cnpjCpf", "sancao_ativa"])
            print("  [AVISO] df_penalidades ausente ou sem coluna origem_arquivo.")

        # ------------------------------------------------------------------
        # 3D. qtd_processos_sancionado — via df_processos
        # ------------------------------------------------------------------
        if not df_procs.empty and "origem_arquivo" in df_procs.columns and "processos" in df_sanc.columns:
            sanc_proc = df_sanc[["cnpjCpf", "processos"]].merge(
                df_procs.rename(columns={"origem_arquivo": "processos"}),
                on="processos", how="left",
            )
            qtd_lookup = (sanc_proc.groupby("cnpjCpf")
                          .size()
                          .reset_index(name="qtd_processos_sancionado"))
            print(f"  qtd_processos_sancionado: min={qtd_lookup['qtd_processos_sancionado'].min()} "
                  f"max={qtd_lookup['qtd_processos_sancionado'].max()} "
                  f"media={qtd_lookup['qtd_processos_sancionado'].mean():.1f}")
        else:
            qtd_lookup = pd.DataFrame(columns=["cnpjCpf", "qtd_processos_sancionado"])
            print("  [AVISO] df_processos ausente ou sem coluna origem_arquivo.")

        # ------------------------------------------------------------------
        # 3E. Combinar lookups e juntar na base_final pelo CNPJ do vencedor
        # ------------------------------------------------------------------
        if col_cnpj and not tipo_lookup.empty:
            lookup_completo = (tipo_lookup
                               .merge(ativa_lookup,  on="cnpjCpf", how="left")
                               .merge(qtd_lookup,    on="cnpjCpf", how="left"))
            lookup_completo["sancao_ativa"]             = lookup_completo["sancao_ativa"].fillna(0).astype(int)
            lookup_completo["qtd_processos_sancionado"] = lookup_completo["qtd_processos_sancionado"].fillna(0).astype(int)

            # Remover colunas que serao preenchidas pelo merge
            for col in ["tipo_sancao_vencedor", "sancao_ativa", "qtd_processos_sancionado"]:
                base_final = base_final.drop(columns=[col], errors="ignore")

            base_final = base_final.merge(
                lookup_completo.rename(columns={"cnpjCpf": col_cnpj}),
                on=col_cnpj, how="left",
            )

            # Fornecedores nao sancionados ficam com valores neutros
            mask_nao_sanc = base_final["vencedor_sancionado"] == 0
            base_final.loc[mask_nao_sanc, "tipo_sancao_vencedor"]      = None
            base_final.loc[mask_nao_sanc, "sancao_ativa"]              = 0
            base_final.loc[mask_nao_sanc, "qtd_processos_sancionado"]  = 0

            base_final["sancao_ativa"]             = base_final["sancao_ativa"].fillna(0).astype(int)
            base_final["qtd_processos_sancionado"] = base_final["qtd_processos_sancionado"].fillna(0).astype(int)


# =============================================================================
# ETAPA 3B — AGREGADOS POR LICITACAO (VARIAVEL ALVO + CANDIDATAS AUSENTES)
#   Calcula no nivel da licitacao e repete o valor em cada linha de item,
#   garantindo que a base contenha todas as 25 candidatas e a variavel alvo.
#
#   Colunas criadas:
#     economia_itens       — ALVO: soma(ref) - soma(vencedor) por licitacao (R$)
#     desconto_global_pct  — economia_itens / soma_ref * 100 (%)
#     media_ratio_itens    — media do ratio vencedor/referencia por licitacao
#     pct_itens_abaixo_ref — % de itens em que vencedor < referencia
# =============================================================================

print("\n" + "=" * 60)
print("ETAPA 3B — AGREGADOS POR LICITACAO (ALVO + CANDIDATAS AUSENTES)")
print("=" * 60)

_cols_req = {"valorTotalReferencia", "valorTotalVencedor", "ratio_vencedor_referencia"}
if _cols_req.issubset(base_final.columns):
    _agg_alvo = (
        base_final.groupby("chave_licitacao")
        .agg(
            _soma_ref_licit      = ("valorTotalReferencia",      "sum"),
            _soma_venc_licit     = ("valorTotalVencedor",        "sum"),
            media_ratio_itens    = ("ratio_vencedor_referencia", "mean"),
            pct_itens_abaixo_ref = ("ratio_vencedor_referencia",
                                    lambda x: (x < 1).mean() * 100),
        )
        .reset_index()
    )
    _agg_alvo["economia_itens"] = _agg_alvo["_soma_ref_licit"] - _agg_alvo["_soma_venc_licit"]
    _agg_alvo["desconto_global_pct"] = np.where(
        _agg_alvo["_soma_ref_licit"] > 0,
        (_agg_alvo["economia_itens"] / _agg_alvo["_soma_ref_licit"] * 100).clip(-100, 100),
        np.nan,
    )
    _agg_alvo = _agg_alvo.drop(columns=["_soma_ref_licit", "_soma_venc_licit"])

    base_final = base_final.merge(
        _agg_alvo[["chave_licitacao", "economia_itens", "desconto_global_pct",
                   "media_ratio_itens", "pct_itens_abaixo_ref"]],
        on="chave_licitacao", how="left",
    )
    _n_alvo = base_final["economia_itens"].notna().sum()
    print(f"  economia_itens       : {_n_alvo:,} itens com valor ({100*_n_alvo/len(base_final):.1f}%)")
    print(f"  desconto_global_pct  : calculado")
    print(f"  media_ratio_itens    : calculado")
    print(f"  pct_itens_abaixo_ref : calculado")
else:
    _falt = _cols_req - set(base_final.columns)
    print(f"  [AVISO] Colunas ausentes: {_falt} — variaveis de alvo nao calculadas.")
    for _col in ["economia_itens", "desconto_global_pct", "media_ratio_itens", "pct_itens_abaixo_ref"]:
        base_final[_col] = np.nan


# =============================================================================
# ETAPA 4 — VARIAVEIS DERIVADAS E CODIFICACOES CATEGORICAS
# =============================================================================

print("\n" + "=" * 60)
print("ETAPA 4 — VARIAVEIS DERIVADAS")
print("=" * 60)

# --- Variaveis de competicao ---
base_final["houve_disputa"] = (base_final["qtd_participantes"] > 1).astype(int)
base_final["log_qtd_participantes"] = np.log1p(base_final["qtd_participantes"])

# --- Logs de valores monetarios ---
for col_orig, col_log in [
    ("valorHomologado",        "log_valorHomologado"),
    ("valorEstimado",          "log_valorEstimado"),
    ("valorTotalReferencia",   "log_valorTotalReferencia"),
    ("valorTotalVencedor",     "log_valorTotalVencedor"),
    ("quantidade",             "log_quantidade"),
    ("n_itens_licitacao",      "log_n_itens"),
    ("n_vencedores_distintos", "log_n_vencedores"),
    ("dias_tramitacao",        "log_dias_tramitacao"),
    ("economia_absoluta",      "log_economia_absoluta"),
]:
    if col_orig in base_final.columns:
        base_final[col_log] = np.log1p(
            pd.to_numeric(base_final[col_orig], errors="coerce").clip(lower=0)
        )

# --- Variavel de interacao: competicao x escala de valor ---
if "log_valorEstimado" in base_final.columns:
    base_final["interact_part_logval"] = (
        base_final["qtd_participantes"] * base_final["log_valorEstimado"]
    )

# --- Codificacoes categoricas (para correlacao) ---
for col_orig, col_cod in [
    ("tipo_processo",    "tipo_processo_cod"),
    ("modalidade",       "modalidade_cod"),
    ("tipoObjeto",       "tipoObjeto_cod"),
    ("formaJulgamento",  "formaJulgamento_cod"),
    ("orgao_principal",  "orgao_cod"),
    ("funcao_principal", "funcao_cod"),
]:
    if col_orig in base_final.columns:
        base_final[col_cod] = codificar(base_final[col_orig])

print("  Variaveis derivadas calculadas.")
print(f"  Colunas totais antes do filtro: {base_final.shape[1]}")


# =============================================================================
# ETAPA 5 — FILTRO DE CONSISTENCIA (FIX-03)
# =============================================================================

print("\n" + "=" * 60)
print("ETAPA 5 — FILTRO DE CONSISTENCIA")
print("=" * 60)

antes = len(base_final)

# Remove itens onde o ratio nao pode ser calculado (referencia nula)
base_final = base_final[base_final["ratio_vencedor_referencia"].notna()].copy()
rem_ratio = antes - len(base_final)

# Remove itens onde valorHomologado ainda e nulo apos reconstrucao
antes2 = len(base_final)
base_final = base_final[base_final["valorHomologado"].notna()].copy()
rem_vh = antes2 - len(base_final)

# valorEstimado NAO e filtro obrigatorio (FIX-03)
n_sem_ve = base_final["valorEstimado"].isna().sum()

print(f"  Removidos por ratio invalido (ref=0 ou nulo):      {rem_ratio:,}")
print(f"  Removidos por valorHomologado nulo apos reconstrucao: {rem_vh:,}")
print(f"  Mantidos sem valorEstimado (nao filtrado):          {n_sem_ve:,}")
print(f"  Restantes: {len(base_final):,}")
print(f"  Meta 20.000: {'ATINGIDA (OK)' if len(base_final) >= 20_000 else 'NAO ATINGIDA'}")


# =============================================================================
# ETAPA 6 — EXPORTACAO
# =============================================================================

print("\n" + "=" * 60)
print("ETAPA 6 — EXPORTACAO")
print("=" * 60)

# Arredondar floats: 2 casas para valores monetarios/%, 6 para demais
kw_2dec = ["valor", "economia", "media", "soma", "ratio", "desconto",
           "pct", "variacao", "amplitude"]
for col in base_final.columns:
    if not pd.api.types.is_float_dtype(base_final[col]):
        continue
    casas = 2 if any(kw in col.lower() for kw in kw_2dec) else 6
    base_final[col] = base_final[col].round(casas)

os.makedirs("baseFinalUnificada", exist_ok=True)
base_final.to_csv(
    ARQUIVO_SAIDA,
    index=False,
    sep=";",
    decimal=",",
    encoding="utf-8-sig",
)
print(f"\n  Arquivo salvo: {os.path.abspath(ARQUIVO_SAIDA)}")
print(f"  Total de registros: {len(base_final):,}")
print(f"  Total de colunas  : {base_final.shape[1]}")


# =============================================================================
# ETAPA 7 — RESUMO DE INTEGRIDADE
# =============================================================================

print("\n" + "=" * 60)
print("RESUMO POR FONTE")
print("=" * 60)

for src, grp in base_final.groupby("_fonte"):
    n_licit   = grp["chave_licitacao"].nunique() if "chave_licitacao" in grp else 0
    med_part  = grp["qtd_participantes"].mean()
    pct_sanc  = grp["vencedor_sancionado"].mean() * 100
    med_econ  = grp["economia_item_pct"].mean() if "economia_item_pct" in grp else float("nan")
    print(f"  {src:<20} {len(grp):>6,} itens | {n_licit:>4} licit | "
          f"part_media={med_part:.1f} | sancionado={pct_sanc:.1f}% | "
          f"econ_item={med_econ:.1f}%")

print("\n" + "=" * 60)
print("RESUMO POR TIPO DE PROCESSO")
print("=" * 60)

for tp, grp in base_final.groupby("tipo_processo"):
    med_part = grp["qtd_participantes"].mean()
    med_econ = grp["economia_item_pct"].mean() if "economia_item_pct" in grp else float("nan")
    pct_sanc = grp["vencedor_sancionado"].mean() * 100
    print(f"  {tp:<12} {len(grp):>6,} itens | "
          f"part_media={med_part:.1f} | econ_item={med_econ:.1f}% | "
          f"sancionado={pct_sanc:.1f}%")

print("\n" + "=" * 60)
print("CHECAGEM DE NULOS NAS COLUNAS PRINCIPAIS")
print("=" * 60)

cols_checar = [c for c in [
    "qtd_participantes", "houve_disputa",
    "ratio_vencedor_referencia", "economia_item_pct",
    "valorHomologado", "valorEstimado",
    "economia_pct_licit", "economia_absoluta",
    "orgao_principal", "tipo_processo",
    "vencedor_sancionado",
    "dias_tramitacao",
    "n_itens_licitacao", "n_vencedores_distintos",
    "economia_itens", "desconto_global_pct",
    "media_ratio_itens", "pct_itens_abaixo_ref",
] if c in base_final.columns]

for col in cols_checar:
    nulos = base_final[col].isna().sum()
    pct   = 100 * nulos / len(base_final)
    status = "OK" if pct < 10 else ("AVISO" if pct < 50 else "CRITICO")
    print(f"  [{status:<7}] {col:<35} {nulos:>6,} nulos ({pct:.1f}%)")

print("\nProcesso concluido!")
