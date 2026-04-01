"""
=============================================================================
UNIFICAÇÃO DE BASES - PORTAL DA TRANSPARÊNCIA CRICIÚMA
=============================================================================
Pergunta problema:
  "Qual o impacto do número de participantes nas licitações sobre a
   economia gerada para o município de Criciúma?"

=============================================================================
MODELO DE DADOS — ESQUEMA DE JUNÇÃO CORRETO (v4)
=============================================================================

  Os arquivos NÃO compartilham uma chave direta comum. A ligação correta é:

  ┌─────────────────────────────────────────────────────────────────────┐
  │  df_27_processos  (Processos Licitatórios + Finalizados)           │
  │  Chave: numeroLicitacao + anoLicitacao                              │
  │  Colunas úteis: valorEstimado, valorHomologado, modalidade, etc.   │
  └──────────────────────────┬──────────────────────────────────────────┘
                             │ JOIN em numeroLicitacao + anoLicitacao
  ┌──────────────────────────▼──────────────────────────────────────────┐
  │  df_contratos  (Relação de Contratos) ← TABELA PONTE CENTRAL       │
  │  Chave entrada : numeroLicitacao + anoLicitacao                     │
  │  Chave saída   : cnpjCpfContratado                                  │
  │  Colunas úteis : valorInicial, valorFinal, diasVigencia, etc.      │
  └──────┬───────────────────────────────────────┬───────────────────────┘
         │ JOIN em cnpjCpfContratado             │ JOIN em cnpjCpfContratado
  ┌──────▼──────────────────┐     ┌─────────────▼───────────────────────┐
  │ df_itensvencedores      │     │ df_participantes                    │
  │ [cnpjCpfVencedor]       │     │ [cnpjCpfFornecedor]                 │
  │ valorTotalReferencia    │     │ formaParticipacao                   │
  │ valorTotalVencedor      │     │ nomeFonecedor                       │
  └─────────────────────────┘     └─────────────────────────────────────┘

  Fluxo de construção da base final (MODO item_vencedor):
  1. df_itensvencedores  →  join com df_contratos via cnpjCpfVencedor
                                                    = cnpjCpfContratado
  2. resultado           →  join com df_27_processos via numeroLicitacao
                                                         + anoLicitacao
  3. resultado           →  agrega qtd_participantes por licitação
                            (df_participantes join df_contratos mesmo caminho)

=============================================================================
CORREÇÕES ACUMULADAS (v1 → v4)
=============================================================================
  [BUG #1] Normalização de moeda: valores EN (ponto decimal) tratados como
           BR (vírgula decimal) → valores x100.
           → pd.to_numeric() direto, sem remoção de ponto.

  [BUG #2] limpar_chave aplicado só no df_27, não nos demais dataframes.
           → aplicado em todos antes de criar qualquer chave de junção.

  [BUG #3] df_part concatenado sem deduplicar → participantes contados 2x.
           → drop_duplicates por chave + id do participante.

  [BUG #4] df_27 com duplicatas ao vir de duas pastas.
           → drop_duplicates com keep="last" mantido.

  [BUG #5] sep=";" fixo para todos os arquivos; alguns usam ",".
           → detectar_separador() por arquivo.

  [BUG #6 — NOVO] Chave de junção inexistente em df_participantes e
           df_itensvencedores: esses arquivos NÃO têm numeroLicitacao.
           A ligação correta é via df_contratos (tabela ponte):
             itensvencedores.cnpjCpfVencedor
               = contratos.cnpjCpfContratado → contratos.numeroLicitacao
               = processos.numeroLicitacao
           e o mesmo caminho para participantes (cnpjCpfFornecedor).

=============================================================================
CONFIGURE AQUI ANTES DE RODAR
=============================================================================
"""

# ── Caminhos para as pastas raiz de cada base ────────────────────────────────
PASTA_PROCESSOS_LICITATORIOS = r'C:\Users\gusta\Documents\Git Hub\analiseEstatísticaPrefeituraCriciuma\dadosUnificados\Processos Licitatórios-2019'
PASTA_PROCESSOS_FINALIZADOS  = r'C:\Users\gusta\Documents\Git Hub\analiseEstatísticaPrefeituraCriciuma\dadosUnificados\Processos Licitatórios Finalizados-2019'
PASTA_CONTRATOS              = r'C:\Users\gusta\Documents\Git Hub\analiseEstatísticaPrefeituraCriciuma\dadosUnificados\Relação de Contratos-2019'

