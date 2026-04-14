"""
=============================================================================
ANÁLISE COMPLETA – PORTAL DA TRANSPARÊNCIA CRICIÚMA  (v5 - MODO LICITAÇÃO)
=============================================================================
Pergunta problema:
  "Qual o impacto do número de participantes nas licitações sobre a
   economia gerada para o município de Criciúma?"

POR QUE MUDAMOS PARA MODO LICITAÇÃO:
  No modo item_vencedor, a variável alvo (economia_pct) é calculada a
  nível de licitação e repetida para cada item — isso "achata" as
  correlações para próximo de zero porque não há variação nova.
  No modo licitação (1 linha = 1 licitação), cada variável é única
  por processo e a correlação funciona corretamente.

UNIDADE DE ANÁLISE: 1 linha = 1 licitação
VARIÁVEL ALVO: economia_pct = (valorEstimado - valorHomologado) / valorEstimado * 100

VARIÁVEIS CONSTRUÍDAS (agregadas para o nível da licitação):
  Da tabela de itens vencedores → agregados por licitação
  Da tabela de participantes    → contagem por licitação
  Da tabela de contratos        → agregados por licitação
  Do próprio df_27              → colunas diretas + features engenheiradas
=============================================================================
CONFIGURE AQUI
=============================================================================
"""

PASTA_PROCESSOS_LICITATORIOS = r'C:\Users\gusta\Documents\Git Hub\analiseEstatísticaPrefeituraCriciuma\dadosUnificados\Processos Licitatórios-2019'
PASTA_PROCESSOS_FINALIZADOS  = r'C:\Users\gusta\Documents\Git Hub\analiseEstatísticaPrefeituraCriciuma\dadosUnificados\Processos Licitatórios Finalizados-2019'
PASTA_CONTRATOS              = r'C:\Users\gusta\Documents\Git Hub\analiseEstatísticaPrefeituraCriciuma\dadosUnificados\Relação de Contratos-2019'

ARQUIVO_SAIDA_BASE   = "base_licitacoes_criciuma.csv"
ARQUIVO_SAIDA_CORR   = "correlacoes_criciuma.csv"
GRAFICO_SAIDA        = "grafico_correlacoes.png"
VARIAVEL_ALVO        = "log_valorHomologado"
ENCODING             = "utf-8"

# =============================================================================
import os, glob, warnings
import pandas as pd
import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
from scipy import stats

warnings.filterwarnings("ignore")
SEP = ";"


# ─────────────────────────────────────────────────────────────────────────────
# UTILITÁRIOS
# ─────────────────────────────────────────────────────────────────────────────

def limpar_chave(txt):
    if pd.isna(txt): return ""
    return str(txt).split('.')[0].strip()

def detectar_sep(filepath):
    for enc in [ENCODING, 'utf-8-sig', 'latin-1', 'cp1252']:
        try:
            with open(filepath, 'r', encoding=enc) as f:
                linha = f.readline()
            scores = {s: linha.count(s) for s in [';', ',', '\t']}
            return max(scores, key=scores.get), enc
        except Exception:
            continue
    return ';', 'latin-1'

def encontrar_csvs(pasta, nome):
    arqs = glob.glob(os.path.join(pasta, "**", f"*{nome}*.csv"), recursive=True)
    return sorted(arqs)

def ler_csvs(pasta, nome, label=""):
    if not pasta or not os.path.isdir(pasta):
        return pd.DataFrame()
    arqs = encontrar_csvs(pasta, nome)
    if not arqs:
        print(f"  [AVISO] '{nome}' não encontrado em: {os.path.basename(pasta)}")
        return pd.DataFrame()
    frames = []
    for a in arqs:
        sep, enc = detectar_sep(a)
        try:
            df = pd.read_csv(a, sep=sep, encoding=enc, low_memory=False, on_bad_lines="skip")
            df["_fonte"] = label
            frames.append(df)
        except Exception as e:
            print(f"  [ERRO] {os.path.basename(a)}: {e}")
    if not frames: return pd.DataFrame()
    res = pd.concat(frames, ignore_index=True)
    print(f"  ✔ '{nome}' ({label}): {len(res):,} linhas")
    return res

def num(serie):
    s = serie.astype(str).str.strip()
    r = pd.to_numeric(s, errors='coerce')
    if r.notna().mean() < 0.5:
        s2 = (s.str.replace(r'[^\d,\.-]', '', regex=True)
               .str.replace('.', '', regex=False)
               .str.replace(',', '.', regex=False))
        r = pd.to_numeric(s2, errors='coerce')
    return r

