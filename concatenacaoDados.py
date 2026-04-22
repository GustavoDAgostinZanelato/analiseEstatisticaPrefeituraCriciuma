"""
=============================================================================
UNIFICACAO DE BASES - PORTAL DA TRANSPARENCIA CRICIUMA (v10)
=============================================================================
Pergunta problema:
  "Qual o impacto da competicao (numero de participantes) e do tipo de gasto
   (Secretaria/Programa) na economia gerada e na eficiencia da execucao
   financeira do municipio de Criciuma?"

=============================================================================
CORRECOES v8 (sobre v7)
=============================================================================

  [FIX #4 - CONTRATOS COM anoLicitacao EM BRANCO]
    Causa: 37 contratos na Relacao de Contratos tinham anoLicitacao = " ",
    gerando chave "10_" em vez de "10_2019" -> join com df_processos falhava.
    Solucao: preencher anoLicitacao em branco com a coluna 'ano' (sempre
    preenchida nesse arquivo).

  [FIX #5 - DESPESAS 100% NULOS (licitacao e credor como nomes de arquivo)]
    Causa: as colunas 'licitacao' e 'credor' em df_27 de despesas contem
    nomes de arquivo CSV (ex: licitacao_cf3d7cf0.csv), nao dados diretos.
    A funcao extrair_numero_licitacao extraia digitos do UUID como numero.
    Solucao: fazer JOIN com df_licitacao_unificado.csv e df_credor_unificado.csv
    (ja gerados pelo script.py) usando o nome do arquivo como chave.

  [FIX #6 - DUPLICATAS DE Processos Licitatorios x Processos Finalizados]
    Causa: os dois datasets do portal sao o mesmo conjunto de dados; a coluna
    'origem_arquivo' diferia entre eles, impedindo o drop_duplicates.
    Solucao: excluir 'origem_arquivo' da chave de deduplicacao na base final.

  [FIX #7 - SUPORTE A MULTIPLOS ANOS]
    Para adicionar um novo ano: rode script.py em cada pasta do novo ano,
    depois adicione uma entrada em CONFIGURACAO_ANOS abaixo.

=============================================================================
NOVIDADES v9/v10 - 6 VARIAVEIS CANDIDATAS ADICIONADAS
=============================================================================

  Variaveis derivadas de fontes ja existentes, incorporadas diretamente
  ao pipeline para enriquecer as correlacoes em calcularCorrelacoes.py:

  [VAR #1 - dias_tramitacao]
    Dias entre dataPublicacao e dataHomologacao da licitacao.
    Hipotese: processos com menor competicao tramitam mais rapido.

  [VAR #2 - log_dias_tramitacao]
    log(dias_tramitacao + 1). Reduz assimetria positiva de dias_tramitacao.

  [VAR #3 - media_variacao_contr]
    (media_valorFinal - media_valorInicial) / media_valorInicial * 100.
    Percentual medio de variacao (aditivos) dos contratos da licitacao.

  [VAR #4 - interact_part_logval]
    qtd_participantes * log(valorEstimado + 1).
    Captura se o efeito da competicao e maior em contratos de alto valor.

  [VAR #5 - formaJulgamento_cod]
    Codificacao categorica de formaJulgamento (menor preco, melhor tecnica,
    tecnica e preco, etc). Diferente de modalidade e tipo de objeto.

  [VAR #6 - amplitude_desconto_item / media_desconto_item]
    Amplitude = max(economia_item_pct) - min(economia_item_pct) por licitacao.
    Media = media dos descontos por item. Ambas indicam heterogeneidade dos
    precos ofertados pelos vencedores.

=============================================================================
CONFIGURE AQUI ANTES DE RODAR
=============================================================================
"""

import os

# Diretorio raiz dos dados ja unificados pelo script.py
# Caminho relativo ao arquivo deste script (portavel entre maquinas).
BASE_DIR = os.path.join(
    os.path.dirname(os.path.abspath(__file__)),
    "dadosUnificados",
)

# =============================================================================
# CONFIGURACAO DE ANOS
# Cada entrada representa um ano baixado do portal da transparencia.
# Para adicionar um novo ano:
#   1. Baixe as pastas do portal para C:\Users\gusta\Desktop\Projeto Extensao Estatistica
#   2. Ajuste o caminho em script.py e rode-o para cada pasta do novo ano
#   3. Adicione uma nova entrada aqui com os caminhos gerados pelo script.py
# =============================================================================
CONFIGURACAO_ANOS = [
    {
        "ano": "2019",
        "processos_licitatorios": os.path.join(BASE_DIR, "Processos Licitatórios-2019"),
        "processos_finalizados":  os.path.join(BASE_DIR, "Processos Licitatórios Finalizados-2019"),
        "dispensa":               os.path.join(BASE_DIR, "Dispensa de Licitação-2019"),
        "inexigibilidade":        os.path.join(BASE_DIR, "Inexigibilidade de Licitação-2019"),
        "contratos":              os.path.join(BASE_DIR, "Relação de Contratos-2019"),
        "despesas":               os.path.join(BASE_DIR, "Execução Detalhada de Despesas-2019"),
    },
    # Descomente e ajuste para adicionar outro ano apos rodar script.py:
    {
        "ano": "2020",
        "processos_licitatorios": os.path.join(BASE_DIR, "Processos Licitatórios-2020"),
        "processos_finalizados":  os.path.join(BASE_DIR, "Processos Licitatórios Finalizados-2020"),
        "dispensa":               os.path.join(BASE_DIR, "Dispensa de Licitação-2020"),
        "inexigibilidade":        os.path.join(BASE_DIR, "Inexigibilidade de Licitação-2020"),
        "contratos":              os.path.join(BASE_DIR, "Relação de Contratos-2020"),
        "despesas":               os.path.join(BASE_DIR, "Execução Detalhada de Despesas-2020"),
    },
]

PASTA_SANCIONADOS = os.path.join(BASE_DIR, "Fornecedores sancionados")
ARQUIVO_SAIDA     = "baseFinalUnificada/base_unificada_criciuma_v13.csv"
ENCODING          = "utf-8"

# Derivar variaveis de compatibilidade para o restante do codigo
_cfg_principal  = CONFIGURACAO_ANOS[0]
PASTA_PROCESSOS_LICITATORIOS = _cfg_principal["processos_licitatorios"]
PASTA_PROCESSOS_FINALIZADOS  = _cfg_principal["processos_finalizados"]
PASTA_DISPENSA               = _cfg_principal["dispensa"]
PASTA_INEXIGIBILIDADE        = _cfg_principal["inexigibilidade"]
PASTA_CONTRATOS              = _cfg_principal["contratos"]
PASTA_DESPESAS               = _cfg_principal["despesas"]