# ── Modo de análise ───────────────────────────────────────────────────────────
MODO = "item_vencedor"   # "licitacao" ou "item_vencedor"

# ── Arquivo de saída ──────────────────────────────────────────────────────────
ARQUIVO_SAIDA = "base_unificada_criciuma_v4.csv"

# ── Encoding padrão ───────────────────────────────────────────────────────────
ENCODING = "utf-8"

# =============================================================================
# NÃO É NECESSÁRIO ALTERAR ABAIXO DESTA LINHA
# =============================================================================

import os, glob, warnings
import pandas as pd
import numpy as np

warnings.filterwarnings("ignore")


# ─────────────────────────────────────────────────────────────────────────────
# FUNÇÕES AUXILIARES
# ─────────────────────────────────────────────────────────────────────────────

def limpar_chave(txt):
    """Garante string inteira sem '.0' e sem espaços. Ex: 10.0 → '10'."""
    if pd.isna(txt):
        return ""
    return str(txt).split('.')[0].strip()


def detectar_separador(filepath, encoding='utf-8'):
    """Detecta o separador real do CSV lendo as primeiras duas linhas."""
    for enc in [encoding, 'utf-8-sig', 'latin-1', 'cp1252']:
        try:
            with open(filepath, 'r', encoding=enc) as f:
                linha1 = f.readline()
                linha2 = f.readline()
            candidatos = {';': linha1.count(';'),
                          ',': linha1.count(','),
                          '\t': linha1.count('\t')}
            melhor_sep, melhor_score = ';', -1
            for sep, contagem in candidatos.items():
                if contagem == 0:
                    continue
                cols1 = len(linha1.split(sep))
                cols2 = len(linha2.split(sep)) if linha2.strip() else cols1
                consistente = 1 if abs(cols1 - cols2) <= 2 else 0
                score = contagem * consistente
                if score > melhor_score:
                    melhor_score, melhor_sep = score, sep
            return melhor_sep, enc
        except (UnicodeDecodeError, PermissionError):
            continue
    return ';', 'latin-1'


def encontrar_csvs(pasta_raiz, nome_arquivo):
    """Procura recursivamente CSVs cujo nome contenha `nome_arquivo`."""
    padrao = os.path.join(pasta_raiz, "**", f"*{nome_arquivo}*.csv")
    arquivos = glob.glob(padrao, recursive=True)
    if not arquivos:
        padrao2 = os.path.join(pasta_raiz, "**", f"*{nome_arquivo}*")
        arquivos = [f for f in glob.glob(padrao2, recursive=True)
                    if os.path.isfile(f) and not f.endswith(".xlsx")]
    return sorted(arquivos)


def ler_csvs(pasta_raiz, nome_arquivo, label=""):
    """Lê e concatena CSVs com detecção automática de separador por arquivo."""
    arquivos = encontrar_csvs(pasta_raiz, nome_arquivo)
    if not arquivos:
        print(f"  [AVISO] '{nome_arquivo}' não encontrado em: {pasta_raiz}")
        return pd.DataFrame()

    frames, seps = [], set()
    for arq in arquivos:
        sep, enc = detectar_separador(arq, encoding=ENCODING)
        seps.add(sep)
        try:
            df = pd.read_csv(arq, sep=sep, encoding=enc,
                             low_memory=False, on_bad_lines="skip")
            df["_fonte"]          = label
            df["_arquivo_origem"] = os.path.basename(arq)
            frames.append(df)
        except Exception as e:
            print(f"  [ERRO] {os.path.basename(arq)}: {e}")

    if not frames:
        return pd.DataFrame()

    resultado = pd.concat(frames, ignore_index=True)
    seps_str = ', '.join(f"'{s}'" for s in seps)
    print(f"  ✔ '{nome_arquivo}' ({label}): {len(resultado):,} linhas | "
          f"{resultado.shape[1]} colunas | sep: {seps_str}")
    return resultado