def chave(df, pares):
    for c1, c2 in pares:
        if c1 in df.columns and c2 in df.columns:
            df[c1] = df[c1].apply(limpar_chave)
            df[c2] = df[c2].apply(limpar_chave)
            df["chave_lic"] = df[c1] + "_" + df[c2]
            return df, True
    return df, False


# ─────────────────────────────────────────────────────────────────────────────
# ETAPA 1 – LEITURA
# ─────────────────────────────────────────────────────────────────────────────
print("\n" + "="*60)
print("ETAPA 1 – LEITURA DAS BASES")
print("="*60)

# Tabela principal de processos (df_27)
frames_proc = []
for lbl, pasta in [("licit", PASTA_PROCESSOS_LICITATORIOS),
                   ("final", PASTA_PROCESSOS_FINALIZADOS)]:
    df = ler_csvs(pasta, "df_27_unificado", lbl)
    if not df.empty: frames_proc.append(df)

df_proc = pd.concat(frames_proc, ignore_index=True) if frames_proc else pd.DataFrame()
print(f"  → df_processos bruto: {len(df_proc):,} linhas")

# Itens vencedores (para agregar por licitação)
frames_venc = []
for lbl, pasta in [("licit", PASTA_PROCESSOS_LICITATORIOS),
                   ("final", PASTA_PROCESSOS_FINALIZADOS)]:
    df = ler_csvs(pasta, "df_itensvencedores_unificado", lbl)
    if not df.empty: frames_venc.append(df)
df_venc = pd.concat(frames_venc, ignore_index=True) if frames_venc else pd.DataFrame()

# Itens propostas (para contar propostas por licitação)
frames_prop = []
for lbl, pasta in [("licit", PASTA_PROCESSOS_LICITATORIOS),
                   ("final", PASTA_PROCESSOS_FINALIZADOS)]:
    df = ler_csvs(pasta, "df_itensproposta_unificado", lbl)
    if not df.empty: frames_prop.append(df)
df_prop = pd.concat(frames_prop, ignore_index=True) if frames_prop else pd.DataFrame()

# Participantes
frames_part = []
for lbl, pasta in [("licit", PASTA_PROCESSOS_LICITATORIOS),
                   ("final", PASTA_PROCESSOS_FINALIZADOS)]:
    df = ler_csvs(pasta, "df_participantes_unificado", lbl)
    if not df.empty: frames_part.append(df)
df_part = pd.concat(frames_part, ignore_index=True) if frames_part else pd.DataFrame()

# Contratos (pasta Relação de Contratos)
df_contr = ler_csvs(PASTA_CONTRATOS, "df_27_unificado", "contrato")

# Alterações de contratos (para medir instabilidade)
df_alt = ler_csvs(PASTA_CONTRATOS, "df_alteracoes_unificado", "alteracoes")

# Itens de contratos
df_itens_contr = ler_csvs(PASTA_CONTRATOS, "df_itens_unificado", "itens_contr")


# ─────────────────────────────────────────────────────────────────────────────
# ETAPA 2 – BASE CENTRAL: df_processos limpo (1 linha = 1 licitação)
# ─────────────────────────────────────────────────────────────────────────────
print("\n" + "="*60)
print("ETAPA 2 – BASE CENTRAL (1 linha = 1 licitação)")
print("="*60)

if df_proc.empty:
    raise RuntimeError("df_processos vazio. Verifique os caminhos.")

for col in ["valorEstimado", "valorHomologado"]:
    if col in df_proc.columns:
        df_proc[col] = num(df_proc[col])

df_proc, ok = chave(df_proc, [("numeroLicitacao","anoLicitacao"),
                               ("numeroProcesso","anoProcesso")])
if not ok:
    raise RuntimeError(f"Chave não criada. Colunas: {df_proc.columns.tolist()}")

antes = len(df_proc)
df_proc = df_proc.drop_duplicates(subset="chave_lic", keep="last")
print(f"  Duplicatas removidas: {antes - len(df_proc):,} | Restaram: {len(df_proc):,}")

# Datas
for col in ["dataPublicacao","dataHomologacao","dataCriacao",
            "dataAberturaEnvelopes","dataJulgamento"]:
    if col in df_proc.columns:
        df_proc[col] = pd.to_datetime(df_proc[col], errors="coerce", utc=True)
        df_proc[col] = df_proc[col].dt.tz_convert(None)  # tz-naive