# Listas de todas as fontes de contratos e despesas (multi-ano)
FONTES_CONTRATOS_LISTA = [
    (f"contrato_{cfg['ano']}", cfg["contratos"])
    for cfg in CONFIGURACAO_ANOS
    if cfg.get("contratos") and os.path.isdir(cfg["contratos"])
]
FONTES_DESPESAS_LISTA = [
    (f"despesas_{cfg['ano']}", cfg["despesas"])
    for cfg in CONFIGURACAO_ANOS
    if cfg.get("despesas") and os.path.isdir(cfg["despesas"])
]

# =============================================================================
import glob, warnings, re
import pandas as pd
import numpy as np

warnings.filterwarnings("ignore")


# -----------------------------------------------------------------------------
# FUNCOES AUXILIARES
# -----------------------------------------------------------------------------

def limpar_chave(txt):
    if pd.isna(txt):
        return ""
    return str(txt).split('.')[0].strip()


def detectar_separador(filepath, encoding="utf-8"):
    for enc in [encoding, "utf-8-sig", "latin-1", "cp1252"]:
        try:
            with open(filepath, "r", encoding=enc) as f:
                linha1 = f.readline()
                linha2 = f.readline()
            candidatos = {";": linha1.count(";"), ",": linha1.count(","), "\t": linha1.count("\t")}
            melhor_sep, melhor_score = ";", -1
            for sep, cnt in candidatos.items():
                if cnt == 0:
                    continue
                c1 = len(linha1.split(sep))
                c2 = len(linha2.split(sep)) if linha2.strip() else c1
                score = cnt * (1 if abs(c1 - c2) <= 2 else 0)
                if score > melhor_score:
                    melhor_score, melhor_sep = score, sep
            return melhor_sep, enc
        except (UnicodeDecodeError, PermissionError):
            continue
    return ";", "latin-1"


def encontrar_csvs(pasta_raiz, nome_arquivo):
    padrao = os.path.join(pasta_raiz, "**", f"*{nome_arquivo}*.csv")
    arquivos = glob.glob(padrao, recursive=True)
    if not arquivos:
        padrao2 = os.path.join(pasta_raiz, "**", f"*{nome_arquivo}*")
        arquivos = [f for f in glob.glob(padrao2, recursive=True)
                    if os.path.isfile(f) and not f.endswith(".xlsx")]
    return sorted(arquivos)


def ler_csvs(pasta_raiz, nome_arquivo, label=""):
    arquivos = encontrar_csvs(pasta_raiz, nome_arquivo)
    if not arquivos:
        print(f"  [AVISO] '{nome_arquivo}' nao encontrado em: {pasta_raiz}")
        return pd.DataFrame()
    frames, seps = [], set()
    for arq in arquivos:
        sep, enc = detectar_separador(arq, encoding=ENCODING)
        seps.add(sep)
        try:
            df = pd.read_csv(arq, sep=sep, encoding=enc,
                             low_memory=False, on_bad_lines="skip", dtype=str)
            df["_fonte"]          = label
            df["_arquivo_origem"] = os.path.basename(arq)
            frames.append(df)
        except Exception as e:
            print(f"  [ERRO] {os.path.basename(arq)}: {e}")
    if not frames:
        return pd.DataFrame()
    resultado = pd.concat(frames, ignore_index=True)
    seps_str = ", ".join(f"'{s}'" for s in seps)
    print(f"  OK '{nome_arquivo}' ({label}): {len(resultado):,} linhas | "
          f"{resultado.shape[1]} colunas | sep: {seps_str}")
    return resultado


def normalizar_moeda(serie):
    """Converte string para float, tentando EN e depois BR."""
    s = serie.astype(str).str.strip().replace({"nan": None, "None": None, "": None})
    resultado = pd.to_numeric(s, errors="coerce")
    if len(resultado) > 0 and resultado.notna().mean() >= 0.5:
        return resultado
    print("  [INFO] Usando fallback BR (virgula decimal)...")
    s_br = (s
            .str.replace(r"\s", "", regex=True)
            .str.replace(r"[^\d,\.\-]", "", regex=True)
            .str.replace(r"\.(?=\d{3}[,\.])", "", regex=True)
            .str.replace(",", ".", regex=False))
    return pd.to_numeric(s_br, errors="coerce")


def preparar_chave(df, cols_candidatas):
    """Cria coluna 'chave_licitacao' = numero + '_' + ano."""
    for col_num, col_ano in cols_candidatas:
        if col_num in df.columns and col_ano in df.columns:
            df[col_num] = df[col_num].apply(limpar_chave)
            df[col_ano] = df[col_ano].apply(limpar_chave)
            df["chave_licitacao"] = df[col_num] + "_" + df[col_ano]
            return df, True
    return df, False


def diagnostico_merge(nome, chaves_esq, chaves_dir):
    intersecao = chaves_esq & chaves_dir
    pct = len(intersecao) / max(len(chaves_esq), 1) * 100
    print(f"  Diagnostico '{nome}':")
    print(f"    Esq: {len(chaves_esq):,}  Dir: {len(chaves_dir):,}  "
          f"Casam: {len(intersecao):,} ({pct:.1f}%)")
    if len(intersecao) == 0:
        print(f"    [ERRO CRITICO] Nenhuma chave casou!")
        print(f"    Exemplos esq: {list(chaves_esq)[:5]}")
        print(f"    Exemplos dir: {list(chaves_dir)[:5]}")


def extrair_numero_licitacao(col_licitacao):
    """
    FIX #1 - Extrai numeroLicitacao da coluna 'licitacao' de df_despesas.

    O campo pode conter o numero puro ('72'), um objeto JSON
    ('{"numeroLicitacao":"72","dataLicitacao":"..."}') ou estar vazio.
    Tenta as seguintes estrategias em ordem:
      1. JSON: procura 'numeroLicitacao' com regex
      2. Numero puro: converte diretamente
    """
    def _extrair_um(val):
        if pd.isna(val) or str(val).strip() in ("", "nan", "None"):
            return None
        s = str(val).strip()
        # Tentativa 1: campo JSON com chave numeroLicitacao
        m = re.search(r'"numeroLicitacao"\s*:\s*"?(\d+)"?', s)
        if m:
            return m.group(1)
        # Tentativa 2: campo JSON com chave numero
        m = re.search(r'"numero"\s*:\s*"?(\d+)"?', s)
        if m:
            return m.group(1)
        # Tentativa 3: numero puro
        s_num = re.sub(r"[^\d]", "", s)
        return s_num if s_num else None

    return col_licitacao.apply(_extrair_um)


# -----------------------------------------------------------------------------
# ETAPA 1 - LEITURA DAS BASES DE PROCESSOS
# -----------------------------------------------------------------------------

print("\n" + "="*60)
print("ETAPA 1 - LEITURA DAS BASES DE PROCESSOS")
print("="*60)

# Construir lista de fontes para todos os anos configurados
FONTES_PROCESSOS = []
for _cfg in CONFIGURACAO_ANOS:
    _ano = _cfg["ano"]
    for _key, _label in [
        ("processos_licitatorios", f"licit_{_ano}"),
        ("processos_finalizados",  f"finalizado_{_ano}"),
        ("dispensa",               f"dispensa_{_ano}"),
        ("inexigibilidade",        f"inexigib_{_ano}"),
    ]:
        if _cfg.get(_key) and os.path.isdir(_cfg[_key]):
            FONTES_PROCESSOS.append((_label, _cfg[_key]))