def normalizar_moeda(serie):
    """
    Converte coluna de valores monetários para float.
    Tenta formato EN (ponto = decimal) primeiro.
    Usa formato BR (vírgula = decimal) como fallback se <50% converter.
    """
    s = serie.astype(str).str.strip().replace('', None)
    resultado = pd.to_numeric(s, errors='coerce')
    if len(resultado) > 0 and resultado.notna().mean() < 0.5:
        print("  [INFO] Usando fallback BR (vírgula decimal)...")
        s_br = (serie.astype(str).str.strip()
                .str.replace(r'[^\d,\.-]', '', regex=True)
                .str.replace('.', '', regex=False)
                .str.replace(',', '.', regex=False)
                .replace('', None))
        resultado = pd.to_numeric(s_br, errors='coerce')
    return resultado


def preparar_chave(df, cols_candidatas):
    """
    Aplica limpar_chave nas colunas presentes e devolve o df com a coluna
    'chave_licitacao' criada. Tenta os pares na ordem fornecida.
    cols_candidatas: lista de tuplas (col_numero, col_ano)
    Retorna (df, True/False indicando se a chave foi criada com sucesso).
    """
    for col_num, col_ano in cols_candidatas:
        if col_num in df.columns and col_ano in df.columns:
            df[col_num] = df[col_num].apply(limpar_chave)
            df[col_ano] = df[col_ano].apply(limpar_chave)
            df["chave_licitacao"] = df[col_num] + "_" + df[col_ano]
            return df, True
    return df, False


def diagnostico_merge(nome, chaves_esq, chaves_dir):
    """Imprime quantas chaves casam entre dois conjuntos."""
    intersecao = chaves_esq & chaves_dir
    print(f"  Diagnóstico '{nome}':")
    print(f"    Esquerda : {len(chaves_esq):,} chaves únicas")
    print(f"    Direita  : {len(chaves_dir):,} chaves únicas")
    print(f"    Casam    : {len(intersecao):,} ({len(intersecao)/max(len(chaves_esq),1)*100:.1f}% da esq.)")
    if len(intersecao) == 0:
        print(f"    [ERRO CRÍTICO] Nenhuma chave casou!")
        print(f"    Exemplos esq: {list(chaves_esq)[:5]}")
        print(f"    Exemplos dir: {list(chaves_dir)[:5]}")


# ─────────────────────────────────────────────────────────────────────────────
# ETAPA 1 – LEITURA DAS BASES
# ─────────────────────────────────────────────────────────────────────────────

print("\n" + "="*60)
print("ETAPA 1 – LEITURA DAS BASES")
print("="*60)

# ── 1A. df_27 de processos (duas pastas) ─────────────────────────────────────
frames_proc = []
for label, pasta in [("licit", PASTA_PROCESSOS_LICITATORIOS),
                      ("finalizado", PASTA_PROCESSOS_FINALIZADOS)]:
    if pasta and os.path.isdir(pasta):
        df = ler_csvs(pasta, "df_27_unificado", label)
        if not df.empty:
            frames_proc.append(df)
    else:
        print(f"  [AVISO] Pasta não encontrada: {pasta}")

df_processos = pd.concat(frames_proc, ignore_index=True) if frames_proc else pd.DataFrame()
print(f"  → df_processos bruto: {len(df_processos):,} linhas")

# ── 1B. df_contratos ──────────────────────────────────────────────────────────
df_contratos = pd.DataFrame()
if PASTA_CONTRATOS and os.path.isdir(PASTA_CONTRATOS):
    df_contratos = ler_csvs(PASTA_CONTRATOS, "df_27_unificado", "contrato")
else:
    print(f"  [AVISO] Pasta de contratos não encontrada: {PASTA_CONTRATOS}")

# ── 1C. df_participantes ─────────────────────────────────────────────────────
frames_part = []
for label, pasta in [("licit", PASTA_PROCESSOS_LICITATORIOS),
                      ("finalizado", PASTA_PROCESSOS_FINALIZADOS)]:
    if pasta and os.path.isdir(pasta):
        df = ler_csvs(pasta, "df_participantes_unificado", label)
        if not df.empty:
            frames_part.append(df)