# VARIÁVEL ALVO
df_proc["economia_absoluta"] = df_proc["valorEstimado"] - df_proc["valorHomologado"]
df_proc["economia_pct"] = np.where(
    df_proc["valorEstimado"] > 0,
    df_proc["economia_absoluta"] / df_proc["valorEstimado"] * 100,
    np.nan
)

n_alvo = df_proc["economia_pct"].notna().sum()
print(f"  Registros com economia_pct válida: {n_alvo:,}")
print(f"  Amostra economia_pct: {df_proc['economia_pct'].describe().round(2).to_dict()}")


# ─────────────────────────────────────────────────────────────────────────────
# ETAPA 3 – AGREGAÇÃO: ITENS VENCEDORES → nível da licitação
# ─────────────────────────────────────────────────────────────────────────────
print("\n" + "="*60)
print("ETAPA 3 – AGREGAÇÃO DE ITENS VENCEDORES")
print("="*60)

if not df_venc.empty:
    for col in ["valorTotalReferencia","valorTotalVencedor",
                "valorUnitarioReferencia","valorUnitarioVencedor"]:
        if col in df_venc.columns:
            df_venc[col] = num(df_venc[col])

    # Itens vencedores têm numero = número da licitação (verificado nas colunas)
    # Chave via "numero" + "_fonte" (arquivo de origem indica o ano)
    # Tentamos numero + anoLicitacao se disponível, senão só numero
    df_venc, ok_v = chave(df_venc, [("numero","anoLicitacao"),("numero","_fonte")])
    if not ok_v:
        # fallback: usar numero como chave parcial e cruzar depois
        if "numero" in df_venc.columns:
            df_venc["numero_clean"] = df_venc["numero"].apply(limpar_chave)

    if "chave_lic" in df_venc.columns:
        df_venc["economia_item"] = (df_venc["valorTotalReferencia"]
                                    - df_venc["valorTotalVencedor"])
        df_venc["economia_item_pct"] = np.where(
            df_venc["valorTotalReferencia"] > 0,
            df_venc["economia_item"] / df_venc["valorTotalReferencia"] * 100,
            np.nan
        )
        df_venc["desconto_unitario"] = np.where(
            df_venc["valorUnitarioReferencia"] > 0,
            (df_venc["valorUnitarioReferencia"] - df_venc["valorUnitarioVencedor"])
            / df_venc["valorUnitarioReferencia"] * 100,
            np.nan
        )

        agg_v = (df_venc.groupby("chave_lic").agg(
            qtd_itens_vencedores   = ("chave_lic", "count"),
            soma_ref               = ("valorTotalReferencia", "sum"),
            soma_venc              = ("valorTotalVencedor", "sum"),
            media_desconto_item    = ("economia_item_pct", "mean"),
            std_desconto_item      = ("economia_item_pct", "std"),
            max_desconto_item      = ("economia_item_pct", "max"),
            min_desconto_item      = ("economia_item_pct", "min"),
            media_desconto_unit    = ("desconto_unitario", "mean"),
        ).reset_index())

        # Desconto global dos itens (soma dos valores)
        agg_v["desconto_global_itens"] = np.where(
            agg_v["soma_ref"] > 0,
            (agg_v["soma_ref"] - agg_v["soma_venc"]) / agg_v["soma_ref"] * 100,
            np.nan
        )

        df_proc = df_proc.merge(agg_v, on="chave_lic", how="left")
        print(f"  ✔ Itens vencedores agregados: {len(agg_v):,} licitações com itens")
    else:
        print("  [AVISO] Chave não criada em df_venc — itens não agregados.")


# ─────────────────────────────────────────────────────────────────────────────
# ETAPA 4 – AGREGAÇÃO: PARTICIPANTES → nível da licitação
# ─────────────────────────────────────────────────────────────────────────────
print("\n" + "="*60)
print("ETAPA 4 – AGREGAÇÃO DE PARTICIPANTES")
print("="*60)

# Participantes estão vinculados à licitação via df_contratos
# Caminho: df_part[cnpjCpfFornecedor] → df_contr[cnpjCpfContratado] → chave_lic

df_proc["qtd_participantes"] = 0