frames_proc = []
frames_part = []
frames_venc = []

for label, pasta in FONTES_PROCESSOS:
    if not pasta or not os.path.isdir(pasta):
        print(f"  [AVISO] Pasta nao encontrada: {pasta}")
        continue
    df27 = ler_csvs(pasta, "df_27_unificado",             label)
    if not df27.empty:  frames_proc.append(df27)
    dfp  = ler_csvs(pasta, "df_participantes_unificado",  label)
    if not dfp.empty:   frames_part.append(dfp)
    dfv  = ler_csvs(pasta, "df_itensvencedores_unificado",label)
    if not dfv.empty:   frames_venc.append(dfv)

df_processos = pd.concat(frames_proc, ignore_index=True) if frames_proc else pd.DataFrame()
df_part      = pd.concat(frames_part, ignore_index=True) if frames_part else pd.DataFrame()
df_venc      = pd.concat(frames_venc, ignore_index=True) if frames_venc else pd.DataFrame()

print(f"\n  -> df_processos bruto : {len(df_processos):,} linhas")
print(f"  -> df_participantes   : {len(df_part):,} linhas")
print(f"  -> df_itensvencedores : {len(df_venc):,} linhas")


# -----------------------------------------------------------------------------
# ETAPA 2 - PREPARACAO DO df_processos
# -----------------------------------------------------------------------------

print("\n" + "="*60)
print("ETAPA 2 - PREPARACAO DO df_processos")
print("="*60)

if df_processos.empty:
    raise RuntimeError("df_processos esta vazio. Verifique os caminhos.")

for col in ["valorEstimado", "valorHomologado"]:
    if col in df_processos.columns:
        df_processos[col] = normalizar_moeda(df_processos[col])

df_processos, ok = preparar_chave(
    df_processos,
    [("numeroLicitacao", "anoLicitacao"), ("numeroProcesso", "anoProcesso")]
)
if not ok:
    raise RuntimeError(f"Chave nao criada em df_processos. Colunas: {df_processos.columns.tolist()}")

# Preencher modalidade para Dispensa/Inexigibilidade
if "modalidade" not in df_processos.columns:
    df_processos["modalidade"] = None
df_processos["modalidade"] = df_processos["modalidade"].fillna(df_processos["_fonte"])

antes = len(df_processos)
df_processos = df_processos.drop_duplicates(subset="chave_licitacao", keep="last")
print(f"  Duplicatas removidas: {antes - len(df_processos):,} | Restaram: {len(df_processos):,}")

df_processos["economia_absoluta"] = (df_processos["valorEstimado"]
                                     - df_processos["valorHomologado"])
df_processos["economia_pct"] = np.where(
    df_processos["valorEstimado"] > 0,
    (df_processos["economia_absoluta"] / df_processos["valorEstimado"]) * 100,
    np.nan
)
print(f"  Chaves unicas: {df_processos['chave_licitacao'].nunique():,}")

# VAR #1 e #2: dias_tramitacao e log_dias_tramitacao
# dataPublicacao e dataHomologacao existem no df_27 de todas as pastas de processos.
for _col_dt in ["dataPublicacao", "dataHomologacao"]:
    if _col_dt in df_processos.columns:
        df_processos[_col_dt] = pd.to_datetime(
            df_processos[_col_dt], errors="coerce", utc=True
        )
        df_processos[_col_dt] = df_processos[_col_dt].dt.tz_convert(None)

if {"dataPublicacao", "dataHomologacao"}.issubset(df_processos.columns):
    df_processos["dias_tramitacao"] = (
        df_processos["dataHomologacao"] - df_processos["dataPublicacao"]
    ).dt.days.clip(lower=0)
    df_processos["log_dias_tramitacao"] = np.log1p(df_processos["dias_tramitacao"])
    _validos_dt = df_processos["dias_tramitacao"].notna().sum()
    print(f"  dias_tramitacao calculados: {_validos_dt:,} de {len(df_processos):,}")
else:
    print("  [AVISO] dataPublicacao ou dataHomologacao ausentes - dias_tramitacao ignorado.")


# -----------------------------------------------------------------------------
# ETAPA 3 - PREPARACAO DO df_contratos
#
# FIX #3: calcular dias_vigencia ANTES de concatenar os contratos extras,
# pois apenas o df_27 da Relacao de Contratos tem dataVigenciaInicial/Final.
# -----------------------------------------------------------------------------

print("\n" + "="*60)
print("ETAPA 3 - PREPARACAO DO df_contratos")
print("="*60)

# 3A: Relacao de Contratos de todos os anos (tem dataVigenciaInicial/Final e valorInicial/Final)
_frames_contr_principal = []
for _label_c, _pasta_c in FONTES_CONTRATOS_LISTA:
    _dfc = ler_csvs(_pasta_c, "df_27_unificado", _label_c)
    if not _dfc.empty:
        _frames_contr_principal.append(_dfc)
df_contratos_principal = (pd.concat(_frames_contr_principal, ignore_index=True)
                          if _frames_contr_principal else pd.DataFrame())

if not df_contratos_principal.empty:
    for col in ["valorInicial", "valorFinal", "valorAlterado"]:
        if col in df_contratos_principal.columns:
            df_contratos_principal[col] = normalizar_moeda(df_contratos_principal[col])

    # FIX #3: calcular dias_vigencia aqui, antes do concat
    for col in ["dataVigenciaInicial", "dataVigenciaFinal"]:
        if col in df_contratos_principal.columns:
            df_contratos_principal[col] = pd.to_datetime(
                df_contratos_principal[col], errors="coerce", dayfirst=True
            )
    if {"dataVigenciaInicial", "dataVigenciaFinal"}.issubset(df_contratos_principal.columns):
        df_contratos_principal["dias_vigencia"] = (
            df_contratos_principal["dataVigenciaFinal"]
            - df_contratos_principal["dataVigenciaInicial"]
        ).dt.days
        validos = df_contratos_principal["dias_vigencia"].notna().sum()
        print(f"  dias_vigencia calculados: {validos:,} de {len(df_contratos_principal):,}")

    # FIX #4: preencher anoLicitacao/anoProcessoCompra em branco com coluna 'ano'
    # (Relacao de Contratos tem 'ano' sempre preenchido, mas 'anoLicitacao' pode ser ' ')
    for col_ano in ["anoLicitacao", "anoProcessoCompra"]:
        if col_ano in df_contratos_principal.columns and "ano" in df_contratos_principal.columns:
            mask_blank = df_contratos_principal[col_ano].str.strip().eq("")
            df_contratos_principal.loc[mask_blank, col_ano] = (
                df_contratos_principal.loc[mask_blank, "ano"]
            )
            fixados = mask_blank.sum()
            if fixados > 0:
                print(f"  {col_ano}: {fixados:,} brancos preenchidos com coluna 'ano'")

    df_contratos_principal, ok = preparar_chave(
        df_contratos_principal,
        [("numeroLicitacao", "anoLicitacao"), ("numeroProcessoCompra", "anoProcessoCompra")]
    )
    if ok and "cnpjCpfContratado" in df_contratos_principal.columns:
        df_contratos_principal["cnpjCpfContratado"] = (
            df_contratos_principal["cnpjCpfContratado"].apply(limpar_chave)
        )

