import pandas as pd
import glob
import os

# 1. Configurações Iniciais
caminho_pasta = r'C:\Users\gusta\Downloads\aaaa'  # ajuta para o nome da pasta que deseja unificiar
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
        # Tente ler o arquivo (ajuste sep e encoding se necessário)
        df = pd.read_csv(arquivo, sep=';', encoding='latin-1', low_memory=False)
        
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
    
    # Limpeza básica: remove duplicatas se houver
    df_unificado = df_unificado.drop_duplicates()
    
    # Salva o arquivo final do grupo
    nome_saida = f"df_{tipo}_unificado.csv"
    df_unificado.to_csv(nome_saida, index=False, sep=';', encoding='utf-8-sig')
    
    print(f"-> Grupo '{tipo}' unificado: {len(df_unificado)} linhas. Salvo como: {nome_saida}")

print("\nProcesso concluído!")