df_part = pd.concat(frames_part, ignore_index=True) if frames_part else pd.DataFrame()

# ── 1D. df_itensvencedores ───────────────────────────────────────────────────
frames_venc = []
for label, pasta in [("licit", PASTA_PROCESSOS_LICITATORIOS),
                      ("finalizado", PASTA_PROCESSOS_FINALIZADOS)]:
    if pasta and os.path.isdir(pasta):
        df = ler_csvs(pasta, "df_itensvencedores_unificado", label)
        if not df.empty:
            frames_venc.append(df)

df_venc = pd.concat(frames_venc, ignore_index=True) if frames_venc else pd.DataFrame()


# ─────────────────────────────────────────────────────────────────────────────
# ETAPA 2 – PREPARAÇÃO DO df_processos (tabela mestre)
# ─────────────────────────────────────────────────────────────────────────────

print("\n" + "="*60)
print("ETAPA 2 – PREPARAÇÃO DO df_processos")
print("="*60)

if df_processos.empty:
    raise RuntimeError("df_processos está vazio. Verifique os caminhos.")

# Normalização monetária (Bug #1)
for col in ["valorEstimado", "valorHomologado"]:
    if col in df_processos.columns:
        df_processos[col] = normalizar_moeda(df_processos[col])

# Criar chave_licitacao (tenta numeroLicitacao ou numeroProcesso)
df_processos, ok = preparar_chave(
    df_processos,
    [("numeroLicitacao", "anoLicitacao"), ("numeroProcesso", "anoProcesso")]
)
if not ok:
    raise RuntimeError(f"Chave não criada em df_processos. Colunas: {df_processos.columns.tolist()}")

# Deduplicar (Bug #4) — processos presentes nas duas pastas
antes = len(df_processos)
df_processos = df_processos.drop_duplicates(subset="chave_licitacao", keep="last")
print(f"  Duplicatas removidas de df_processos: {antes - len(df_processos):,} | "
      f"Restaram: {len(df_processos):,}")

# Calcular economia a nível de licitação
df_processos["economia_absoluta"] = (df_processos["valorEstimado"]
                                     - df_processos["valorHomologado"])
df_processos["economia_pct"] = np.where(
    df_processos["valorEstimado"] > 0,
    (df_processos["economia_absoluta"] / df_processos["valorEstimado"]) * 100,
    np.nan
)

print(f"  Chaves únicas em df_processos: {df_processos['chave_licitacao'].nunique():,}")
print(f"  Amostra valorEstimado: {df_processos['valorEstimado'].dropna().head(4).tolist()}")
print(f"  NaN valorEstimado: {df_processos['valorEstimado'].isna().sum()} | "
      f"NaN valorHomologado: {df_processos['valorHomologado'].isna().sum()}")


# ─────────────────────────────────────────────────────────────────────────────
# ETAPA 3 – PREPARAÇÃO DO df_contratos (tabela ponte)
# ─────────────────────────────────────────────────────────────────────────────

print("\n" + "="*60)
print("ETAPA 3 – PREPARAÇÃO DO df_contratos (tabela ponte)")
print("="*60)

if df_contratos.empty:
    print("  [AVISO] df_contratos vazio — etapa de enriquecimento via contratos ignorada.")