# 3B: df_contratos_unificado das pastas de processos (tem 'valor' mas NAO tem dias_vigencia)
frames_contr_extra = []
for label, pasta in FONTES_PROCESSOS:
    if pasta and os.path.isdir(pasta):
        dfc = ler_csvs(pasta, "df_contratos_unificado", label + "_contr")
        if not dfc.empty:
            # Normalizar coluna 'valor' -> mapear para valorInicial/valorFinal
            if "valor" in dfc.columns:
                dfc["valor"] = normalizar_moeda(dfc["valor"])
                if "valorInicial" not in dfc.columns:
                    dfc["valorInicial"] = dfc["valor"]
                if "valorFinal" not in dfc.columns:
                    dfc["valorFinal"] = dfc["valor"]
            # Esses contratos nao tem dataVigencia -> dias_vigencia sera NaN (correto)
            dfc["dias_vigencia"] = np.nan
            frames_contr_extra.append(dfc)

# 3C: Concatenar todos os contratos
frames_todos_contr = []
if not df_contratos_principal.empty:
    frames_todos_contr.append(df_contratos_principal)
if frames_contr_extra:
    frames_todos_contr.append(pd.concat(frames_contr_extra, ignore_index=True))

df_contratos = pd.concat(frames_todos_contr, ignore_index=True) if frames_todos_contr else pd.DataFrame()

if df_contratos.empty:
    print("  [AVISO] df_contratos vazio.")
else:
    # Criar chave_licitacao nos contratos extras que ainda nao tem
    if "chave_licitacao" not in df_contratos.columns:
        df_contratos, _ = preparar_chave(
            df_contratos,
            [("numeroLicitacao", "anoLicitacao"), ("numeroProcessoCompra", "anoProcessoCompra")]
        )
    else:
        # Garantir que contratos extras tambem tenham chave_licitacao
        mask_sem_chave = df_contratos["chave_licitacao"].isna()
        if mask_sem_chave.any():
            df_tmp = df_contratos[mask_sem_chave].copy()
            df_tmp, ok_tmp = preparar_chave(
                df_tmp,
                [("numeroLicitacao", "anoLicitacao"), ("numeroProcessoCompra", "anoProcessoCompra")]
            )
            if ok_tmp:
                df_contratos.loc[mask_sem_chave, "chave_licitacao"] = df_tmp["chave_licitacao"]

    if "cnpjCpfContratado" not in df_contratos.columns and "cnpjCpf" in df_contratos.columns:
        df_contratos["cnpjCpfContratado"] = df_contratos["cnpjCpf"]
    if "cnpjCpfContratado" in df_contratos.columns:
        df_contratos["cnpjCpfContratado"] = df_contratos["cnpjCpfContratado"].apply(limpar_chave)

    # Deduplicar
    antes_c = len(df_contratos)
    chave_dedup_c = [c for c in ["chave_licitacao", "cnpjCpfContratado"] if c in df_contratos.columns]
    df_contratos = df_contratos.drop_duplicates(subset=chave_dedup_c, keep="last")
    print(f"  Duplicatas removidas de df_contratos: {antes_c - len(df_contratos):,}")

    diagnostico_merge(
        "contratos -> processos",
        set(df_contratos["chave_licitacao"].dropna()) - {""},
        set(df_processos["chave_licitacao"].dropna()) - {""}
    )

    # Usar dias_vigencia da Relacao de Contratos (unica fonte com as datas)
    agg_contr = (df_contratos.groupby("chave_licitacao")
                 .agg(
                     qtd_contratos       = ("chave_licitacao", "count"),
                     media_valorInicial  = ("valorInicial",    "mean"),
                     media_valorFinal    = ("valorFinal",      "mean"),
                     media_dias_vigencia = ("dias_vigencia",   "mean"),  # NaN ignorado pelo mean()
                 )
                 .reset_index())

    df_processos = df_processos.merge(agg_contr, on="chave_licitacao", how="left")
    preenchidos = df_processos["media_dias_vigencia"].notna().sum()
    print(f"  OK Contratos vinculados | media_dias_vigencia preenchida: "
          f"{preenchidos:,} de {len(df_processos):,} licitacoes "
          f"({preenchidos/len(df_processos)*100:.1f}%)")

    # VAR #3: media_variacao_contr - variacao percentual media dos contratos
    if {"media_valorInicial", "media_valorFinal"}.issubset(df_processos.columns):
        df_processos["media_variacao_contr"] = np.where(
            df_processos["media_valorInicial"] > 0,
            (df_processos["media_valorFinal"] - df_processos["media_valorInicial"])
            / df_processos["media_valorInicial"] * 100,
            np.nan
        )
        _validos_vc = df_processos["media_variacao_contr"].notna().sum()
        print(f"  media_variacao_contr calculada: {_validos_vc:,} licitacoes")


# -----------------------------------------------------------------------------
# ETAPA 4 - CONTAGEM DE PARTICIPANTES
# -----------------------------------------------------------------------------

print("\n" + "="*60)
print("ETAPA 4 - CONTAGEM DE PARTICIPANTES")
print("="*60)

df_processos["qtd_participantes"] = 0
df_processos["houve_disputa"]     = 0

if df_part.empty:
    print("  [AVISO] df_participantes vazio.")
elif df_contratos.empty or "chave_licitacao" not in df_contratos.columns:
    print("  [AVISO] df_contratos sem chave_licitacao.")
else:
    col_cnpj_part = next(
        (c for c in ["cnpjCpfFornecedor", "cnpjCpf", "cnpj", "cpf"] if c in df_part.columns), None
    )
    if col_cnpj_part is None:
        print("  [ERRO] Coluna CNPJ nao encontrada em df_part.")
    else:
        df_part[col_cnpj_part] = df_part[col_cnpj_part].apply(limpar_chave)

        mapa_part = (df_contratos[["cnpjCpfContratado", "chave_licitacao"]]
                     .dropna().drop_duplicates())

        diagnostico_merge(
            "participantes (CNPJ) -> contratos",
            set(df_part[col_cnpj_part].dropna()),
            set(mapa_part["cnpjCpfContratado"].dropna())
        )

        df_part_chave = df_part.merge(
            mapa_part, left_on=col_cnpj_part, right_on="cnpjCpfContratado", how="inner"
        )

        # BUG #7: deduplicar por (cnpj + chave), sem _arquivo_origem
        antes_p = len(df_part_chave)
        df_part_chave = df_part_chave.drop_duplicates(
            subset=[col_cnpj_part, "chave_licitacao"], keep="last"
        )
        print(f"  Duplicatas removidas de df_part: {antes_p - len(df_part_chave):,}")

        if not df_part_chave.empty:
            agg_part = (df_part_chave.groupby("chave_licitacao")
                        .size().reset_index(name="qtd_participantes"))
            df_processos = df_processos.drop(columns=["qtd_participantes"], errors="ignore")
            df_processos = df_processos.merge(agg_part, on="chave_licitacao", how="left")
            df_processos["qtd_participantes"] = df_processos["qtd_participantes"].fillna(0).astype(int)
            print(f"  OK Participantes vinculados: {len(df_part_chave):,}")
            print(df_processos["qtd_participantes"].value_counts().sort_index().head(10).to_string())

    df_processos["houve_disputa"] = (df_processos["qtd_participantes"] > 1).astype(int)