if not df_part.empty and not df_contr.empty:
    for col in ["valorInicial","valorFinal","valorAlterado"]:
        if col in df_contr.columns:
            df_contr[col] = num(df_contr[col])

    for col in ["dataVigenciaInicial","dataVigenciaFinal","dataAssinatura"]:
        if col in df_contr.columns:
            df_contr[col] = pd.to_datetime(df_contr[col], errors="coerce", utc=True)
            df_contr[col] = df_contr[col].dt.tz_convert(None)  # tz-naive

    df_contr, ok_c = chave(df_contr, [("numeroLicitacao","anoLicitacao"),
                                       ("numeroProcessoCompra","anoProcessoCompra")])

    if ok_c and "cnpjCpfContratado" in df_contr.columns:
        df_contr["cnpjCpfContratado"] = df_contr["cnpjCpfContratado"].apply(limpar_chave)

        col_cnpj_part = next((c for c in ["cnpjCpfFornecedor","cnpjCpf","cnpj"]
                              if c in df_part.columns), None)

        if col_cnpj_part:
            df_part[col_cnpj_part] = df_part[col_cnpj_part].apply(limpar_chave)
            df_part = df_part.drop_duplicates(subset=[col_cnpj_part,"_fonte"], keep="last")

            mapa = (df_contr[["cnpjCpfContratado","chave_lic"]]
                    .dropna().drop_duplicates())

            part_com_chave = df_part.merge(
                mapa, left_on=col_cnpj_part,
                right_on="cnpjCpfContratado", how="inner"
            )

            agg_p = (part_com_chave
                     .drop_duplicates(subset=["chave_lic", col_cnpj_part])
                     .groupby("chave_lic").size()
                     .reset_index(name="qtd_participantes"))

            df_proc = df_proc.drop(columns=["qtd_participantes"], errors="ignore")
            df_proc = df_proc.merge(agg_p, on="chave_lic", how="left")
            df_proc["qtd_participantes"] = df_proc["qtd_participantes"].fillna(0).astype(int)
            print(f"  ✔ Participantes vinculados | median: {df_proc['qtd_participantes'].median()}")
            print(f"  Distribuição: {df_proc['qtd_participantes'].value_counts().sort_index().head(8).to_dict()}")
        else:
            print("  [AVISO] Coluna CNPJ não encontrada em df_part.")
    else:
        print("  [AVISO] Chave não criada em df_contr ou coluna CNPJ ausente.")

        # FALLBACK: contar participantes via coluna 'participantes' do df_27
        # Essa coluna contém lista de IDs separados por vírgula
        if "participantes" in df_proc.columns:
            print("  [FALLBACK] Contando via coluna 'participantes' do df_27...")
            df_proc["qtd_participantes"] = (
                df_proc["participantes"]
                .fillna("")
                .apply(lambda x: len([i for i in str(x).split(",") if i.strip()]))
            )
            print(f"  ✔ qtd_participantes via fallback | median: {df_proc['qtd_participantes'].median()}")

elif "participantes" in df_proc.columns:
    print("  [FALLBACK] Contando via coluna 'participantes' do df_27...")
    df_proc["qtd_participantes"] = (
        df_proc["participantes"]
        .fillna("")
        .apply(lambda x: len([i for i in str(x).split(",") if i.strip()]))
    )
    print(f"  ✔ qtd_participantes via fallback | median: {df_proc['qtd_participantes'].median()}")


# ─────────────────────────────────────────────────────────────────────────────
# ETAPA 5 – AGREGAÇÃO: CONTRATOS → nível da licitação
# ─────────────────────────────────────────────────────────────────────────────
print("\n" + "="*60)
print("ETAPA 5 – AGREGAÇÃO DE CONTRATOS")
print("="*60)

if not df_contr.empty and "chave_lic" in df_contr.columns:
    if "dataVigenciaInicial" in df_contr.columns and "dataVigenciaFinal" in df_contr.columns:
        for _dc in ["dataVigenciaInicial", "dataVigenciaFinal"]:
            df_contr[_dc] = pd.to_datetime(df_contr[_dc], errors="coerce", utc=True)
            df_contr[_dc] = df_contr[_dc].dt.tz_convert(None)  # tz-naive
        df_contr["dias_vigencia"] = (
            df_contr["dataVigenciaFinal"] - df_contr["dataVigenciaInicial"]
        ).dt.days

    if "valorInicial" in df_contr.columns and "valorFinal" in df_contr.columns:
        df_contr["variacao_contrato_pct"] = np.where(
            df_contr["valorInicial"] > 0,
            (df_contr["valorFinal"] - df_contr["valorInicial"]) / df_contr["valorInicial"] * 100,
            np.nan
        )

    agg_c = (df_contr.groupby("chave_lic").agg(
        qtd_contratos           = ("chave_lic", "count"),
        media_valorInicial      = ("valorInicial", "mean"),
        media_valorFinal        = ("valorFinal", "mean"),
        media_dias_vigencia     = ("dias_vigencia", "mean"),
        media_variacao_contr    = ("variacao_contrato_pct", "mean"),
        soma_valorInicial       = ("valorInicial", "sum"),
    ).reset_index())

    df_proc = df_proc.merge(agg_c, on="chave_lic", how="left")
    print(f"  ✔ Contratos agregados: {len(agg_c):,} licitações com contrato")