else:
    # Normalização monetária
    for col in ["valorInicial", "valorFinal", "valorAlterado"]:
        if col in df_contratos.columns:
            df_contratos[col] = normalizar_moeda(df_contratos[col])

    # Datas de vigência
    for col in ["dataVigenciaInicial", "dataVigenciaFinal"]:
        if col in df_contratos.columns:
            df_contratos[col] = pd.to_datetime(df_contratos[col],
                                               errors="coerce", dayfirst=True)
    if "dataVigenciaInicial" in df_contratos.columns and \
       "dataVigenciaFinal" in df_contratos.columns:
        df_contratos["dias_vigencia"] = (
            df_contratos["dataVigenciaFinal"] - df_contratos["dataVigenciaInicial"]
        ).dt.days

    # Criar chave_licitacao no df_contratos para ligar ao df_processos
    # df_contratos tem: numeroLicitacao + anoLicitacao (confirmado nas colunas)
    df_contratos, ok = preparar_chave(
        df_contratos,
        [("numeroLicitacao", "anoLicitacao"),
         ("numeroProcessoCompra", "anoProcessoCompra")]
    )
    if not ok:
        print(f"  [ERRO] Chave não criada em df_contratos. "
              f"Colunas: {df_contratos.columns.tolist()}")
    else:
        # Limpar cnpjCpfContratado para uso como chave secundária
        if "cnpjCpfContratado" in df_contratos.columns:
            df_contratos["cnpjCpfContratado"] = (df_contratos["cnpjCpfContratado"]
                                                  .apply(limpar_chave))

        # Verificar cobertura do join com df_processos
        diagnostico_merge(
            "contratos → processos",
            set(df_contratos["chave_licitacao"].dropna()),
            set(df_processos["chave_licitacao"].dropna())
        )

        # Agregar contratos por licitação para enriquecer df_processos
        agg_contr = (df_contratos.groupby("chave_licitacao")
                     .agg(
                         qtd_contratos        = ("chave_licitacao", "count"),
                         media_valorInicial   = ("valorInicial", "mean"),
                         media_valorFinal     = ("valorFinal", "mean"),
                         media_dias_vigencia  = ("dias_vigencia", "mean"),
                     )
                     .reset_index())

        df_processos = df_processos.merge(agg_contr, on="chave_licitacao", how="left")
        print(f"  ✔ Contratos agregados e vinculados a df_processos")


# ─────────────────────────────────────────────────────────────────────────────
# ETAPA 4 – CONTAGEM DE PARTICIPANTES
# ─────────────────────────────────────────────────────────────────────────────
#
# [BUG #6] df_participantes NÃO tem numeroLicitacao.
# Caminho correto:
#   df_part[cnpjCpfFornecedor] → df_contratos[cnpjCpfContratado]
#                                → df_contratos[chave_licitacao]
#   Depois agregar por chave_licitacao → qtd_participantes
#
# ─────────────────────────────────────────────────────────────────────────────

print("\n" + "="*60)
print("ETAPA 4 – CONTAGEM DE PARTICIPANTES")
print("="*60)

df_processos["qtd_participantes"] = 0
df_processos["houve_disputa"]     = 0

if df_part.empty:
    print("  [AVISO] df_participantes vazio.")
elif df_contratos.empty or "chave_licitacao" not in df_contratos.columns:
    print("  [AVISO] df_contratos sem chave_licitacao — não é possível vincular participantes.")
else:
    print(f"  Colunas df_part: {df_part.columns.tolist()}")

    # Limpar identificador do participante
    col_cnpj_part = None
    for cand in ["cnpjCpfFornecedor", "cnpjCpf", "cnpj", "cpf", "documento"]:
        if cand in df_part.columns:
            col_cnpj_part = cand
            break

    if col_cnpj_part is None:
        print(f"  [ERRO] Coluna de CNPJ/CPF não encontrada em df_part.")
    else:
        df_part[col_cnpj_part] = df_part[col_cnpj_part].apply(limpar_chave)

        # Bug #3: deduplicar participantes antes de contar
        antes_part = len(df_part)
        df_part = df_part.drop_duplicates(
            subset=[col_cnpj_part] + [c for c in ["_arquivo_origem"] if c in df_part.columns],
            keep="last"
        )
        print(f"  Duplicatas removidas de df_part: {antes_part - len(df_part):,}")

        # Tabela de mapeamento: cnpjCpfContratado → chave_licitacao (via contratos)
        mapa_cnpj_chave = (df_contratos[["cnpjCpfContratado", "chave_licitacao"]]
                           .dropna(subset=["cnpjCpfContratado", "chave_licitacao"])
                           .drop_duplicates())

        diagnostico_merge(
            "participantes (CNPJ) → contratos",
            set(df_part[col_cnpj_part].dropna()),
            set(mapa_cnpj_chave["cnpjCpfContratado"].dropna())
        )

        # Vincular participantes → chave_licitacao via CNPJ
        df_part_com_chave = df_part.merge(
            mapa_cnpj_chave,
            left_on=col_cnpj_part,
            right_on="cnpjCpfContratado",
            how="inner"
        )

        if df_part_com_chave.empty:
            print("  [AVISO] Nenhum participante vinculado via CNPJ/CPF.")
            print("  Verifique se cnpjCpfFornecedor em df_part bate com "
                  "cnpjCpfContratado em df_contratos.")
        else:
            # Contar participantes únicos por licitação
            agg_part = (df_part_com_chave
                        .drop_duplicates(subset=["chave_licitacao", col_cnpj_part])
                        .groupby("chave_licitacao")
                        .size()
                        .reset_index(name="qtd_participantes"))

            df_processos = df_processos.drop(columns=["qtd_participantes"], errors="ignore")
            df_processos = df_processos.merge(agg_part, on="chave_licitacao", how="left")
            df_processos["qtd_participantes"] = (df_processos["qtd_participantes"]
                                                  .fillna(0).astype(int))
            df_processos["houve_disputa"] = (df_processos["qtd_participantes"] > 1).astype(int)

            print(f"  ✔ Participantes vinculados: {len(df_part_com_chave):,} registros")
            print(f"  Distribuição qtd_participantes:")
            print(df_processos["qtd_participantes"]
                  .value_counts().sort_index().head(10).to_string())
            print(f"  Máx: {df_processos['qtd_participantes'].max()} | "
                  f"Média: {df_processos['qtd_participantes'].mean():.1f} | "
                  f"Zeros: {(df_processos['qtd_participantes'] == 0).sum()}")


