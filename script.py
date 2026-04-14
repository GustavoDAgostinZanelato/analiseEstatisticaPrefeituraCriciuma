import pandas as pd
import glob
import os

# 1. Configurações Iniciais
caminho_pasta = r'C:\Users\gusta\Desktop\Projeto Extensão Estatística\Execução Detalhada de Despesas-2020'  # ajuste para o nome da pasta que deseja unificar
arquivos = glob.glob(os.path.join(caminho_pasta, "*.csv"))

# Dicionário para armazenar os grupos (ex: {'contratos': [df1, df2], 'itens': [df1, df2]})
grupos_dataframes = {}

print(f"Encontrados {len(arquivos)} arquivos. Iniciando agrupamento...")

# 2. Processamento e Agrupamento
for arquivo in arquivos:
    # Pega apenas o nome do arquivo e remove a extensão e números/datas do final
    # Exemplo: 'contratos_2019_01.csv' vira 'contratos'
    nome_base = os.path.basename(arquivo).split('_')[0].split('-')[0].lower()

    try:
        # Detecta o separador correto antes de ler
        with open(arquivo, 'r', encoding='latin-1') as f:
            primeira_linha = f.readline()
        sep = ';' if primeira_linha.count(';') >= primeira_linha.count(',') else ','

        # Lê o CSV sem converter tipos automaticamente — evita notação científica em IDs
        df = pd.read_csv(
            arquivo,
            sep=sep,
            encoding='latin-1',
            low_memory=False,
            dtype=str          # <-- FIX: lê tudo como string; conversão numérica fica no concatenacaoDados
        )

        # Adiciona uma coluna para saber de qual arquivo veio (útil para auditoria)
        df['origem_arquivo'] = os.path.basename(arquivo)

        if nome_base not in grupos_dataframes:
            grupos_dataframes[nome_base] = []

        grupos_dataframes[nome_base].append(df)
    except Exception as e:
        print(f"Erro ao ler {arquivo}: {e}")

# 3. Unificação e Exportação
print("\nUnificando grupos...")

for tipo, lista_df in grupos_dataframes.items():
    df_unificado = pd.concat(lista_df, ignore_index=True)

    # FIX: remove duplicatas considerando todas as colunas exceto 'origem_arquivo'
    colunas_chave = [c for c in df_unificado.columns if c != 'origem_arquivo']
    df_unificado = df_unificado.drop_duplicates(subset=colunas_chave)

    # Salva o arquivo final do grupo
    # FIX: quoting=1 (QUOTE_ALL) + encoding utf-8-sig evita que o Excel
    #      interprete números grandes como notação científica ao abrir o CSV
    nome_saida = f"df_{tipo}_unificado.csv"
    df_unificado.to_csv(
        nome_saida,
        index=False,
        sep=';',
        encoding='utf-8-sig',
    )

    print(f"-> Grupo '{tipo}' unificado: {len(df_unificado)} linhas. Salvo como: {nome_saida}")

print("\nProcesso concluído!")