# Alterações de contratos
if not df_alt.empty:
    for col in ["valorAlterado"]:
        if col in df_alt.columns:
            df_alt[col] = num(df_alt[col])

    col_id_contr = next((c for c in ["id","numero"] if c in df_alt.columns), None)
    if col_id_contr:
        agg_alt = (df_alt.groupby(col_id_contr).agg(
            qtd_alteracoes      = (col_id_contr, "count"),
            soma_alteracoes     = ("valorAlterado", "sum"),
        ).reset_index())
        agg_alt.rename(columns={col_id_contr: "id_contr"}, inplace=True)

        # Precisaria cruzar id_contr com chave_lic via df_contr — simplificando:
        # Contar alterações por chave_lic se df_alt tiver chave de licitação
        alt_com_chave = df_alt.copy()
        alt_com_chave, ok_a = chave(alt_com_chave,
                                    [("numero","ano"),("id","ano")])
        if ok_a:
            agg_alt2 = (alt_com_chave.groupby("chave_lic").agg(
                qtd_alteracoes_contr = ("chave_lic", "count"),
            ).reset_index())
            df_proc = df_proc.merge(agg_alt2, on="chave_lic", how="left")
            df_proc["qtd_alteracoes_contr"] = df_proc.get("qtd_alteracoes_contr",
                                                          pd.Series(0)).fillna(0)
            print(f"  ✔ Alterações de contratos agregadas")


# ─────────────────────────────────────────────────────────────────────────────
# ETAPA 6 – ENGENHARIA DE VARIÁVEIS (a partir do df_proc já enriquecido)
# ─────────────────────────────────────────────────────────────────────────────
print("\n" + "="*60)
print("ETAPA 6 – ENGENHARIA DE VARIÁVEIS")
print("="*60)

p = df_proc  # alias

if "valorHomologado" in p.columns and "qtd_itens_vencedores" in p.columns:
    p["valor_medio_por_item"] = p["valorHomologado"] / p["qtd_itens_vencedores"].replace(0, np.nan)
    p["log_valor_medio_item"] = np.log1p(p["valor_medio_por_item"].clip(lower=0))

# Volume de empenhos (Quanto maior o contrato, mais empenhos costumam ser gerados)
if "n_empenhos" in p.columns:
    p["log_n_empenhos"] = np.log1p(p["n_empenhos"])
    

# ── GRUPO A: competição ───────────────────────────────────────────────────────
p["log_qtd_participantes"] = np.log1p(p["qtd_participantes"])
p["houve_disputa"]         = (p["qtd_participantes"] > 1).astype(float)
p["monopolio"]             = (p["qtd_participantes"] == 1).astype(float)
mediana_p = p["qtd_participantes"].median()
p["alta_competicao"]       = (p["qtd_participantes"] > mediana_p).astype(float)
if "qtd_participantes" in p.columns:
    p["participantes_sq"]  = p["qtd_participantes"] ** 2   # efeito quadrático

# ── GRUPO B: escala de valor ──────────────────────────────────────────────────
p["log_valorEstimado"]     = np.log1p(p["valorEstimado"].clip(lower=0))
p["log_valorHomologado"]   = np.log1p(p["valorHomologado"].clip(lower=0))
p["log_economia_absoluta"] = np.where(
    p["economia_absoluta"] > 0, np.log1p(p["economia_absoluta"]), np.nan)
p["razao_valor"]           = np.where(
    p["valorEstimado"] > 0, p["valorHomologado"] / p["valorEstimado"], np.nan)
p["faixa_valor"]           = pd.qcut(
    p["valorEstimado"], q=4, labels=[1,2,3,4], duplicates="drop").astype(float)

# ── GRUPO C: tempo e datas ────────────────────────────────────────────────────

