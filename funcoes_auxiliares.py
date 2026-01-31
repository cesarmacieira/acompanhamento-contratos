import pandas as pd
import numpy as np

def formatar_real(valor):
    """Formata valor para Real brasileiro (R$ 1.234.567,89)"""
    if pd.isna(valor):
        return "R$ 0,00"
    return f"R$ {valor:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")

def formatar_percentual(valor):
    """Formata percentual no padrão brasileiro"""
    if pd.isna(valor) or np.isinf(valor):
        return "0,0%"
    return f"{valor:.1f}%".replace(".", ",")

def quebrar_linha(texto, max_chars=40):
    """Quebra texto em múltiplas linhas para gráficos"""
    if pd.isna(texto):
        return ""
    palavras = str(texto).split()
    linhas = []
    linha_atual = []
    tamanho_atual = 0
    
    for palavra in palavras:
        if tamanho_atual + len(palavra) + 1 <= max_chars:
            linha_atual.append(palavra)
            tamanho_atual += len(palavra) + 1
        else:
            if linha_atual:
                linhas.append(" ".join(linha_atual))
            linha_atual = [palavra]
            tamanho_atual = len(palavra)
    
    if linha_atual:
        linhas.append(" ".join(linha_atual))
    
    return "\n".join(linhas[:2])  # Máximo 2 linhas

def carregar_dados_trf5():
    """Carrega dados do portal TRF5"""
    try:
        df_resumo = pd.read_parquet('Dados_resumo_centro_de_custos.parquet')
    except:
        try:
            df_resumo = pd.read_excel('Dados resumo centro de custos.xlsx')
        except:
            df_resumo = pd.DataFrame()
    
    try:
        df_empenhos = pd.read_parquet('Dados empenhos.parquet')
    except:
        try:
            df_empenhos = pd.read_excel('Dados empenhos.xlsx')
        except:
            df_empenhos = pd.DataFrame()
    
    try:
        df_pre_empenhos = pd.read_parquet('Dados_pré_empenhos.parquet')
    except:
        try:
            df_pre_empenhos = pd.read_excel('Dados pré empenhos.xlsx')
        except:
            df_pre_empenhos = pd.DataFrame()
    
    try:
        df_rp = pd.read_parquet('Dados_restos_a_pagar.parquet')
    except:
        try:
            df_rp = pd.read_excel('Dados restos a pagar.xlsx')
        except:
            df_rp = pd.DataFrame()
    
    try:
        df_portal = pd.read_parquet('Dados portal TRF5.parquet')
    except:
        try:
            df_portal = pd.read_excel('Dados portal TRF5.xlsx')
        except:
            df_portal = pd.DataFrame()
    
    # Processar df_resumo
    if not df_resumo.empty:
        df_resumo['Ano'] = df_resumo['Ano'].astype(str)
        financial_cols = ['Valor Limite Disponível', 'Valor Pré-Empenhos a Empenhar', 
                         'Valor Empenhos Total', 'Valor Empenhos Pagos',
                         'Limite', 'Destaques', 'Pré-empenhado', 'Empenhado', 'Disponível']
        
        for col in financial_cols:
            if col in df_resumo.columns:
                df_resumo[col] = pd.to_numeric(df_resumo[col], errors='coerce').fillna(0)
        
        if 'Gestor(a)' in df_resumo.columns:
            df_resumo['Gestor(a)'] = df_resumo['Gestor(a)'].fillna('Não informado')
        if 'Centro de Custo' in df_resumo.columns:
            df_resumo['Centro de Custo'] = df_resumo['Centro de Custo'].fillna('Não informado')
        
        df_resumo = df_resumo.rename(columns={
            "Centro.de.Custo": "Centro de Custo", 
            'Valor.Limite.Disponível': 'Valor Limite Disponível',
            'Valor.Pré-Empenhos.a.Empenhar': 'Valor Pré-Empenhos a Empenhar', 
            'Valor.Empenhos.Total': 'Valor Empenhos Total', 
            'Valor.Empenhos.Pagos': 'Valor Empenhos Pagos'
        })
    
    # Processar df_empenhos
    if not df_empenhos.empty:
        financial_cols = ['Valor Empenhado', 'Valor Pago', 'R$ a pagar']
        for col in financial_cols:
            if col in df_empenhos.columns:
                df_empenhos[col] = pd.to_numeric(df_empenhos[col], errors='coerce').fillna(0)
    
    # Processar df_pre_empenhos
    if not df_pre_empenhos.empty:
        if 'Ano' in df_pre_empenhos.columns:
            df_pre_empenhos['Ano'] = df_pre_empenhos['Ano'].astype(str)
        if 'Valor Pré-Empenhado' in df_pre_empenhos.columns:
            df_pre_empenhos['Valor Pré-Empenhado'] = pd.to_numeric(df_pre_empenhos['Valor Pré-Empenhado'], errors='coerce').fillna(0)
    
    # Processar df_rp
    if not df_rp.empty:
        financial_cols = ['Valor RP Processados Inscritos', 'RP Inscritos', 'RP Cancelados', 
                         'RP Bloqueados', 'RP Pagos', 'RP a Pagar']
        for col in financial_cols:
            if col in df_rp.columns:
                df_rp[col] = pd.to_numeric(df_rp[col], errors='coerce').fillna(0)
    
    # Processar df_portal
    if not df_portal.empty:
        if 'Ano' in df_portal.columns:
            df_portal['Ano'] = df_portal['Ano'].astype(str)
    
    return df_resumo, df_empenhos, df_pre_empenhos, df_rp, df_portal