# ─────────────────────────────────────────────────────────────────────────────
# ETAPA 5 – PREPARAÇÃO DOS ITENS VENCEDORES
# ─────────────────────────────────────────────────────────────────────────────
#
# [BUG #6] df_itensvencedores NÃO tem numeroLicitacao.
# Caminho correto:
#   df_venc[cnpjCpfVencedor] → df_contratos[cnpjCpfContratado]
#                             → df_contratos[chave_licitacao]
#
# ─────────────────────────────────────────────────────────────────────────────

print("\n" + "="*60)
print("ETAPA 5 – PREPARAÇÃO DOS ITENS VENCEDORES")
print("="*60)

if df_venc.empty:
    print("  [AVISO] df_itensvencedores vazio.")
elif df_contratos.empty or "chave_licitacao" not in df_contratos.columns:
    print("  [AVISO] df_contratos sem chave_licitacao — não é possível vincular itens.")
else:
    print(f"  Colunas df_venc: {df_venc.columns.tolist()}")

    # Normalização monetária (Bug #1)
    for col in ["valorTotalReferencia", "valorTotalVencedor",
                "valorUnitarioReferencia", "valorUnitarioVencedor"]:
        if col in df_venc.columns:
            df_venc[col] = normalizar_moeda(df_venc[col])

    # Limpar CNPJ/CPF do vencedor
    col_cnpj_venc = None
    for cand in ["cnpjCpfVencedor", "cnpjCpf", "cnpj"]:
        if cand in df_venc.columns:
            col_cnpj_venc = cand
            break

    if col_cnpj_venc is None:
        print(f"  [ERRO] Coluna de CNPJ/CPF não encontrada em df_venc.")
    else:
        df_venc[col_cnpj_venc] = df_venc[col_cnpj_venc].apply(limpar_chave)

        # Reutilizar o mesmo mapa CNPJ → chave_licitacao já construído na Etapa 4
        mapa_cnpj_chave = (df_contratos[["cnpjCpfContratado", "chave_licitacao"]]
                           .dropna(subset=["cnpjCpfContratado", "chave_licitacao"])
                           .drop_duplicates())

        diagnostico_merge(
            "itensvencedores (CNPJ) → contratos",
            set(df_venc[col_cnpj_venc].dropna()),
            set(mapa_cnpj_chave["cnpjCpfContratado"].dropna())
        )

        # Vincular itens → chave_licitacao via CNPJ
        df_venc = df_venc.merge(
            mapa_cnpj_chave,
            left_on=col_cnpj_venc,
            right_on="cnpjCpfContratado",
            how="left"
        )

        vinculados = df_venc["chave_licitacao"].notna().sum()
        print(f"  Itens vinculados via CNPJ: {vinculados:,} de {len(df_venc):,} "
              f"({vinculados/len(df_venc)*100:.1f}%)")

        # Calcular economia por item
        df_venc["economia_item"] = (df_venc["valorTotalReferencia"]
                                    - df_venc["valorTotalVencedor"])
        df_venc["economia_item_pct"] = np.where(
            df_venc["valorTotalReferencia"] > 0,
            (df_venc["economia_item"] / df_venc["valorTotalReferencia"]) * 100,
            np.nan
        )