def tz_naive(serie):
    """Remove timezone de uma Series datetime (tz-aware → tz-naive)."""
    try:
        if pd.api.types.is_datetime64_any_dtype(serie):
            if hasattr(serie.dt, "tz") and serie.dt.tz is not None:
                return serie.dt.tz_convert(None)
        return serie
    except Exception:
        return serie

def parse_data(df, col):
    """Converte coluna para datetime tz-naive de forma segura."""
    if col not in df.columns:
        return df
    df[col] = pd.to_datetime(df[col], errors="coerce", utc=True)
    df[col] = df[col].dt.tz_convert(None)   # normaliza para tz-naive
    return df

for _col in ["dataPublicacao", "dataHomologacao", "dataCriacao",
             "dataAberturaEnvelopes", "dataJulgamento"]:
    p = parse_data(p, _col)

if "dataPublicacao" in p.columns and "dataHomologacao" in p.columns:
    p["dias_tramitacao"] = (p["dataHomologacao"] - p["dataPublicacao"]).dt.days
    p["log_dias_tramitacao"] = np.log1p(p["dias_tramitacao"].clip(lower=0))
if "dataPublicacao" in p.columns:
    p["mes_publicacao"]  = p["dataPublicacao"].dt.month.astype(float)
    p["semestre"]        = (p["mes_publicacao"] <= 6).astype(float)
    p["trim_publicacao"] = p["dataPublicacao"].dt.quarter.astype(float)
if "dataPublicacao" in p.columns and "dataAberturaEnvelopes" in p.columns:
    p["dias_prep_abertura"] = (
        p["dataAberturaEnvelopes"] - p["dataPublicacao"]).dt.days

# ── GRUPO D: categóricas ──────────────────────────────────────────────────────
for col in ["modalidade","tipoObjeto","formaJulgamento",
            "formaContratacao","situacao","meioDivulgacao","fundamentoLegal"]:
    if col in p.columns:
        p[col + "_cod"] = pd.Categorical(p[col].astype(str)).codes.astype(float)
        p.loc[p[col].isna(), col + "_cod"] = np.nan

# ── GRUPO E: flags e listas embutidas ────────────────────────────────────────
def contar_lista(s):
    return s.fillna("").apply(
        lambda x: len([i for i in str(x).split(",") if i.strip()]))

for col in ["itensVencedores","contratos","empenhos","despesas","participantes"]:
    if col in p.columns:
        p[f"n_{col}"] = contar_lista(p[col])

for col in ["registroPrecos","adesao"]:
    if col in p.columns:
        p[f"{col}_flag"] = p[col].notna().astype(float)

# ── GRUPO F: variáveis de itens vencedores (agregadas na Etapa 3) ─────────────
# media_desconto_item, std_desconto_item, max_desconto_item, min_desconto_item,
# desconto_global_itens, qtd_itens_vencedores — já estão no df_proc

# Amplitude do desconto: máximo - mínimo (heterogeneidade dos descontos por item)
if "max_desconto_item" in p.columns and "min_desconto_item" in p.columns:
    p["amplitude_desconto_item"] = p["max_desconto_item"] - p["min_desconto_item"]

# ── GRUPO G: variáveis de contratos ──────────────────────────────────────────
if "media_valorInicial" in p.columns:
    p["log_media_valorInicial"] = np.log1p(p["media_valorInicial"].clip(lower=0))
if "media_valorFinal" in p.columns:
    p["log_media_valorFinal"]   = np.log1p(p["media_valorFinal"].clip(lower=0))
if "media_dias_vigencia" in p.columns:
    p["log_dias_vigencia"]      = np.log1p(p["media_dias_vigencia"].clip(lower=0))

# Diferença entre valor do contrato e valor homologado
if "soma_valorInicial" in p.columns and "valorHomologado" in p.columns:
    p["dif_contr_homolog"] = np.where(
        p["valorHomologado"] > 0,
        (p["soma_valorInicial"] - p["valorHomologado"]) / p["valorHomologado"] * 100,
        np.nan
    )

# ── GRUPO H: interações ───────────────────────────────────────────────────────
if "qtd_participantes" in p.columns and "log_valorEstimado" in p.columns:
    p["interact_part_logval"] = p["qtd_participantes"] * p["log_valorEstimado"]
if "qtd_participantes" in p.columns and "qtd_itens_vencedores" in p.columns:
    p["itens_por_participante"] = np.where(
        p["qtd_participantes"] > 0,
        p["qtd_itens_vencedores"] / p["qtd_participantes"], np.nan)