# VAR #4: interact_part_logval - interacao entre competicao e escala de valor
if "valorEstimado" in df_processos.columns:
    df_processos["interact_part_logval"] = (
        df_processos["qtd_participantes"]
        * np.log1p(df_processos["valorEstimado"].clip(lower=0))
    )
    print(f"  interact_part_logval calculado: "
          f"{df_processos['interact_part_logval'].notna().sum():,} licitacoes")

# VAR #5: formaJulgamento_cod - codificacao categorica de formaJulgamento
if "formaJulgamento" in df_processos.columns:
    df_processos["formaJulgamento_cod"] = (
        pd.Categorical(df_processos["formaJulgamento"].astype(str)).codes.astype(float)
    )
    df_processos.loc[df_processos["formaJulgamento"].isna(), "formaJulgamento_cod"] = np.nan
    _cats_fj = df_processos["formaJulgamento"].dropna().unique()
    print(f"  formaJulgamento_cod: {len(_cats_fj)} categorias: "
          f"{sorted(str(c) for c in _cats_fj)}")


# -----------------------------------------------------------------------------
# ETAPA 5 - EXECUCAO DETALHADA DE DESPESAS
#
# FIX #1: usar coluna 'licitacao' de df_27_unificado (ja tem o numeroLicitacao)
# em vez de tentar cruzar via _arquivo_origem com df_licitacao_unificado.
#
# Estrutura da coluna 'licitacao':
#   - Pode ser um numero puro:  "72"
#   - Pode ser JSON:            {"numeroLicitacao":"72","dataLicitacao":"..."}
#   - Pode ser vazio/nulo
#
# Estrategia:
#   a) Extrair numeroLicitacao da coluna 'licitacao' com regex
#   b) Inferir ano pelo anoExercicio do empenho
#   c) Montar chave_licitacao e agrupar por ela
#   d) Fallback: para empenhos sem licitacao, vincular via credor (CNPJ) -> contratos
# -----------------------------------------------------------------------------

print("\n" + "="*60)
print("ETAPA 5 - EXECUCAO DETALHADA DE DESPESAS")
print("="*60)

# Carregar despesas de todos os anos configurados
_frames_desp_todos = []
for _label_d, _pasta_d in FONTES_DESPESAS_LISTA:
    _df_d = ler_csvs(_pasta_d, "df_27_unificado", _label_d)
    if _df_d.empty:
        continue

    # Normalizar valores monetarios por pasta (antes de concat para evitar conflito de tipos)
    for col in ["valorEmpenho", "valorLiquidadoEmpenho", "valorPagoEmpenho",
                "valorEmpenhado", "saldoAPagar", "saldoALiquidar"]:
        if col in _df_d.columns:
            _df_d[col] = normalizar_moeda(_df_d[col])

    # FIX #5 (v8): Resolver chave_licitacao via tabela de referencia df_licitacao_unificado
    # A coluna 'licitacao' em df_27 contem nomes de arquivo (ex: licitacao_cf3d7cf0.csv).
    _df_d["chave_licitacao"] = None
    if "licitacao" in _df_d.columns:
        _df_lic_ref = ler_csvs(_pasta_d, "df_licitacao_unificado", _label_d + "_licref")
        if (not _df_lic_ref.empty
                and "numeroLicitacao" in _df_lic_ref.columns
                and "origem_arquivo" in _df_lic_ref.columns):
            _lic_parts = _df_lic_ref["numeroLicitacao"].str.strip().str.split("/", n=1, expand=True)
            _df_lic_ref["_num_lic"] = _lic_parts[0].apply(limpar_chave)
            _df_lic_ref["_ano_lic"] = (_lic_parts[1].apply(limpar_chave)
                                       if _lic_parts.shape[1] > 1 else "")
            _df_lic_ref["_chave_ref"] = (_df_lic_ref["_num_lic"] + "_"
                                         + _df_lic_ref["_ano_lic"])
            _df_lic_ref["_chave_ref"] = _df_lic_ref["_chave_ref"].replace(
                {"_": None, "": None})

            _lookup_lic = (_df_lic_ref[["origem_arquivo", "_chave_ref"]]
                           .drop_duplicates(subset=["origem_arquivo"])
                           .rename(columns={"origem_arquivo": "_lic_fname"}))
            _df_d = _df_d.merge(_lookup_lic, left_on="licitacao",
                                right_on="_lic_fname", how="left")
            _df_d["chave_licitacao"] = _df_d["_chave_ref"]
            _df_d = _df_d.drop(columns=["_lic_fname", "_chave_ref"], errors="ignore")
            _v = _df_d["chave_licitacao"].notna().sum()
            print(f"  [{_label_d}] Empenhos vinculados via tabela licitacao: "
                  f"{_v:,} de {len(_df_d):,} ({_v/len(_df_d)*100:.1f}%)")

    # Guardar pasta de origem para resolucao CNPJ do credor (etapa posterior)
    _df_d["_pasta_despesas"] = _pasta_d
    _frames_desp_todos.append(_df_d)

df_desp = (pd.concat(_frames_desp_todos, ignore_index=True)
           if _frames_desp_todos else pd.DataFrame())

if df_desp.empty:
    print("  [AVISO] df_despesas vazio - camada de despesas ignorada.")