def extrair_numero_contrato_trf5(df_empenhos):
    """
    Extrai números de contratos dos dados do TRF5
    Tenta extrair do campo 'Número Processo', 'Contrato', ou campos similares
    """
    contratos_trf5 = set()
    
    if df_empenhos.empty:
        return contratos_trf5
    
    # Verificar colunas que podem conter número de contrato
    colunas_possiveis = ['Contrato', 'Número Contrato', 'numeroContrato', 'Número Processo', 'Processo']
    
    for coluna in colunas_possiveis:
        if coluna in df_empenhos.columns:
            valores = df_empenhos[coluna].dropna().astype(str).unique()
            contratos_trf5.update(valores)
    
    return contratos_trf5

def normalizar_numero_contrato(numero):
    """
    Normaliza número de contrato removendo caracteres especiais e espaços
    """
    if pd.isna(numero):
        return ""
    
    # Converter para string e remover espaços, barras, traços
    numero_str = str(numero).strip()
    numero_str = numero_str.replace(" ", "").replace("/", "").replace("-", "")
    
    return numero_str.upper()

def cruzar_contratos_comprasnet_trf5(df_comprasnet, df_trf5_empenhos):
    """
    Cruza os dados de contratos do ComprasNet com os dados do TRF5
    Retorna DataFrames com contratos em comum, apenas no ComprasNet e apenas no TRF5
    """
    # Normalizar números de contratos do ComprasNet
    df_cn = df_comprasnet.copy()
    df_cn['numeroContrato_normalizado'] = df_cn['numeroContrato'].apply(normalizar_numero_contrato)
    
    # Extrair e normalizar números de contratos do TRF5
    contratos_trf5_raw = extrair_numero_contrato_trf5(df_trf5_empenhos)
    contratos_trf5_norm = {normalizar_numero_contrato(c): c for c in contratos_trf5_raw}
    
    # Identificar contratos em comum
    df_cn['esta_no_trf5'] = df_cn['numeroContrato_normalizado'].isin(contratos_trf5_norm.keys())
    
    # Separar os conjuntos
    contratos_comuns = df_cn[df_cn['esta_no_trf5']].copy()
    apenas_comprasnet = df_cn[~df_cn['esta_no_trf5']].copy()
    
    # Contratos apenas no TRF5
    contratos_cn_norm = set(df_cn['numeroContrato_normalizado'].unique())
    apenas_trf5_norm = set(contratos_trf5_norm.keys()) - contratos_cn_norm
    apenas_trf5 = pd.DataFrame({
        'numeroContrato_normalizado': list(apenas_trf5_norm),
        'numeroContrato_original': [contratos_trf5_norm[c] for c in apenas_trf5_norm]
    })
    
    return contratos_comuns, apenas_comprasnet, apenas_trf5, contratos_trf5_norm

def obter_dados_trf5_por_contrato(numero_contrato_normalizado, df_empenhos, contratos_trf5_norm):
    """
    Obtém dados do TRF5 para um contrato específico
    """
    if numero_contrato_normalizado not in contratos_trf5_norm:
        return pd.DataFrame()
    
    # Buscar nos empenhos do TRF5
    numero_original = contratos_trf5_norm[numero_contrato_normalizado]
    
    # Verificar em diferentes colunas
    colunas_possiveis = ['Contrato', 'Número Contrato', 'numeroContrato', 'Número Processo', 'Processo']
    
    mask = pd.Series([False] * len(df_empenhos))
    
    for coluna in colunas_possiveis:
        if coluna in df_empenhos.columns:
            mask = mask | (df_empenhos[coluna].astype(str) == numero_original)
    
    return df_empenhos[mask].copy()