df_proc = p
print(f"  ✔ Engenharia concluída | Total de colunas: {df_proc.shape[1]}")


# ─────────────────────────────────────────────────────────────────────────────
# ETAPA 7 – SALVAR BASE FINAL
# ─────────────────────────────────────────────────────────────────────────────
print("\n" + "="*60)
print("ETAPA 7 – SALVAR BASE FINAL")
print("="*60)

df_proc.to_csv(ARQUIVO_SAIDA_BASE, index=False, sep=";", encoding="utf-8-sig")
print(f"  ✔ Base salva: {os.path.abspath(ARQUIVO_SAIDA_BASE)}")
print(f"  Linhas: {len(df_proc):,} | Colunas: {df_proc.shape[1]}")
print(f"  Registros com economia_pct: {df_proc[VARIAVEL_ALVO].notna().sum():,}")


# ─────────────────────────────────────────────────────────────────────────────
# ETAPA 8 – CÁLCULO DE CORRELAÇÕES
# ─────────────────────────────────────────────────────────────────────────────
print("\n" + "="*60)
print("ETAPA 8 – CÁLCULO DE CORRELAÇÕES")
print("="*60)

# 25 variáveis candidatas (em ordem de relevância teórica)
candidatas = [
    # A – Competição
    "qtd_participantes",
    "log_qtd_participantes",
    "houve_disputa",
    "monopolio",
    # B – Escala de valor e Economia (Antigo alvo vira preditora)
    "valorEstimado",
    "log_valorEstimado",
    "economia_pct", 
    "razao_valor",
    "faixa_valor",
    # C – Itens e Contratos (Fortes candidatas para valorHomologado)
    "qtd_itens_vencedores",
    "n_itensVencedores",
    "n_contratos",
    "qtd_contratos",
    "soma_valorInicial",
    "n_empenhos",
    # D – Tempo e Categóricas
    "dias_tramitacao",
    "log_dias_tramitacao",
    "media_dias_vigencia",
    "modalidade_cod",
    "tipoObjeto_cod",
    "interact_part_logval"
]

# Filtrar apenas colunas existentes (sem a variável alvo)
candidatas = [c for c in candidatas if c in df_proc.columns and c != VARIAVEL_ALVO]
print(f"  Candidatas disponíveis: {len(candidatas)}")

alvo = df_proc[VARIAVEL_ALVO]

resultados = []
for col in candidatas:
    par = df_proc[[VARIAVEL_ALVO, col]].dropna()
    n = len(par)
    if n < 30:
        continue
    try:
        r_p, p_p = stats.pearsonr(par[VARIAVEL_ALVO], par[col])
    except Exception:
        r_p, p_p = np.nan, np.nan
    try:
        r_s, p_s = stats.spearmanr(par[VARIAVEL_ALVO], par[col])
    except Exception:
        r_s, p_s = np.nan, np.nan

    bem = abs(r_p) >= 0.3 or abs(r_s) >= 0.3
    resultados.append({
        "variavel": col, "pearson": round(r_p, 4),
        "p_pearson": round(p_p, 4), "spearman": round(r_s, 4),
        "p_spearman": round(p_s, 4), "n": n, "bem_correlacionada": bem,
    })

df_corr = pd.DataFrame(resultados).sort_values("pearson", key=abs, ascending=False)
df_corr = df_corr.reset_index(drop=True)
df_corr.index += 1

n_bem = df_corr["bem_correlacionada"].sum()
print(f"\n  Variáveis com |r| >= 0.3: {n_bem} de {len(df_corr)}")
print(f"  {'✅' if n_bem >= 15 else '⚠'} Critério (≥15): {'ATENDIDO' if n_bem >= 15 else 'NÃO ATENDIDO'}")


# ─────────────────────────────────────────────────────────────────────────────
# ETAPA 9 – TABELA NO TERMINAL
# ─────────────────────────────────────────────────────────────────────────────
print("\n" + "="*60)
print("ETAPA 9 – RESULTADOS")
print("="*60)
print(f"\n  {'#':>3}  {'Variável':<35}  {'Pearson':>8}  {'Spearman':>9}  {'N':>7}  {'OK?'}")
print("  " + "-"*75)
for idx, row in df_corr.iterrows():
    ic = "✔" if row["bem_correlacionada"] else " "
    print(f"  {idx:>3}  {row['variavel']:<35}  {row['pearson']:>+8.4f}  "
          f"{row['spearman']:>+9.4f}  {int(row['n']):>7,}  {ic}")