else:
    # FIX #5b (v8): fallback via CNPJ do credor resolvido por pasta (df_credor_unificado)
    # A coluna 'credor' em df_27 contem nomes de arquivo (ex: credor_56792299.csv),
    # nao CNPJs diretos. Resolvemos por pasta para manter a correspondencia correta.
    sem_chave = df_desp["chave_licitacao"].isna().sum()
    print(f"  Empenhos sem chave_licitacao apos vinculacao direta: {sem_chave:,}")

    if sem_chave > 0 and not df_contratos.empty and "chave_licitacao" in df_contratos.columns:
        # Carregar tabelas de referencia de credor de todos os anos
        # (UUIDs nos nomes de arquivo sao unicos entre anos, sem colisao)
        _frames_cred_ref = []
        for _label_d, _pasta_d in FONTES_DESPESAS_LISTA:
            _dcr = ler_csvs(_pasta_d, "df_credor_unificado", _label_d + "_credref")
            if not _dcr.empty:
                _frames_cred_ref.append(_dcr)
        df_cred_ref = (pd.concat(_frames_cred_ref, ignore_index=True)
                       if _frames_cred_ref else pd.DataFrame())
        if not df_cred_ref.empty and "cnpjCpfCredor" in df_cred_ref.columns and "origem_arquivo" in df_cred_ref.columns:
            lookup_cred = (df_cred_ref[["origem_arquivo", "cnpjCpfCredor"]]
                           .drop_duplicates(subset=["origem_arquivo"])
                           .rename(columns={"origem_arquivo": "_cred_fname"}))
            lookup_cred["cnpjCpfCredor"] = lookup_cred["cnpjCpfCredor"].apply(limpar_chave)

            df_desp = df_desp.merge(lookup_cred, left_on="credor", right_on="_cred_fname", how="left")
            df_desp = df_desp.drop(columns=["_cred_fname"], errors="ignore")
            col_credor_resolved = "cnpjCpfCredor"
            print(f"  CNPJ credor resolvido para {df_desp['cnpjCpfCredor'].notna().sum():,} empenhos")
        else:
            # Sem tabela de referencia, tentar coluna direta (dados sem filename ref)
            col_credor_resolved = next(
                (c for c in ["cnpjCpfCredor", "cnpjCpf"] if c in df_desp.columns), None
            )

        if col_credor_resolved and col_credor_resolved in df_desp.columns:
            df_desp["_cnpj_credor"] = df_desp[col_credor_resolved].apply(limpar_chave)
            # Filtrar apenas CNPJs validos (nao mascarados, formato XX.XXX.XXX/XXXX-XX ou similar)
            mask_cnpj_valido = df_desp["_cnpj_credor"].str.len().between(11, 20)
            mapa_cnpj_desp = (df_contratos[["cnpjCpfContratado", "chave_licitacao"]]
                              .dropna()
                              .drop_duplicates(subset=["cnpjCpfContratado"], keep="first"))

            mask_sem = df_desp["chave_licitacao"].isna() & mask_cnpj_valido
            if mask_sem.any():
                df_fallback = df_desp[mask_sem][["_cnpj_credor"]].merge(
                    mapa_cnpj_desp, left_on="_cnpj_credor", right_on="cnpjCpfContratado", how="left"
                )
                df_desp.loc[mask_sem, "chave_licitacao"] = df_fallback["chave_licitacao"].values

            vinc_fallback = df_desp["chave_licitacao"].notna().sum()
            print(f"  Empenhos vinculados apos fallback CNPJ: {vinc_fallback:,} de {len(df_desp):,} "
                  f"({vinc_fallback/len(df_desp)*100:.1f}%)")
        else:
            print("  [AVISO] CNPJ do credor nao resolvido - fallback ignorado.")

    diagnostico_merge(
        "despesas -> processos",
        set(df_desp["chave_licitacao"].dropna()) - {""},
        set(df_processos["chave_licitacao"].dropna()) - {""}
    )

    # Agregar por chave_licitacao
    agg_dict = {"qtd_empenhos": pd.NamedAgg("chave_licitacao", "count")}
    for col, alias in [("valorEmpenho",          "soma_valorEmpenho"),
                       ("valorLiquidadoEmpenho", "soma_valorLiquidadoEmpenho"),
                       ("valorPagoEmpenho",      "soma_valorPagoEmpenho")]:
        if col in df_desp.columns:
            agg_dict[alias] = pd.NamedAgg(col, "sum")

    df_desp_valid = df_desp[df_desp["chave_licitacao"].notna()
                            & (df_desp["chave_licitacao"] != "")]

    agg_desp = df_desp_valid.groupby("chave_licitacao").agg(**agg_dict).reset_index()

    # Moda de descritivos categoricos
    for col_orig, col_dest in [("descricaoOrgao",    "orgao_principal"),
                               ("descricaoPrograma", "programa_principal"),
                               ("descricaoFuncao",   "funcao_principal"),
                               ("descricaoUnidade",  "unidade_principal")]:
        if col_orig in df_desp_valid.columns:
            moda_s = (df_desp_valid.groupby("chave_licitacao")[col_orig]
                      .agg(lambda x: x.dropna().mode().iloc[0]
                           if len(x.dropna().mode()) > 0 else None)
                      .reset_index().rename(columns={col_orig: col_dest}))
            agg_desp = agg_desp.merge(moda_s, on="chave_licitacao", how="left")

    df_processos = df_processos.merge(agg_desp, on="chave_licitacao", how="left")
    preenchidos_desp = df_processos["soma_valorEmpenho"].notna().sum()
    print(f"  OK Despesas agregadas: {len(agg_desp):,} licitacoes com empenhos | "
          f"Vinculadas a df_processos: {preenchidos_desp:,} de {len(df_processos):,} "
          f"({preenchidos_desp/len(df_processos)*100:.1f}%)")


# -----------------------------------------------------------------------------
# ETAPA 6 - FORNECEDORES SANCIONADOS
# -----------------------------------------------------------------------------

print("\n" + "="*60)
print("ETAPA 6 - FORNECEDORES SANCIONADOS")
print("="*60)

df_sanc = pd.DataFrame()
if PASTA_SANCIONADOS and os.path.isdir(PASTA_SANCIONADOS):
    df_sanc = ler_csvs(PASTA_SANCIONADOS, "df_27_unificado", "sancionados")

df_processos["contratado_sancionado"] = 0

if df_sanc.empty:
    print("  [AVISO] Base de sancionados vazia.")
elif not df_contratos.empty and "cnpjCpfContratado" in df_contratos.columns:
    col_cnpj_sanc = next(
        (c for c in ["cnpjCpf", "cnpj", "cpfCnpj"] if c in df_sanc.columns), None
    )
    if col_cnpj_sanc:
        sancionados_set = set(df_sanc[col_cnpj_sanc].dropna().apply(limpar_chave))
        df_contratos["contratado_sancionado"] = (
            df_contratos["cnpjCpfContratado"].isin(sancionados_set).astype(int)
        )
        if "chave_licitacao" in df_contratos.columns:
            flag_sanc = (df_contratos.groupby("chave_licitacao")["contratado_sancionado"]
                         .max().reset_index())
            df_processos = df_processos.drop(columns=["contratado_sancionado"], errors="ignore")
            df_processos = df_processos.merge(flag_sanc, on="chave_licitacao", how="left")
            df_processos["contratado_sancionado"] = (df_processos["contratado_sancionado"]
                                                      .fillna(0).astype(int))
            print(f"  OK Licitacoes com contratado sancionado: "
                  f"{df_processos['contratado_sancionado'].sum():,}")