# ─────────────────────────────────────────────────────────────────────────────
# ETAPA 6 – MONTAGEM DA BASE FINAL
# ─────────────────────────────────────────────────────────────────────────────

print("\n" + "="*60)
print(f"ETAPA 6 – MONTAGEM DA BASE FINAL (MODO: {MODO.upper()})")
print("="*60)

# Colunas do df_processos a trazer para a base final
colunas_processos = [c for c in [
    "chave_licitacao", "valorEstimado", "valorHomologado",
    "economia_absoluta", "economia_pct",
    "qtd_participantes", "houve_disputa",
    "modalidade", "tipoObjeto", "formaJulgamento",
    "qtd_contratos", "media_valorInicial", "media_valorFinal", "media_dias_vigencia"
] if c in df_processos.columns]

if MODO == "licitacao":
    base_final = df_processos.copy()
    print(f"  Base final (licitação): {len(base_final):,} linhas")

elif MODO == "item_vencedor":
    if df_venc.empty or "chave_licitacao" not in df_venc.columns:
        raise RuntimeError("df_venc sem chave_licitacao. Verifique a Etapa 5.")

    # Join: cada item vencedor recebe os dados da licitação pai
    base_final = df_venc.merge(
        df_processos[colunas_processos],
        on="chave_licitacao",
        how="left"
    )

    vinc = base_final["valorEstimado"].notna().sum()
    total = len(base_final)
    print(f"  Itens com dados da licitação pai: {vinc:,} de {total:,} "
          f"({vinc/total*100:.1f}%)")
    if total - vinc > 0:
        print(f"  [AVISO] {total - vinc:,} itens sem vínculo com licitação pai.")

print(f"  Base final: {len(base_final):,} linhas | {base_final.shape[1]} colunas")


# ─────────────────────────────────────────────────────────────────────────────
# ETAPA 7 – EXPORTAÇÃO
# ─────────────────────────────────────────────────────────────────────────────

print("\n" + "="*60)
print("ETAPA 7 – EXPORTAÇÃO")
print("="*60)

base_final.to_csv(ARQUIVO_SAIDA, index=False, sep=";", encoding="utf-8-sig")
print(f"\n  ✔ Arquivo salvo: {os.path.abspath(ARQUIVO_SAIDA)}")
print(f"  Total de registros: {len(base_final):,}")
print(f"  Total de colunas  : {base_final.shape[1]}")

# ─────────────────────────────────────────────────────────────────────────────
# RESUMO ESTATÍSTICO
# ─────────────────────────────────────────────────────────────────────────────

print("\n" + "="*60)
print("RESUMO ESTATÍSTICO – VARIÁVEIS PRINCIPAIS")
print("="*60)

cols_resumo = [c for c in [
    "qtd_participantes", "houve_disputa",
    "economia_pct", "economia_absoluta",
    "valorEstimado", "valorHomologado",
    "economia_item_pct", "economia_item",
    "media_dias_vigencia", "qtd_contratos"
] if c in base_final.columns]

if cols_resumo:
    print(base_final[cols_resumo].describe().round(2).to_string())

# ─────────────────────────────────────────────────────────────────────────────
# CHECAGEM DE INTEGRIDADE
# ─────────────────────────────────────────────────────────────────────────────

print("\n" + "="*60)
print("CHECAGEM DE INTEGRIDADE")
print("="*60)

for col in cols_resumo:
    nulos = base_final[col].isna().sum()
    pct   = nulos / len(base_final) * 100 if len(base_final) > 0 else 0
    status = "✔" if pct < 10 else ("⚠" if pct < 50 else "✗")
    print(f"  {status} {col}: {nulos:,} nulos ({pct:.1f}%)")

print("\n✅ Processo concluído!")