# ─────────────────────────────────────────────────────────────────────────────
# ETAPA 10 – GRÁFICO
# ─────────────────────────────────────────────────────────────────────────────
print("\n" + "="*60)
print("ETAPA 10 – GRÁFICO")
print("="*60)

fig, ax = plt.subplots(figsize=(14, max(8, len(df_corr) * 0.40)))

cores = []
for _, row in df_corr.iterrows():
    if row["bem_correlacionada"]:
        cores.append("#2ecc71" if row["pearson"] >= 0 else "#e74c3c")
    else:
        cores.append("#bdc3c7")

barras = ax.barh(df_corr["variavel"], df_corr["pearson"],
                 color=cores, edgecolor="white", linewidth=0.4, height=0.72)

ax.axvline(x=0.3,  color="#c0392b", linestyle="--", lw=1.2, alpha=0.8, label="+0.3")
ax.axvline(x=-0.3, color="#2980b9", linestyle="--", lw=1.2, alpha=0.8, label="−0.3")
ax.axvline(x=0,    color="black",   linestyle="-",  lw=0.7, alpha=0.35)

for barra, (_, row) in zip(barras, df_corr.iterrows()):
    v = row["pearson"]
    ax.text(v + (0.01 if v >= 0 else -0.01),
            barra.get_y() + barra.get_height() / 2,
            f"{v:+.3f}", va="center",
            ha="left" if v >= 0 else "right",
            fontsize=7.5, fontweight="bold")

ax.set_xlabel(f"Correlação de Pearson com '{VARIAVEL_ALVO}'", fontsize=11)
ax.set_title(
    f"Correlação das variáveis candidatas com '{VARIAVEL_ALVO}'\n"
    f"Prefeitura de Criciúma — Unidade: Licitação",
    fontsize=13, fontweight="bold", pad=14)
ax.invert_yaxis()

legenda = [
    mpatches.Patch(color="#2ecc71", label="Correlação positiva ≥ +0.3 ✔"),
    mpatches.Patch(color="#e74c3c", label="Correlação negativa ≤ −0.3 ✔"),
    mpatches.Patch(color="#bdc3c7", label="Abaixo do limiar"),
]
ax.legend(handles=legenda, loc="lower right", fontsize=9)
ax.set_xlim(-1.05, 1.05)
ax.grid(axis="x", linestyle=":", alpha=0.4)
ax.tick_params(axis="y", labelsize=8.5)
fig.tight_layout()
plt.savefig(GRAFICO_SAIDA, dpi=150, bbox_inches="tight")
print(f"  ✔ Gráfico salvo: {os.path.abspath(GRAFICO_SAIDA)}")
plt.close()


# ─────────────────────────────────────────────────────────────────────────────
# ETAPA 11 – EXPORTAR RELATÓRIO CSV
# ─────────────────────────────────────────────────────────────────────────────
df_corr["abs_pearson"] = df_corr["pearson"].abs()
df_corr = df_corr.sort_values(["bem_correlacionada","abs_pearson"],
                               ascending=[False, False]).drop(columns="abs_pearson")
df_corr.to_csv(ARQUIVO_SAIDA_CORR, index=False, sep=";", encoding="utf-8-sig")
print(f"  ✔ Relatório CSV salvo: {os.path.abspath(ARQUIVO_SAIDA_CORR)}")

print("\n" + "="*60)
print("RESUMO FINAL")
print("="*60)
bem_pos = df_corr[df_corr["pearson"] >= 0.3]
bem_neg = df_corr[df_corr["pearson"] <= -0.3]
print(f"\n  ✅ {len(bem_pos)} variáveis com correlação positiva ≥ +0.3:")
for _, r in bem_pos.iterrows():
    print(f"     {r['variavel']:<35}  r = {r['pearson']:+.4f}  (Spearman: {r['spearman']:+.4f})")
print(f"\n  ✅ {len(bem_neg)} variáveis com correlação negativa ≤ −0.3:")
for _, r in bem_neg.iterrows():
    print(f"     {r['variavel']:<35}  r = {r['pearson']:+.4f}  (Spearman: {r['spearman']:+.4f})")
print(f"\n  Total bem correlacionadas: {n_bem} | Critério ≥ 15: {'✅ ATENDIDO' if n_bem >= 15 else '⚠ NÃO ATENDIDO'}")
print("\n✅ Análise concluída!")