# -----------------------------------------------------------------------------
# ETAPA 7 - PREPARACAO DOS ITENS VENCEDORES
#
# FIX #2: usar coluna 'numero' do df_venc (= numeroLicitacao do item)
# para criar chave_licitacao diretamente, sem depender do mapa CNPJ -> contrato.
# O mapa CNPJ continua como fallback para os ~1.3% de itens sem 'numero'.
# -----------------------------------------------------------------------------

print("\n" + "="*60)
print("ETAPA 7 - PREPARACAO DOS ITENS VENCEDORES")
print("="*60)

if df_venc.empty:
    print("  [AVISO] df_itensvencedores vazio.")
else:
    print(f"  Colunas df_venc: {df_venc.columns.tolist()}")

    for col in ["valorTotalReferencia", "valorTotalVencedor",
                "valorUnitarioReferencia", "valorUnitarioVencedor"]:
        if col in df_venc.columns:
            df_venc[col] = normalizar_moeda(df_venc[col])

    # FIX #2a: chave direta via coluna 'numero' (numeroLicitacao do item)
    if "numero" in df_venc.columns:
        # Inferir ano a partir do campo _fonte (ex: 'licit_2020' -> '2020').
        # FIX #9: antes estava fixo em '_2019', corrompendo todos os itens de 2020.
        _num_venc = df_venc["numero"].apply(limpar_chave)
        if "_fonte" in df_venc.columns:
            _ano_venc = df_venc["_fonte"].str.extract(r"(\d{4})$")[0].fillna("2019")
        else:
            _ano_venc = "2019"
        df_venc["chave_licitacao"] = _num_venc + "_" + _ano_venc
        # Limpar chaves onde numero estava vazio (resultado seria "_YYYY")
        df_venc["chave_licitacao"] = df_venc["chave_licitacao"].where(
            _num_venc.ne("") & _num_venc.notna(), other=None
        )
        df_venc["chave_licitacao"] = df_venc["chave_licitacao"].replace({"": None})

        direto = df_venc["chave_licitacao"].notna().sum()
        print(f"  Itens com chave_licitacao direta (via 'numero'): "
              f"{direto:,} de {len(df_venc):,} ({direto/len(df_venc)*100:.1f}%)")
    else:
        df_venc["chave_licitacao"] = None
        print("  [AVISO] Coluna 'numero' nao encontrada em df_venc.")

    # FIX #2b: fallback via CNPJ para itens sem chave
    col_cnpj_venc = next(
        (c for c in ["cnpjCpfVencedor", "cnpjCpf", "cnpj"] if c in df_venc.columns), None
    )
    sem_chave_venc = df_venc["chave_licitacao"].isna().sum()

    if sem_chave_venc > 0 and col_cnpj_venc and not df_contratos.empty:
        df_venc[col_cnpj_venc] = df_venc[col_cnpj_venc].apply(limpar_chave)

        # BUG #8: mapa deduplicado por CNPJ (keep="first") evita explosao cartesiana
        mapa_venc = (df_contratos[["cnpjCpfContratado", "chave_licitacao"]]
                     .dropna()
                     .drop_duplicates(subset=["cnpjCpfContratado"], keep="first"))

        mask_sem = df_venc["chave_licitacao"].isna()
        df_fb = df_venc[mask_sem][[col_cnpj_venc]].merge(
            mapa_venc, left_on=col_cnpj_venc, right_on="cnpjCpfContratado", how="left"
        )
        df_venc.loc[mask_sem, "chave_licitacao"] = df_fb["chave_licitacao"].values
        print(f"  Itens vinculados apos fallback CNPJ: "
              f"{df_venc['chave_licitacao'].notna().sum():,} de {len(df_venc):,}")

    # FIX #9b: Deduplicar itens vencedores antes do merge.
    # Alguns itens aparecem em multiplos arquivos UUID do portal com valores ligeiramente
    # diferentes. O concat coloca 'finalizado' depois de 'licit', entao keep='last'
    # privilegia as entradas de Processos Finalizados (resultado mais definitivo).
    _key_venc_dedup = [c for c in ["chave_licitacao", "codigo", "cnpjCpfVencedor", "numero"]
                       if c in df_venc.columns]
    if _key_venc_dedup:
        _antes_vd = len(df_venc)
        df_venc = df_venc.drop_duplicates(subset=_key_venc_dedup, keep="last")
        print(f"  Duplicatas removidas de df_venc: {_antes_vd - len(df_venc):,} | "
              f"Restaram: {len(df_venc):,}")

    diagnostico_merge(
        "itensvencedores -> processos",
        set(df_venc["chave_licitacao"].dropna()) - {""},
        set(df_processos["chave_licitacao"].dropna()) - {""}
    )

    # Economia por item
    df_venc["economia_item"] = (df_venc["valorTotalReferencia"]
                                - df_venc["valorTotalVencedor"])
    df_venc["economia_item_pct"] = np.where(
        df_venc["valorTotalReferencia"] > 0,
        (df_venc["economia_item"] / df_venc["valorTotalReferencia"]) * 100,
        np.nan
    )
    df_venc["ratio_vencedor_referencia"] = np.where(
        df_venc["valorTotalReferencia"] > 0,
        df_venc["valorTotalVencedor"] / df_venc["valorTotalReferencia"],
        np.nan
    )

    # VAR #6: amplitude_desconto_item e media_desconto_item
    # Agrega economia_item_pct ao nivel da licitacao e junta em df_processos.
    # FIX #10: alguns itens do portal registram valorTotalReferencia = 1,00 como
    # placeholder (ex.: contratos de uso de espacos culturais), gerando
    # economia_item_pct na casa de -679.000%. Esses outliers distorcem
    # amplitude_desconto_item para milhoes de pontos percentuais.
    # Solucao: clipar economia_item_pct em [-100, 100] antes de agregar,
    # preservando descontos validos e descartando artefatos de dados.
    if "chave_licitacao" in df_venc.columns and "economia_item_pct" in df_venc.columns:
        _venc_desc = df_venc.dropna(subset=["economia_item_pct", "chave_licitacao"]).copy()
        _venc_desc["economia_item_pct"] = _venc_desc["economia_item_pct"].clip(-100, 100)
        if not _venc_desc.empty:
            agg_desc = (_venc_desc
                        .groupby("chave_licitacao")
                        .agg(
                            media_desconto_item     = ("economia_item_pct", "mean"),
                            amplitude_desconto_item = ("economia_item_pct",
                                                       lambda x: x.max() - x.min()),
                        )
                        .reset_index())
            df_processos = df_processos.merge(agg_desc, on="chave_licitacao", how="left")
            print(f"  media_desconto_item calculada: "
                  f"{df_processos['media_desconto_item'].notna().sum():,} licitacoes")
            print(f"  amplitude_desconto_item calculada: "
                  f"{df_processos['amplitude_desconto_item'].notna().sum():,} licitacoes")


# -----------------------------------------------------------------------------
# ETAPA 8 - MONTAGEM DA BASE FINAL
# -----------------------------------------------------------------------------

print("\n" + "="*60)
print("ETAPA 8 - MONTAGEM DA BASE FINAL")
print("="*60)

colunas_processos = [c for c in [
    "chave_licitacao",
    "modalidade", "tipoObjeto", "formaJulgamento", "objeto",
    "valorEstimado", "valorHomologado",
    "economia_absoluta", "economia_pct",
    "qtd_participantes", "houve_disputa",
    "qtd_contratos", "media_valorInicial", "media_valorFinal", "media_dias_vigencia",
    "soma_valorEmpenho", "soma_valorLiquidadoEmpenho", "soma_valorPagoEmpenho",
    "qtd_empenhos", "orgao_principal", "programa_principal",
    "funcao_principal", "unidade_principal",
    "contratado_sancionado",
    # Variaveis adicionadas (v10)
    "dias_tramitacao", "log_dias_tramitacao",
    "media_variacao_contr",
    "interact_part_logval",
    "formaJulgamento_cod",
    "media_desconto_item", "amplitude_desconto_item",
] if c in df_processos.columns]

if df_venc.empty or "chave_licitacao" not in df_venc.columns:
    print("  [AVISO] df_venc sem chave_licitacao. Usando df_processos como base final.")
    base_final = df_processos.copy()
else:
    base_final = df_venc.merge(
        df_processos[colunas_processos], on="chave_licitacao", how="left"
    )

    antes_f = len(base_final)
    # FIX #6: excluir tambem 'origem_arquivo' (coluna do script.py) da deduplicacao,
    # pois Processos Licitatorios e Processos Licitatorios Finalizados sao o mesmo
    # dado baixado de duas secoes diferentes do portal — diferem so no nome do arquivo.
    cols_id = [c for c in base_final.columns
               if c not in ["_fonte", "_arquivo_origem", "origem_arquivo"]]
    base_final = base_final.drop_duplicates(subset=cols_id)
    if antes_f - len(base_final) > 0:
        print(f"  Duplicatas residuais removidas: {antes_f - len(base_final):,}")

    if "valorEstimado" in base_final.columns:
        vinc  = base_final["valorEstimado"].notna().sum()
        total = len(base_final)
        print(f"  Itens com dados da licitacao pai: {vinc:,} de {total:,} ({vinc/total*100:.1f}%)")

# -----------------------------------------------------------------------------
# FILTRO DE CONSISTENCIA PARA CALCULO DO ALVO
# -----------------------------------------------------------------------------
# Mantem apenas itens onde as tres colunas criticas para o calculo do alvo
# estao preenchidas. Isso alinha ratio_vencedor_referencia (nivel item),
# valorEstimado e valorHomologado (nivel licitacao), garantindo que cada
# linha contribua de forma consistente para a analise de razao_pago_homolog.
COLUNAS_CONSISTENCIA = [
    "ratio_vencedor_referencia",
    "valorEstimado",
    "valorHomologado",
]
cols_ok = [c for c in COLUNAS_CONSISTENCIA if c in base_final.columns]
if len(cols_ok) == len(COLUNAS_CONSISTENCIA):
    antes = len(base_final)
    base_final = base_final.dropna(subset=cols_ok).reset_index(drop=True)
    removidas = antes - len(base_final)
    print(f"\n  Filtro de consistencia ({', '.join(cols_ok)}):")
    print(f"    Removidas: {removidas:,} linhas com nulos em alguma das 3 colunas")
    print(f"    Restantes: {len(base_final):,} linhas")
else:
    faltam = [c for c in COLUNAS_CONSISTENCIA if c not in base_final.columns]
    print(f"  [AVISO] Filtro de consistencia pulado: colunas ausentes {faltam}")

print(f"\n  Base final: {len(base_final):,} linhas | {base_final.shape[1]} colunas")
if len(base_final) < 20_000:
    print(f"  ATENCAO: abaixo da meta de 20.000 linhas (adicione mais anos).")
else:
    print(f"  OK Meta de 20.000 linhas atingida!")


# -----------------------------------------------------------------------------
# ETAPA 9 - EXPORTACAO
# -----------------------------------------------------------------------------

print("\n" + "="*60)
print("ETAPA 9 - EXPORTACAO")
print("="*60)

# FIX #5 / FIX #11: arredondar todas as colunas float antes de exportar.
#   - Colunas monetarias e percentuais: 2 casas decimais
#   - Demais floats (logs, indices, flags): 6 casas decimais
# Isso evita que Python grave 16 digitos significativos (ex.: 2.9444389791664403),
# que o Excel em locale pt-BR interpreta como inteiro gigante ao tratar '.' como
# separador de milhar.
# O separador decimal e ',' (padrao BR) para compatibilidade nativa com Excel.
KEYWORDS_2 = ["valor", "economia", "media", "soma", "ratio", "desconto",
              "variacao", "pago", "liquidado", "empenho"]
for c in base_final.columns:
    if not pd.api.types.is_float_dtype(base_final[c]):
        continue
    if any(kw in c.lower() for kw in KEYWORDS_2):
        base_final[c] = base_final[c].round(2)
    else:
        base_final[c] = base_final[c].round(6)

base_final.to_csv(
    ARQUIVO_SAIDA,
    index=False,
    sep=";",
    decimal=",",
    encoding="utf-8-sig"
)
print(f"\n  OK Arquivo salvo: {os.path.abspath(ARQUIVO_SAIDA)}")
print(f"  Total de registros: {len(base_final):,}")
print(f"  Total de colunas  : {base_final.shape[1]}")


# -----------------------------------------------------------------------------
# ETAPA 10 - RESUMO ESTATISTICO E CHECAGEM DE INTEGRIDADE
# -----------------------------------------------------------------------------

print("\n" + "="*60)
print("RESUMO ESTATISTICO - VARIAVEIS PRINCIPAIS")
print("="*60)

cols_resumo = [c for c in [
    "qtd_participantes", "houve_disputa",
    "economia_pct", "economia_absoluta",
    "valorEstimado", "valorHomologado",
    "economia_item_pct", "economia_item",
    "ratio_vencedor_referencia",
    "media_dias_vigencia", "qtd_contratos",
    "soma_valorEmpenho", "soma_valorLiquidadoEmpenho", "soma_valorPagoEmpenho",
    "qtd_empenhos", "contratado_sancionado",
    "dias_tramitacao", "log_dias_tramitacao",
    "media_variacao_contr", "interact_part_logval",
    "formaJulgamento_cod", "media_desconto_item", "amplitude_desconto_item",
] if c in base_final.columns]

if cols_resumo:
    print(base_final[cols_resumo].describe().round(2).to_string())

print("\n" + "="*60)
print("CHECAGEM DE INTEGRIDADE")
print("="*60)

for col in cols_resumo:
    nulos = base_final[col].isna().sum()
    pct   = nulos / len(base_final) * 100 if len(base_final) > 0 else 0
    status = "OK" if pct < 10 else ("AVISO" if pct < 50 else "CRITICO")
    print(f"  [{status}] {col}: {nulos:,} nulos ({pct:.1f}%)")

print("\nProcesso concluido!")