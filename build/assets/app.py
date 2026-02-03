import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from datetime import datetime, timedelta
from plotly.subplots import make_subplots
import numpy as np
from datetime import datetime
from PIL import Image,ImageDraw,ImageFont
from buscador_contratos import BuscadorContratos
import io
import os
import unicodedata

st.set_page_config(page_title="Gestão de Contratos Públicos",layout="wide")

def header_banner():
    W,H=2200,140
    bg=(0,104,157,255)
    banner=Image.new("RGBA",(W,H),bg)
    draw=ImageDraw.Draw(banner)
    BASE_DIR = os.path.dirname(os.path.abspath(__file__))
    FONT_PATH = os.path.join(BASE_DIR, "fonts/DejaVuSans-Bold.ttf")

    try:
        font = ImageFont.truetype(FONT_PATH, 45)
    except Exception as e:
        st.error(f"Erro ao carregar fonte: {e}")
        font = ImageFont.load_default()


    # LOGO PRINCIPAL À ESQUERDA
    logo_esquerda="logos/logo_horizontal_branca.png"
    im_left=Image.open(logo_esquerda).convert("RGBA")
    h_left=80
    w_left=int(im_left.size[0]*h_left/im_left.size[1])
    im_left=im_left.resize((w_left,h_left))
    left_x=32
    banner.alpha_composite(im_left,(left_x,(H-h_left)//2))

    # LOGOS À DIREITA (calcular largura total)
    logos_direita=["logos/logo_Justica_Federal_5Regiao_branca.png", 
                   "logos/logo_Justica_Federal_Ceara_branca.png", 
                   "logos/Logo_PNUD_branca.png"]
    gap=28
    total_w=0
    resized=[]
    for p in logos_direita:
        im=Image.open(p).convert("RGBA")
        h=80
        w=int(im.size[0]*h/im.size[1])
        resized.append((im.resize((w,h)),w,h))
        total_w+=w
    total_w+=gap*(len(resized)-1)

    right_start=W-32-total_w
    x=right_start
    for im,w,h in resized:
        banner.alpha_composite(im,(x,(H-h)//2))
        x+=w+gap

    # TÍTULO CENTRALIZADO ENTRE LOGOS
    texto="Painel Executivo de Contratos, Orçamento e Financeiro"
    bbox = draw.textbbox((0, 0), texto, font=font)

    text_w = bbox[2] - bbox[0]
    text_h = bbox[3] - bbox[1]

    area_inicio = left_x + w_left + 32
    area_fim = right_start - 32
    centro_area = (area_inicio + area_fim) // 2
    texto_x = centro_area - (text_w // 2)
    texto_y = (H - text_h) // 2 - bbox[1]
    draw.text((texto_x, texto_y),texto,fill=(255,255,255,255),font=font)
    return banner

st.image(header_banner(), use_container_width=True)

st.markdown('''
    <style>
    .main {
        padding: 0rem 1rem;
    }
    
    /* Tabs responsivas - esconde overflow e permite scroll horizontal */
    .stTabs [data-baseweb="tab-list"] {
        gap: 2px;
        overflow-x: auto;
        overflow-y: hidden;
        white-space: nowrap;
        flex-wrap: nowrap !important;
        -webkit-overflow-scrolling: touch;
        scrollbar-width: thin;
    }
    
    .stTabs [data-baseweb="tab-list"]::-webkit-scrollbar {
        height: 4px;
    }
    
    .stTabs [data-baseweb="tab-list"]::-webkit-scrollbar-thumb {
        background-color: #0068c9;
        border-radius: 2px;
    }
    
    .stTabs [data-baseweb="tab"] {
        padding: 8px 16px;
        background-color: #f0f2f6;
        border-radius: 5px 5px 0px 0px;
        white-space: nowrap;
        flex-shrink: 0;
        font-size: 14px;
    }
    
    /* Ajuste para telas pequenas */
    @media (max-width: 768px) {
        .stTabs [data-baseweb="tab"] {
            padding: 6px 12px;
            font-size: 12px;
        }
    }
    
    /* Aba selecionada */
    .stTabs [aria-selected="true"] {
        background-color: #00689D;
        color: white;
    }

    /* Hover: quando passar o mouse em aba NÃO selecionada, a fonte fica #00689D */
    .stTabs [data-baseweb="tab"]:not([aria-selected="true"]):hover {
        color: #00689D !important;
    }

    .metric-card {
        background-color: #f8f9fa;
        padding: 20px;
        border-radius: 10px;
        border-left: 4px solid #0068c9;
        box-shadow: 0 2px 4px rgba(0,0,0,0.1);
    }
    .metric-title {
        font-size: 14px;
        color: #666;
        margin-bottom: 5px;
    }
    .metric-value {
        font-size: 24px;
        font-weight: bold;
        color: #0068c9;
    }
    h1 {
        color: #0068c9;
        border-bottom: 3px solid #0068c9;
        padding-bottom: 10px;
    }
    h2 {
        color: #555;
        margin-top: 20px;
    }
    </style>
''', unsafe_allow_html=True)


# Função para formatação brasileira
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

# Função para carregar dados do resumo
@st.cache_data
def load_resumo_data():
    # try:
    #     df = pd.read_parquet('dados/Dados resumo centro de custos.parquet')
    # except:
    df = pd.read_excel('dados/Dados resumo centro de custos.xlsx')
    
    # Converter Ano para string
    df['Ano'] = df['Ano'].astype(str)
    
    # Converter colunas financeiras para numérico
    financial_cols = ['Valor Limite Disponível', 'Valor Pré-Empenhos a Empenhar', 
                     'Valor Empenhos Total', 'Valor Empenhos Pagos',
                     'Limite', 'Destaques', 'Pré-empenhado', 'Empenhado', 'Disponível']

    for col in financial_cols:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors='coerce').fillna(0)
    
    # Preencher campos vazios
    if 'Gestor(a)' in df.columns:
        df['Gestor(a)'] = df['Gestor(a)'].fillna('Não informado')
    if 'Centro de Custo' in df.columns:
        df['Centro de Custo'] = df['Centro de Custo'].fillna('Não informado')
    
    df = df.rename(columns={"Centro.de.Custo": "Centro de Custo", 'Valor.Limite.Disponível': 'Valor Limite Disponível',
    'Valor.Pré-Empenhos.a.Empenhar': 'Valor Pré-Empenhos a Empenhar', 'Valor.Empenhos.Total': 'Valor Empenhos Total', 
    'Valor.Empenhos.Pagos': 'Valor Empenhos Pagos'})
    
    return df

# Função para carregar dados de empenhos
@st.cache_data
def load_empenhos_data():
    # try:
    df = pd.read_parquet('dados/Dados empenhos.parquet')
    # except:
    #     df = pd.read_excel('dados/Dados empenhos.xlsx')
    
    # Converter colunas financeiras
    df = df.rename(columns={'Processo.SEI': 'Processo SEI','Observação./.Descrição': 'Observação /Descrição',
                            'Valor.Empenhado': 'Valor Empenhado','Valor.Pago': 'Valor Pago','R$.a.pagar': 'R$ a pagar'})
    financial_cols = ['Valor Empenhado', 'Valor Pago', 'R$ a pagar']
    for col in financial_cols:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors='coerce').fillna(0)
            df[col] = df[col].where(df[col].abs() > 1e-9, 0)

    return df

# Função para carregar dados de pré-empenhos
@st.cache_data
def load_pre_empenhos_data():
    # try:
    df = pd.read_parquet('dados/Dados pré empenhos.parquet')
    # except:
    #     df = pd.read_excel('dados/Dados pré empenhos.xlsx')
    df = df.rename(columns={'Processo.SEI': 'Processo SEI','Valor.Pré-Empenhado': 'Valor Pré-Empenhado'})
    # Converter Ano para string
    if 'Ano' in df.columns:
        df['Ano'] = df['Ano'].astype(str)
    
    # Converter colunas financeiras
    if 'Valor Pré-Empenhado' in df.columns:
        df['Valor Pré-Empenhado'] = pd.to_numeric(df['Valor Pré-Empenhado'], errors='coerce').fillna(0)
    
    return df

# Função para carregar dados de restos a pagar
@st.cache_data
def load_restos_pagar_data():
    #try:
    df = pd.read_parquet('dados/Dados restos a pagar.parquet')
    #except:
    #    df = pd.read_excel('dados/Dados restos a pagar.xlsx')
    df = df.rename(columns={'Valor.RP.Processados.Inscritos': 'Valor RP Processados Inscritos',
                            'RP.Inscritos': 'RP Inscritos', 'RP.Cancelados': 'RP Cancelados', 
                            'RP.Bloqueados': 'RP Bloqueados', 'RP.Pagos': 'RP Pagos', 'RP.a.Pagar': 'RP a Pagar'})
    # Converter colunas financeiras
    financial_cols = ['Valor RP Processados Inscritos', 'RP Inscritos', 'RP Cancelados', 
                     'RP Bloqueados', 'RP Pagos', 'RP a Pagar']
    for col in financial_cols:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors='coerce').fillna(0)
    
    return df

# Função para carregar dados do comprasnet (para buscas detalhadas)
@st.cache_data(show_spinner=True)
def load_comprasnet_data():
    buscador = BuscadorContratos()
    contratos = buscador.buscar_multiplos_anos("12000","090006",2015,datetime.now().year)
    return pd.DataFrame(contratos)
df = load_comprasnet_data()
df = df.dropna(how="all")
df = df.dropna(subset=["numeroContrato","dataVigenciaFinal"])
if df.empty:
    st.warning("Nenhum contrato encontrado.")
    st.stop()

df["dataVigenciaInicial"] = pd.to_datetime(df["dataVigenciaInicial"], errors="coerce")
df["dataVigenciaFinal"] = pd.to_datetime(df["dataVigenciaFinal"], errors="coerce")
df["valorGlobal"] = pd.to_numeric(df["valorGlobal"], errors="coerce").fillna(0)

hoje = pd.Timestamp.today()

df["status"] = df["dataVigenciaFinal"].apply(lambda x: "Vencido" if x < hoje else "Vigente")
df["ano"] = df["dataVigenciaInicial"].dt.year

# Carregar dados
df_resumo = load_resumo_data()
df_empenhos = load_empenhos_data()
df_pre_empenhos = load_pre_empenhos_data()
df_rp = load_restos_pagar_data()

# Função para normalizar texto
def norm(s):
    if pd.isna(s):
        return ""
    s = unicodedata.normalize("NFKD", str(s).lower())
    return "".join(c for c in s if not unicodedata.combining(c))

colunas_renomeadas = ["Código do Órgão","Nome do Órgão","Código da Unidade Gestora","Nome da Unidade Gestora",
    "Código da Unidade Gestora de Origem do Contrato","Nome da Unidade Gestora de Origem do Contrato",
    "Tipo de Receita ou Despesa","Número do Contrato","Código da Unidade Realizadora da Compra",
    "Nome da Unidade Realizadora da Compra","Número da Compra","Código da Modalidade de Compra",
    "Nome da Modalidade de Compra","Código do Tipo","Nome do Tipo","Código da Categoria","Nome da Categoria",
    "Código da Subcategoria","Nome da Subcategoria","CNPJ ou CPF do Fornecedor","Razão Social do Fornecedor",
    "Número do Processo","Objeto do Contrato","Informações Complementares","Data de Vigência Inicial",
    "Data de Vigência Final","Valor Global do Contrato","Número de Parcelas","Valor da Parcela",
    "Valor Acumulado","Total de Despesas Acessórias","Data e Hora de Inclusão","Número de Controle PNCP do Contrato",
    "ID da Compra","Data e Hora de Exclusão","Contrato Excluído","Unidades Requisitantes","Status","Ano"]

# Criar abas principais
tab1, tab2, tab3, tab4, tab5, tab6, tab7 = st.tabs([
    "📋 Lista de contratos", 
    "🚨 Alertas", 
    "📊 Análises dos contratos",
    "💰 Análise financeira",  
    "💳 Dados orçamentários", 
    "❗ Inconsistências nos sistemas",
    #"🔍 Buscador detalhado",
    "📈 Análise detalhada de contratos"])

# ==================== ABA 1: LISTA DE CONTRATOS ====================
with tab1:
    st.subheader("Lista geral de contratos")
    c1, c2, c3, c4 = st.columns(4)
    fornecedor = c1.multiselect("Fornecedor",sorted(df["nomeRazaoSocialFornecedor"].dropna().unique()))
    unidade = c2.multiselect("Unidade realizadora",sorted(df["nomeUnidadeRealizadoraCompra"].dropna().unique()))
    ano = c3.multiselect("Ano",sorted(df["ano"].dropna().unique()))
    status = c4.multiselect("Status",["Vigente", "Vencido"])
    c5, c6, c7, c8 = st.columns(4)
    modalidade = c5.multiselect("Modalidade de compra",sorted(df["nomeModalidadeCompra"].dropna().unique()))
    tipo = c6.multiselect("Tipo de contrato",sorted(df["nomeTipo"].dropna().unique()))
    categoria = c7.multiselect("Categoria",sorted(df["nomeCategoria"].dropna().unique()))
    busca_texto = c8.text_input("Busca livre (objeto / informações complementares)")
    c9, c10, c11, c12 = st.columns(4)
    data_ini = c9.date_input("Vigência final a partir de",value=df["dataVigenciaFinal"].min().date() if pd.notnull(df["dataVigenciaFinal"].min()) else None)
    data_fim = c10.date_input("Vigência final até",value=df["dataVigenciaFinal"].max().date() if pd.notnull(df["dataVigenciaFinal"].max()) else None)
    numero_contrato = c11.multiselect("Número do contrato",sorted(df["numeroContrato"].dropna().unique()))
    valor_parcela_min, valor_parcela_max = c12.slider("Valor do contrato (R$)",float(df["valorGlobal"].min()),
        float(df["valorGlobal"].max()),(float(df["valorGlobal"].min()), float(df["valorGlobal"].max())))
    df_f = df.copy()
    if fornecedor:
        df_f = df_f[df_f["nomeRazaoSocialFornecedor"].isin(fornecedor)]
    if unidade:
        df_f = df_f[df_f["nomeUnidadeRealizadoraCompra"].isin(unidade)]
    if ano:
        df_f = df_f[df_f["ano"].isin(ano)]
    if status:
        df_f = df_f[df_f["status"].isin(status)]
    if modalidade:
        df_f = df_f[df_f["nomeModalidadeCompra"].isin(modalidade)]
    if tipo:
        df_f = df_f[df_f["nomeTipo"].isin(tipo)]
    if categoria:
        df_f = df_f[df_f["nomeCategoria"].isin(categoria)]
    if busca_texto:
        texto = norm(busca_texto)
        df_f = df_f[df_f["objeto"].apply(norm).str.contains(texto, na=False) | df_f["informacoesComplementares"].apply(norm).str.contains(texto, na=False)]
    if data_ini:
        df_f = df_f[df_f["dataVigenciaFinal"] >= pd.to_datetime(data_ini)]
    if data_fim:
        df_f = df_f[df_f["dataVigenciaFinal"] <= pd.to_datetime(data_fim)]
    df_f = df_f[(df_f["valorParcela"] >= valor_parcela_min) & (df_f["valorParcela"] <= valor_parcela_max)]
    if numero_contrato:
        df_f = df_f[df_f["numeroContrato"].isin(numero_contrato)]

    df_f.columns = colunas_renomeadas
    st.dataframe(df_f.sort_values("Data de Vigência Final").reset_index(drop=True),use_container_width=True)
    st.caption(f"Contratos exibidos: {len(df_f)}")
    buffer = io.BytesIO()
    with pd.ExcelWriter(buffer, engine="openpyxl") as writer:
        df_f.sort_values("Data de Vigência Final").to_excel(writer, index=False, sheet_name="Contratos")
    buffer.seek(0)

    st.download_button(label="⬇️ Baixar contratos", data=buffer, file_name="contratos.xlsx",
        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")

# ==================== ABA 2: ALERTAS ====================
with tab2:
    st.subheader("Alertas de prazo e risco")
    v30 = df[(df["dataVigenciaFinal"] >= hoje) & (df["dataVigenciaFinal"] <= hoje + timedelta(days=30))]
    v60 = df[(df["dataVigenciaFinal"] > hoje + timedelta(days=30)) & (df["dataVigenciaFinal"] <= hoje + timedelta(days=60))]
    v90 = df[(df["dataVigenciaFinal"] > hoje + timedelta(days=60)) & (df["dataVigenciaFinal"] <= hoje + timedelta(days=90))]
    vencidos = df[df["dataVigenciaFinal"] < hoje]
    vigentes = df[df["dataVigenciaFinal"] >= hoje]
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Quantidade total de contratos", len(df))
    c2.metric("Contratos vigentes", len(vigentes))
    c3.metric("Contratos vencidos", len(vencidos))
    c4.metric("Percentual de contratos vencidos", f"{(len(vencidos)/len(df)*100):.1f}%" if len(df) > 0 else "0%")
    c5, c6, c7, c8 = st.columns(4)
    c5.metric("Vencendo em 30 dias", len(v30))
    c6.metric("Vencendo em 60 dias", len(v60))
    c7.metric("Vencendo em 90 dias", len(v90))
    c8.metric("Total contratos críticos", len(v30)+len(v60)+len(v90))
    c9, c10, c11, c12 = st.columns(4)
    c9.metric("Valor total contratado", f"R$ {df['valorGlobal'].sum():,.2f}".replace(",", "X").replace(".", ",").replace("X", "."))
    c10.metric("Valor vigente", f"R$ {vigentes['valorGlobal'].sum():,.2f}".replace(",", "X").replace(".", ",").replace("X", "."))
    c11.metric("Valor vencido", f"R$ {vencidos['valorGlobal'].sum():,.2f}".replace(",", "X").replace(".", ",").replace("X", "."))
    c12.metric("Valor total em risco", f"R$ {(v30['valorGlobal'].sum()+v60['valorGlobal'].sum()+v90['valorGlobal'].sum()):,.2f}".replace(",", "X").replace(".", ",").replace("X", "."))
    st.divider()
    st.markdown("### 📋 Contratos vigentes")
    c29, c30, c31, c32 = st.columns(4)
    c29.metric("Qtd contratos", len(vigentes))
    c30.metric("Percentual do total", f"{(len(vigentes)/len(df)*100):.1f}%" if len(df) > 0 else "0%")
    c31.metric("Valor total vigente", f"R$ {vigentes['valorGlobal'].sum():,.2f}".replace(",", "X").replace(".", ",").replace("X", "."))
    c32.metric("Valor médio", f"R$ {vigentes['valorGlobal'].mean():,.2f}".replace(",", "X").replace(".", ",").replace("X", ".") if not vigentes.empty else "R$ 0,00")
    c33, c34, c35, c36 = st.columns(4)
    c33.metric("Maior contrato", f"R$ {vigentes['valorGlobal'].max():,.2f}".replace(",", "X").replace(".", ",").replace("X", ".") if not vigentes.empty else "R$ 0,00")
    c34.metric("Vigentes fora de risco (>90d)", len(vigentes)-(len(v30)+len(v60)+len(v90)))
    c35.metric("Valor fora de risco", f"R$ {(vigentes['valorGlobal'].sum()-(v30['valorGlobal'].sum()+v60['valorGlobal'].sum()+v90['valorGlobal'].sum())):,.2f}".replace(",", "X").replace(".", ",").replace("X", "."))
    c36.metric("Percentual fora de risco", f"{((len(vigentes)-(len(v30)+len(v60)+len(v90)))/len(vigentes)*100):.1f}%" if len(vigentes) > 0 else "0%")
    colvigentes_1, colvigentes_2 = st.columns(2)
    numero_contrato = colvigentes_1.multiselect("Número do contrato",sorted(vigentes["numeroContrato"].dropna().unique()))
    fornecedor = colvigentes_2.multiselect("Fornecedor",sorted(vigentes["nomeRazaoSocialFornecedor"].dropna().unique()))
    if numero_contrato:
        vigentes = vigentes[vigentes["numeroContrato"].isin(numero_contrato)]
    if fornecedor:
        vigentes = vigentes[vigentes["nomeRazaoSocialFornecedor"].isin(fornecedor)]
    vigentes1 = vigentes.copy() 
    vigentes1.columns = colunas_renomeadas
    st.dataframe(vigentes1.sort_values("Data de Vigência Final").reset_index(drop=True),use_container_width=True)
    st.divider()
    with st.container():
        st.markdown("### ⏰ Vencendo em até 30 dias")
        c13, c14, c15, c16 = st.columns(4)
        c13.metric("Qtd contratos", len(v30))
        c14.metric("Valor total", f"R$ {v30['valorGlobal'].sum():,.2f}".replace(",", "X").replace(".", ",").replace("X", "."))
        c15.metric("Valor do maior contrato", f"R$ {v30['valorGlobal'].max():,.2f}".replace(",", "X").replace(".", ",").replace("X", ".") if not v30.empty else "R$ 0,00")
        c16.metric("Média por contrato", f"R$ {v30['valorGlobal'].mean():,.2f}".replace(",", "X").replace(".", ",").replace("X", ".") if not v30.empty else "R$ 0,00")
        colv30_1, colv30_2 = st.columns(2)
        numero_contrato = colv30_1.multiselect("Número do contrato",sorted(v30["numeroContrato"].dropna().unique()))
        fornecedor = colv30_2.multiselect("Fornecedor",sorted(v30["nomeRazaoSocialFornecedor"].dropna().unique()))
        if numero_contrato:
            v30 = v30[v30["numeroContrato"].isin(numero_contrato)]
        if fornecedor:
            v30 = v30[v30["nomeRazaoSocialFornecedor"].isin(fornecedor)]
        v301 = v30.copy() 
        v301.columns = colunas_renomeadas
        st.dataframe(v301.sort_values("Data de Vigência Final").reset_index(drop=True),use_container_width=True)
    with st.container():
        st.markdown("### ⏳ Vencendo entre 31 e 60 dias")
        c17, c18, c19, c20 = st.columns(4)
        c17.metric("Qtd contratos", len(v60))
        c18.metric("Valor total", f"R$ {v60['valorGlobal'].sum():,.2f}".replace(",", "X").replace(".", ",").replace("X", "."))
        c19.metric("Valor do maior contrato", f"R$ {v60['valorGlobal'].max():,.2f}".replace(",", "X").replace(".", ",").replace("X", ".") if not v60.empty else "R$ 0,00")
        c20.metric("Média por contrato", f"R$ {v60['valorGlobal'].mean():,.2f}".replace(",", "X").replace(".", ",").replace("X", ".") if not v60.empty else "R$ 0,00")
        colv60_1, colv60_2 = st.columns(2)
        numero_contrato = colv60_1.multiselect("Número do contrato",sorted(v60["numeroContrato"].dropna().unique()))
        fornecedor = colv60_2.multiselect("Fornecedor",sorted(v60["nomeRazaoSocialFornecedor"].dropna().unique()))
        if numero_contrato:
            v60 = v60[v60["numeroContrato"].isin(numero_contrato)]
        if fornecedor:
            v60 = v60[v60["nomeRazaoSocialFornecedor"].isin(fornecedor)]
        v601 = v60.copy() 
        v601.columns = colunas_renomeadas
        st.dataframe(v601.sort_values("Data de Vigência Final").reset_index(drop=True),use_container_width=True)
    with st.container():
        st.markdown("### ⏳ Vencendo entre 61 e 90 dias")
        c21, c22, c23, c24 = st.columns(4)
        c21.metric("Qtd contratos", len(v90))
        c22.metric("Valor total", f"R$ {v90['valorGlobal'].sum():,.2f}".replace(",", "X").replace(".", ",").replace("X", "."))
        c23.metric("Valor do maior contrato", f"R$ {v90['valorGlobal'].max():,.2f}".replace(",", "X").replace(".", ",").replace("X", ".") if not v90.empty else "R$ 0,00")
        c24.metric("Média por contrato", f"R$ {v90['valorGlobal'].mean():,.2f}".replace(",", "X").replace(".", ",").replace("X", ".") if not v90.empty else "R$ 0,00")
        colv90_1, colv90_2 = st.columns(2)
        numero_contrato = colv90_1.multiselect("Número do contrato",sorted(v90["numeroContrato"].dropna().unique()))
        fornecedor = colv90_2.multiselect("Fornecedor",sorted(v90["nomeRazaoSocialFornecedor"].dropna().unique()))
        if numero_contrato:
            v90 = v90[v90["numeroContrato"].isin(numero_contrato)]
        if fornecedor:
            v90 = v90[v90["nomeRazaoSocialFornecedor"].isin(fornecedor)]
        v901 = v90.copy() 
        v901.columns = colunas_renomeadas
        st.dataframe(v901.sort_values("Data de Vigência Final").reset_index(drop=True),use_container_width=True)
    with st.container():
        st.markdown("### 🔴 Contratos vencidos")
        c25, c26, c27, c28 = st.columns(4)
        c25.metric("Qtd contratos", len(vencidos))
        c26.metric("Valor total", f"R$ {vencidos['valorGlobal'].sum():,.2f}".replace(",", "X").replace(".", ",").replace("X", "."))
        c27.metric("Valor do maior contrato", f"R$ {vencidos['valorGlobal'].max():,.2f}".replace(",", "X").replace(".", ",").replace("X", ".") if not vencidos.empty else "R$ 0,00")
        c28.metric("Média por contrato", f"R$ {vencidos['valorGlobal'].mean():,.2f}".replace(",", "X").replace(".", ",").replace("X", ".") if not vencidos.empty else "R$ 0,00")
        colvencidos_1, colvencidos_2 = st.columns(2)
        numero_contrato = colvencidos_1.multiselect("Número do contrato",sorted(vencidos["numeroContrato"].dropna().unique()))
        fornecedor = colvencidos_2.multiselect("Fornecedor",sorted(vencidos["nomeRazaoSocialFornecedor"].dropna().unique()))
        if numero_contrato:
            vencidos = vencidos[vencidos["numeroContrato"].isin(numero_contrato)]
        if fornecedor:
            vencidos = vencidos[vencidos["nomeRazaoSocialFornecedor"].isin(fornecedor)]
        vencidos.columns = colunas_renomeadas     
        st.dataframe(vencidos.sort_values("Data de Vigência Final").reset_index(drop=True),use_container_width=True)
    
    # ============ ANÁLISE POR CATEGORIA - CONTRATOS VENCENDO ============
    st.divider()
    st.markdown("## 📂 Análises dos contratos próximos do vencimento")
    
    # Combinar todos os contratos em risco
    contratos_risco = pd.concat([v30, v60, v90])
    
    if len(contratos_risco) > 0:
        # Análise por categoria
        cat_risco = contratos_risco.groupby('nomeCategoria').agg({'numeroContrato': 'count', 'valorGlobal': 'sum', 'dataVigenciaFinal': 'min'}).reset_index()
        cat_risco.columns = ['Categoria', 'Quantidade', 'Valor total', 'Data mais próxima']
        cat_risco = cat_risco.sort_values('Quantidade', ascending=False)
        
        # Gráfico de categorias
        col1, col2 = st.columns(2)
        with col1:
            st.markdown("### Quantidade de contratos por categoria")
            top_cat_qtd = cat_risco
            fig_cat_qtd = go.Figure()
            fig_cat_qtd.add_trace(go.Bar(x=top_cat_qtd['Quantidade'], y=top_cat_qtd['Categoria'], orientation='h',
                marker_color='#D32F2F', text=top_cat_qtd['Quantidade'], textposition='auto'))
            fig_cat_qtd.update_layout(xaxis_title="Quantidade de Contratos", yaxis_title="", height=400, yaxis={'categoryorder':'total ascending'})
            st.plotly_chart(fig_cat_qtd, use_container_width=True)
        
        with col2:
            st.markdown("### Valor total por categoria")
            top_cat_valor = cat_risco.nlargest(100, 'Valor total')
            fig_cat_valor = go.Figure()
            fig_cat_valor.add_trace(go.Bar(x=top_cat_valor['Valor total'], y=top_cat_valor['Categoria'], orientation='h',
                marker_color='#00689D', text=top_cat_valor['Valor total'].apply(lambda x: formatar_real(x)), textposition='auto'))
            fig_cat_valor.update_layout(xaxis_title="Valor total (R$)", yaxis_title="", height=400, yaxis={'categoryorder':'total ascending'})
            st.plotly_chart(fig_cat_valor, use_container_width=True)
        
        # Tabela com detalhes
        hoje = pd.Timestamp.today().normalize()

        contratos_display = contratos_risco.copy()
        contratos_display['Dias até vencimento'] = (pd.to_datetime(contratos_display['dataVigenciaFinal']) - hoje).dt.days
        contratos_display['Risco de vencimento'] = contratos_display['Dias até vencimento'].apply(lambda x: '🔴 Crítico' if x <= 30 else '🟡 Atenção' if x <= 90 else '🟢 Controlado')

        contratos_display['valorGlobal'] = contratos_display['valorGlobal'].apply(formatar_real)
        contratos_display['dataVigenciaFinal'] = pd.to_datetime(contratos_display['dataVigenciaFinal']).dt.strftime('%d/%m/%Y')

        contratos_display = contratos_display.rename(columns={'numeroContrato': 'Contrato',
            'nomeCategoria': 'Categoria', 'valorGlobal': 'Valor do contrato', 'dataVigenciaFinal': 'Data final'})
        contratos_display = contratos_display[['Contrato','Categoria','Valor do contrato','Data final','Dias até vencimento','Risco de vencimento']]
        with st.expander("Ver detalhes", expanded=False):
            st.dataframe(contratos_display.sort_values('Dias até vencimento').reset_index(drop=True),
                use_container_width=True)

    else:
        st.success("✅ Não há contratos em risco de vencimento nos próximos 90 dias!")
    
# ==================== ABA 3: ANÁLISES ====================
with tab3:
    st.subheader("Análises dos contratos")

    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Quantidade total de contratos", len(df))
    c2.metric("Contratos vigentes", len(df[df["status"] == "Vigente"]))
    c3.metric("Contratos vencidos", len(df[df["status"] == "Vencido"]))
    c4.metric("Percentual de contratos vigentes", f'{(len(df[df["status"] == "Vigente"]) / len(df) * 100):.1f}%' if len(df) > 0 else "0%")
    
    c5, c6, c7, c8 = st.columns(4)
    c5.metric("Valor total", f"R$ {df['valorGlobal'].sum():,.2f}".replace(",", "X").replace(".", ",").replace("X", "."))
    c6.metric("Valor vigente", f"R$ {df[df['status']=='Vigente']['valorGlobal'].sum():,.2f}".replace(",", "X").replace(".", ",").replace("X", "."))
    c7.metric("Valor vencido", f"R$ {df[df['status']=='Vencido']['valorGlobal'].sum():,.2f}".replace(",", "X").replace(".", ",").replace("X", "."))
    c8.metric("Fornecedores únicos", df["nomeRazaoSocialFornecedor"].nunique())
    st.divider()

    # ============ EVOLUÇÃO TEMPORAL ============
    st.markdown("## Evolução Temporal")
    evolucao = df.groupby("ano").agg(contratos=("numeroContrato", "count"),valor=("valorGlobal", "sum")).reset_index()
    
    col1, col2 = st.columns(2)
    with col1: 
        st.markdown("### Contratos por ano")
        fig=px.bar(evolucao,x="ano",y="contratos",labels={"ano":"Ano","contratos":"Quantidade"},
                    color_discrete_sequence=["#00689D"])
        fig.update_xaxes(tickangle=0,tickmode="linear",dtick=1)
        st.plotly_chart(fig,use_container_width=True)
        st.caption(f"Média anual: {evolucao['contratos'].mean():.0f} contratos")

    with col2:
        st.markdown("### Valor contratado por ano")
        fig_valor = px.bar(evolucao, x="ano", y="valor", labels={"ano": "Ano", "valor": "Valor contratado (R$)"},
                           color_discrete_sequence=["#00689D"])
        fig_valor.update_xaxes(tickangle=0, tickmode="linear", dtick=1)
        fig_valor.update_yaxes(tickprefix="R$ ", separatethousands=True)
        st.plotly_chart(fig_valor, use_container_width=True)
        st.caption(f"Média anual: R$ {evolucao['valor'].mean():,.2f}".replace(",", "X").replace(".", ",").replace("X", "."))
    
    # Comparação ano a ano
    evolucao["var_contratos_%"] = evolucao["contratos"].pct_change() * 100
    evolucao["var_valor_%"] = evolucao["valor"].pct_change() * 100
    evolucao["ticket_medio"] = evolucao["valor"] / evolucao["contratos"]
    
    # Renomear colunas
    evolucao_display = evolucao.copy()
    evolucao_display.columns = ['Ano', 'Contratos', 'Valor', 'Variação da quantidade de contratos em relação ao ano anterior (%)', 
                                'Variação dos valores dos contratos em relação ao ano anterior %', 'Ticket médio']
    
    with st.expander("Ver detalhes", expanded=False):
        st.dataframe(evolucao_display.style.format({"Valor": "R$ {:,.2f}",
        "Variação da quantidade de contratos em relação ao ano anterior (%)": "{:.1f}%",
        "Variação dos valores dos contratos em relação ao ano anterior %": "{:.1f}%",
        "Ticket médio": "R$ {:,.2f}"}), use_container_width=True)

    st.divider()

    # ============ ANÁLISE POR STATUS ============
    st.markdown("## Análise por Status dos Contratos")
    
    status_analise = df.groupby("status").agg(quantidade=("numeroContrato", "count"),
            valor_total=("valorGlobal", "sum"), valor_medio=("valorGlobal", "mean"),
            valor_minimo=("valorGlobal", "min"), valor_maximo=("valorGlobal", "max")).reset_index()
    
    col1, col2, col3 = st.columns(3)
    
    with col1:
        st.markdown("### Quantidade de contratos por status")
        st.plotly_chart(px.bar(status_analise,x="status",y="quantidade", color_discrete_sequence=["#00689D"],
                               labels={"status":"Status","quantidade":"Quantidade"}),use_container_width=True)

    with col2:
        st.markdown("### Valor total dos contratos por status")
        fig_total = px.bar(status_analise,x="status",y="valor_total",labels={"status":"Status","valor_total":"Valor total (R$)"},
        color_discrete_sequence=["#00689D"])
        fig_total.update_yaxes(tickprefix="R$ ",separatethousands=True)
        st.plotly_chart(fig_total,use_container_width=True)

    with col3:
        st.markdown("### Ticket médio dos contratos por status")
        fig_medio = px.bar(status_analise,x="status",y="valor_medio",labels={"status":"Status","valor_medio":"Valor médio (R$)"},
                           color_discrete_sequence=["#00689D"])
        fig_medio.update_yaxes(tickprefix="R$ ",separatethousands=True)
        st.plotly_chart(fig_medio,use_container_width=True)
    
    status_analise.columns = ['Status', 'Quantidade de contratos', 'Valor total', 'Valor médio', 'Valor mínimo', 'Valor máximo']
        
    with st.expander("Ver detalhes", expanded=False):
        st.dataframe(status_analise.style.format({"Valor total": "R$ {:,.2f}", "Valor médio": "R$ {:,.2f}",
            "Valor mínimo": "R$ {:,.2f}", "Valor máximo": "R$ {:,.2f}"}), use_container_width=True)
    st.divider()

    # ============ ANÁLISE POR CATEGORIA ============
    st.markdown("## Análise por Categoria")
    cat_analise = df.groupby("nomeCategoria").agg(quantidade=("numeroContrato", "count"),
        valor_total=("valorGlobal", "sum"), valor_medio=("valorGlobal", "mean"),
        vigentes=("status", lambda x: (x == "Vigente").sum()),
        vencidos=("status", lambda x: (x == "Vencido").sum())).reset_index().sort_values("valor_total", ascending=False)
    cat_analise["perc_vigentes"] = (cat_analise["vigentes"] / cat_analise["quantidade"] * 100).round(1)
    col1, col2 = st.columns(2)
    with col1:
        st.markdown("### Quantidade de contratos por categoria")
        top_cat_qtd = cat_analise.sort_values("quantidade")
        st.plotly_chart(px.bar(top_cat_qtd,x="quantidade",y="nomeCategoria",orientation="h", color_discrete_sequence=["#00689D"],
                               labels={"quantidade":"Quantidade","nomeCategoria":"Categoria"}),
                               use_container_width=True)
    with col2:
        st.markdown("### Valor dos contratos por categoria")
        top_cat_valor = cat_analise.sort_values("valor_total")
        fig_valor = px.bar(top_cat_valor,x="valor_total",y="nomeCategoria",orientation="h", 
                           labels={"valor_total":"Valor (R$)","nomeCategoria":"Categoria"},
                           color_discrete_sequence=["#00689D"])
        fig_valor.update_xaxes(tickprefix="R$ ",separatethousands=True)
        st.plotly_chart(fig_valor,use_container_width=True)

    # Renomear colunas
    cat_display = cat_analise.copy()
    cat_display.columns = ['Categoria', 'Quantidade de contratos', 'Valor total', 'Valor médio', 'Vigentes', 'Vencidos', '% Vigentes']
    with st.expander("Ver detalhes", expanded=False):
        st.dataframe(cat_display.reset_index(drop=True).style.format({"Valor total": "R$ {:,.2f}","Valor médio": "R$ {:,.2f}",
            "% Vigentes": "{:.1f}%"}), use_container_width=True)
    st.divider()

    # ============ ANÁLISE POR FORNECEDOR ============
    st.markdown("## Análise por Fornecedor")
    
    forn_analise = df.groupby("nomeRazaoSocialFornecedor").agg(quantidade=("numeroContrato", "count"),
        valor_total=("valorGlobal", "sum"), valor_medio=("valorGlobal", "mean"), vigentes=("status", lambda x: (x == "Vigente").sum()),
        categorias=("nomeCategoria", "nunique")).reset_index().sort_values("valor_total", ascending=False)
    
    forn_analise["participacao_%"] = (forn_analise["valor_total"] / forn_analise["valor_total"].sum() * 100).round(2)
    forn_analise.columns = ['Fornecedor', 'Quantidade', 'Valor Total', 'Valor Médio', 'Vigentes', 'Categorias', 'Frequência relativa %']
    
    # Função para quebrar linhas longas
    def quebrar_linha(texto, max_chars=40):
        if len(texto) <= max_chars:
            return texto
        palavras = texto.split()
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
        return "\n".join(linhas[:2]) 
    
    col1, col2 = st.columns(2)
    with col1:
        st.markdown("### Quantidade de contratos por categoria")
        top_forn_qtd = forn_analise.copy()
        top_forn_qtd["nome_curto"] = top_forn_qtd["Fornecedor"].apply(quebrar_linha)
        top_forn_qtd = top_forn_qtd.head(15).sort_values("Quantidade")
        st.plotly_chart(px.bar(top_forn_qtd.head(15),x="Quantidade",y="nome_curto",orientation="h", color_discrete_sequence=["#00689D"],
                               labels={"quantidade":"Quantidade","nome_curto":"Fornecedor"}),
                               use_container_width=True)
        
    with col2:
        st.markdown("### Valor dos contratos por fornecedor")
        top_forn = forn_analise.copy()
        top_forn["nome_curto"] = top_forn["Fornecedor"].apply(quebrar_linha)
        top_forn = top_forn.head(15).sort_values("Valor Total")
        fig_forn_valor = px.bar(top_forn,x="Valor Total",y="nome_curto",orientation="h",
                                labels={"Valor Total":"Valor (R$)","nome_curto":"Fornecedor"},
                                color_discrete_sequence=["#00689D"])
        fig_forn_valor.update_xaxes(tickprefix="R$ ",separatethousands=True)
        st.plotly_chart(fig_forn_valor,use_container_width=True)
    
    # Detalhamento completo por fornecedor
    with st.expander("Ver detalhes", expanded=False):
        st.dataframe(forn_analise.reset_index(drop=True).style.format({"Valor Total": "R$ {:,.2f}",
            "Valor Médio": "R$ {:,.2f}", "Frequência relativa %": "{:.2f}%"}), use_container_width=True)
    st.divider()

    # ============ ANÁLISE POR MODALIDADE ============
    st.markdown("## Análise por Modalidade de Compra")
    mod_analise = df.groupby("nomeModalidadeCompra").agg(quantidade=("numeroContrato", "count"), valor_total=("valorGlobal", "sum"), 
        valor_medio=("valorGlobal", "mean")).reset_index().sort_values("valor_total", ascending=False)
    mod_analise["participacao_%"] = (mod_analise["valor_total"] / mod_analise["valor_total"].sum() * 100).round(2)
    mod_analise.columns = ['Modalidade', 'Quantidade', 'Valor total', 'Valor médio', 'Frequência relativa %']
    col1, col2 = st.columns(2)
    with col1:
        st.markdown("### Distribuição por Modalidade")
        st.plotly_chart(px.bar(mod_analise,x="Modalidade",y="Quantidade",color_discrete_sequence=["#00689D"],
                               labels={"Modalidade":"Modalidade","Quantidade":"Quantidade"}),use_container_width=True)
    with col2:
        st.markdown("### Valor por Modalidade")
        fig_mod = px.bar(mod_analise,x="Modalidade",y="Valor total",labels={"Modalidade":"Modalidade","Valor total":"Valor (R$)"},
                         color_discrete_sequence=["#00689D"])
        fig_mod.update_yaxes(tickprefix="R$ ",separatethousands=True)
        st.plotly_chart(fig_mod,use_container_width=True)
    with st.expander("Ver detalhes", expanded=False):
        st.dataframe(mod_analise.reset_index(drop=True).style.format({"Valor total": "R$ {:,.2f}",
            "Valor médio": "R$ {:,.2f}", "Frequência relativa %": "{:.2f}%"}), use_container_width=True)
    st.divider()

    # ============ ANÁLISE POR TIPO ============
    st.markdown("## Análise por Tipo de Contrato")
    tipo_analise = df.groupby("nomeTipo").agg(quantidade=("numeroContrato", "count"), valor_total=("valorGlobal", "sum"),
        valor_medio=("valorGlobal", "mean")).reset_index().sort_values("valor_total", ascending=False)
    tipo_analise.columns = ['Tipo', 'Quantidade', 'Valor total', 'Valor médio']
    col1, col2 = st.columns(2)
    with col1:
        st.markdown("### Quantidade por Tipo")
        st.plotly_chart(px.bar(tipo_analise,x="Tipo",y="Quantidade",labels={"Tipo":"Tipo","Quantidade":"Quantidade"},
                               color_discrete_sequence=["#00689D"]),use_container_width=True)
    with col2:
        st.markdown("### Valor por Tipo")
        fig_tipo = px.bar(tipo_analise,x="Tipo",y="Valor total",labels={"Tipo":"Tipo","Valor total":"Valor (R$)"},
        color_discrete_sequence=["#00689D"])
        fig_tipo.update_yaxes(tickprefix="R$ ",separatethousands=True)
        st.plotly_chart(fig_tipo,use_container_width=True)
    with st.expander("Ver detalhes", expanded=False):
        st.dataframe(tipo_analise.reset_index(drop=True).style.format({"Valor total": "R$ {:,.2f}",
            "Valor médio": "R$ {:,.2f}"}), use_container_width=True)
    st.divider()

    # ============ ANÁLISE DE UNIDADES ============
    st.markdown("## Análise por Unidade Realizadora")
    
    unid_analise = df.groupby("nomeUnidadeRealizadoraCompra").agg(quantidade=("numeroContrato", "count"),
        valor_total=("valorGlobal", "sum"), fornecedores=("nomeRazaoSocialFornecedor", "nunique"),
        categorias=("nomeCategoria", "nunique")).reset_index().sort_values("valor_total", ascending=False)
    
    unid_analise.columns = ['Unidade', 'Quantidade', 'Valor total', 'Fornecedores', 'Categorias']
    col1, col2 = st.columns(2)
    with col1:
        st.markdown("### Quantidade de contratos por unidade")
        top_unid = unid_analise.copy()
        top_unid["nome_curto"] = top_unid["Unidade"].apply(quebrar_linha)
        top_unid = top_unid.sort_values("Quantidade")
        st.plotly_chart(px.bar(top_unid,x="Quantidade",y="nome_curto",orientation="h",color_discrete_sequence=["#00689D"],
                               labels={"Quantidade":"Quantidade","nome_curto":"Unidade"}),use_container_width=True)
    with col2:
        st.markdown("### Valor dos contratos por unidade")
        top_unid_valor = unid_analise.copy()
        top_unid_valor["nome_curto"] = top_unid_valor["Unidade"].apply(quebrar_linha)
        top_unid_valor = top_unid_valor.sort_values("Valor total")
        fig_unid = px.bar(top_unid_valor,x="Valor total",y="nome_curto",orientation="h",color_discrete_sequence=["#00689D"],
                          labels={"Valor total":"Valor (R$)","nome_curto":"Unidade"})
        fig_unid.update_xaxes(tickprefix="R$ ",separatethousands=True); st.plotly_chart(fig_unid,use_container_width=True)

    with st.expander("Ver detalhes", expanded=False):
        st.dataframe(unid_analise.style.format({"Valor total": "R$ {:,.2f}"}), use_container_width=True)
    st.divider()

    # ============ ANÁLISE CRUZADA ============
    st.markdown("## Análises comparativas por ano")
    
    st.markdown("### Categoria × Ano")
    cat_ano = pd.crosstab(df["nomeCategoria"], df["ano"], values=df["valorGlobal"], aggfunc="sum").fillna(0)

    fig_cat_ano = go.Figure()
    for categoria in cat_ano.index: 
        fig_cat_ano.add_bar(x=cat_ano.columns, y=cat_ano.loc[categoria], name=categoria)
    fig_cat_ano.update_layout(barmode="group", xaxis_title="Ano", yaxis_title="Valor (R$)", height=450)
    st.plotly_chart(fig_cat_ano, use_container_width=True)

    cat_ano_display = cat_ano.copy()
    for col in cat_ano_display.columns: 
        cat_ano_display[col] = cat_ano_display[col].apply(lambda x: f"R$ {x:,.2f}".replace(",", "X").replace(".", ",").replace("X", "."))
    with st.expander("Ver detalhes", expanded=False): 
        st.dataframe(cat_ano_display, use_container_width=True)

    st.markdown("### Modalidade × Ano")
    mod_ano = pd.crosstab(df["nomeModalidadeCompra"], df["ano"], values=df["valorGlobal"], aggfunc="sum").fillna(0)

    fig_mod_ano = go.Figure()
    for modalidade in mod_ano.index: 
        fig_mod_ano.add_bar(x=mod_ano.columns, y=mod_ano.loc[modalidade], name=modalidade)
    fig_mod_ano.update_layout(barmode="group", xaxis_title="Ano", yaxis_title="Valor (R$)", height=450)
    st.plotly_chart(fig_mod_ano, use_container_width=True)
    mod_ano_display = mod_ano.copy()
    for col in mod_ano_display.columns: 
        mod_ano_display[col] = mod_ano_display[col].apply(lambda x: f"R$ {x:,.2f}".replace(",", "X").replace(".", ",").replace("X", "."))
    with st.expander("Ver detalhes", expanded=False): 
        st.dataframe(mod_ano_display, use_container_width=True)

# ==================== ABA 4: VISÃO GERAL & FILTROS ====================
with tab4:
    st.header("Análise Financeira")
    subtab1_fin, subtab2_fin, subtab3_fin = st.tabs(["Análises", "Perfil dos Gestores", "Análise por Centro de Custos"])
    with subtab1_fin:    
        col1, col2, col3 = st.columns(3)
        with col1:
            anos_disponiveis = sorted(df_resumo['Ano'].unique())
            ano_selecionado = st.multiselect("Ano", options=anos_disponiveis, default=[], key="ano_tab1")
        with col2:
            gestores_disponiveis = sorted([g for g in df_resumo['Gestor(a)'].unique() if g != 'Não informado'])
            gestor_selecionado = st.multiselect("Gestor", options=['Todos'] + gestores_disponiveis, default=[], key="gestor_tab1")
        with col3:
            centros_disponiveis = sorted([c for c in df_resumo['Centro de Custo'].unique() if c != 'Não informado'])
            centro_selecionado = st.multiselect("Centro de Custo", options=['Todos'] + centros_disponiveis, default=[], key="centro_tab1")

        df_filtered = df_resumo.copy()
        if ano_selecionado:
            df_filtered = df_filtered[df_filtered['Ano'].isin(ano_selecionado)]
        if gestor_selecionado and 'Todos' not in gestor_selecionado:
            df_filtered = df_filtered[df_filtered['Gestor(a)'].isin(gestor_selecionado)]
        if centro_selecionado and 'Todos' not in centro_selecionado:
            df_filtered = df_filtered[df_filtered['Centro de Custo'].isin(centro_selecionado)]
        
        st.markdown("---")
        
        # Calcular indicadores principais
        limite_gastos = df_filtered['Limite'].sum()
        valor_pre_empenhado = df_filtered['Pré-empenhado'].sum()
        valor_empenhado = df_filtered['Empenhado'].sum()
        valor_pago = df_filtered['Valor Empenhos Pagos'].sum()
        limite_disponivel = limite_gastos - valor_pre_empenhado - valor_empenhado
        valor_a_pagar = valor_empenhado - valor_pago
        valor_a_pagar = 0.0 if abs(valor_a_pagar) <= 1e-9 else valor_a_pagar
        
        # Mostrar indicadores principais em cards
        st.subheader("Indicadores Financeiros Principais")
        col1, col2, col3, col4 = st.columns(4)
        with col1:
            st.metric("Limite de Gastos", formatar_real(limite_gastos), help="Valor Limite Disponível")
            st.metric("Valor Empenhado", formatar_real(valor_empenhado), help="Soma dos empenhos totais")
        with col2:
            st.metric("Valor Pago", formatar_real(valor_pago), help="Soma dos valores pagos")
            st.metric("Valor a Pagar", formatar_real(valor_a_pagar), help="Empenhado - Pago")
        with col3:
            st.metric("Pré-Empenhado", formatar_real(valor_pre_empenhado), help="Valor de pré-empenhos a empenhar")
            st.metric("Limite Disponível", formatar_real(limite_disponivel), help="Limite - Pré-Empenhos - Empenhos")
        with col4:
            perc_execucao = (valor_empenhado / limite_gastos * 100) if limite_gastos > 0 else 0
            st.metric("Execução Orçamentária", formatar_percentual(perc_execucao), help="Percentual do limite que foi empenhado")
            perc_pagamento = (valor_pago / valor_empenhado * 100) if valor_empenhado > 0 else 0
            st.metric("Taxa de Pagamento", formatar_percentual(perc_pagamento), help="Percentual do empenhado que foi pago")
        
        st.markdown("---")
        
        col1, col2 = st.columns(2)
        with col1:
            st.subheader("Evolução temporal")
            evolucao_ano = df_filtered.groupby('Ano').agg({'Limite': 'sum', 'Empenhado': 'sum', 
                                                           'Valor Empenhos Pagos': 'sum'}).reset_index()
            fig_evolucao = go.Figure()
            fig_evolucao.add_trace(go.Bar(name='Limite', x=evolucao_ano['Ano'], y=evolucao_ano['Limite'],
                marker_color='lightblue'))
            fig_evolucao.add_trace(go.Bar(name='Empenhado', x=evolucao_ano['Ano'], y=evolucao_ano['Empenhado'],
                                          marker_color='#0068c9'))
            fig_evolucao.add_trace(go.Bar(name='Pago', x=evolucao_ano['Ano'], y=evolucao_ano['Valor Empenhos Pagos'],
                marker_color='#28a745')) 
            fig_evolucao.update_layout(xaxis_title="Ano", yaxis_title="Valor (R$)", barmode='group', height=400)
            st.plotly_chart(fig_evolucao, use_container_width=True)
        with col2:
            st.subheader("Empenhado vs Pago")
            if valor_empenhado > 0:
                perc_pago = (valor_pago / valor_empenhado * 100) if valor_empenhado > 0 else 0
                perc_a_pagar = (valor_a_pagar / valor_empenhado * 100) if valor_empenhado > 0 else 0
                import plotly.graph_objects as go
                fig_emp_pago=go.Figure()
                fig_emp_pago.add_trace(go.Bar(name='Pago',x=[valor_pago],y=['Empenho'],orientation='h',
                                              marker=dict(color='#00689D'),text=[f"Valor pago<br>{formatar_real(valor_pago)}<br>{perc_pago:.1f}%"],
                                              textposition='inside',textfont=dict(color='white',size=14),
                                              hovertemplate=f'Pago: {formatar_real(valor_pago)}<br>{perc_pago:.1f}%<extra></extra>'))
                fig_emp_pago.add_trace(go.Bar(name='A Pagar',x=[valor_a_pagar],y=['Empenho'],orientation='h',
                marker=dict(color='#E4F0F3'),hovertemplate=f'A Pagar: {formatar_real(valor_a_pagar)}<br>{perc_a_pagar:.1f}%<extra></extra>'))
                fig_emp_pago.update_layout(barmode='stack',height=400,showlegend=True,margin=dict(l=20,r=240,t=20,b=20),
                legend=dict(orientation="h",yanchor="bottom",y=1.05,xanchor="right",x=1),
                xaxis=dict(range=[0,valor_empenhado*1.15],tickformat=",.0f",title=""),yaxis=dict(title=""))
                fig_emp_pago.add_vline(x=valor_empenhado,line_dash="dot",line_color="gray",line_width=2)
                fig_emp_pago.add_annotation(x=1.05,y=0.5,xref="paper",yref="paper",
                                            text=f"<b>Total empenhado</b><br>{formatar_real(valor_empenhado)}",
                                            showarrow=False,align="left",font=dict(size=12,color="#4a4a4a"))
                st.plotly_chart(fig_emp_pago,use_container_width=True)
            else:
                st.info("Sem dados de empenhos para exibir")
        
        # Tabela resumo
        st.subheader("Informações financeiras por ano")
        resumo_ano = df_filtered.groupby('Ano').agg({'Limite': 'sum', 'Pré-empenhado': 'sum', 
        'Empenhado': 'sum', 'Valor Empenhos Pagos': 'sum'}).reset_index()
        resumo_ano['Disponível'] = (resumo_ano['Limite'] - resumo_ano['Pré-empenhado'] - resumo_ano['Empenhado'])
        resumo_ano['A Pagar'] = resumo_ano['Empenhado'] - resumo_ano['Valor Empenhos Pagos']
        resumo_ano['% Execução'] = resumo_ano.apply(lambda row: (row['Empenhado'] / row['Limite'] * 100) if row['Limite'] > 0 else 0,
            axis=1)
        # Formatar valores
        resumo_display = resumo_ano.copy()
        for col in ['Limite', 'Pré-empenhado', 'Empenhado', 'Valor Empenhos Pagos', 'Disponível', 'A Pagar']:
            resumo_display[col] = resumo_display[col].apply(formatar_real)
        resumo_display['% Execução'] = resumo_display['% Execução'].apply(formatar_percentual)
        def marcar_negativo(v):
            try:
                return 'color:red' if float(str(v).replace('.','').replace(',','.').replace('R$','').strip())<0 else ''
            except:
                return ''
        st.dataframe(resumo_display.style.applymap(marcar_negativo,subset=['Disponível']),use_container_width=True)
    with subtab2_fin:
        st.header("Perfil dos Gestores")
        col1_f, col2_f, col3_f = st.columns(3)
        with col1_f:
            ano_gest = st.multiselect("Ano", options=anos_disponiveis, 
                                    default=ano_selecionado if ano_selecionado else [], key="ano_gest")
        with col2_f:
            gestor_gest = st.multiselect("Gestor", options=['Todos'] + gestores_disponiveis, 
                                        default=gestor_selecionado if gestor_selecionado else [], key="gestor_gest")
        with col3_f:
            centro_gest = st.multiselect("Centro de Custo", options=['Todos'] + centros_disponiveis, 
                                     default=centro_selecionado if centro_selecionado else [], key="centro_gest")

        df_gestores = df_resumo.copy()
        if ano_gest:
            df_gestores = df_gestores[df_gestores['Ano'].isin(ano_gest)]
        if gestor_gest and 'Todos' not in gestor_gest:
            df_gestores = df_gestores[df_gestores['Gestor(a)'].isin(gestor_gest)]
        if centro_gest and 'Todos' not in centro_gest:
            df_gestores = df_gestores[df_gestores['Centro de Custo'].isin(centro_gest)]
        df_gestores = df_gestores[df_gestores['Gestor(a)'] != 'Não informado'].copy()
        st.markdown("---")
        
        if len(df_gestores) == 0:
            st.warning("Não há dados de gestores para os filtros selecionados.")
        else:
            gestores_agg = df_gestores.groupby('Gestor(a)').agg({'Limite': 'sum', 'Empenhado': 'sum',
                'Valor Empenhos Pagos': 'sum', 'Pré-empenhado': 'sum'}).reset_index()
            gestores_agg['Disponível'] = (gestores_agg['Limite'] - gestores_agg['Pré-empenhado'] - gestores_agg['Empenhado'])
            gestores_agg['% Execução'] = gestores_agg.apply(lambda row: (row['Empenhado'] / row['Limite'] * 100) if row['Limite'] > 0 else 0, axis=1)
            col1, col2, col3 = st.columns(3)
            with col1:
                st.metric("Quantidade de Gestores", len(gestores_agg))
            with col2:
                st.metric("Total empenhado", formatar_real(gestores_agg['Empenhado'].sum()))
            with col3:
                st.metric("Total pago", formatar_real(gestores_agg['Valor Empenhos Pagos'].sum()))
            st.markdown("---")
            
            st.subheader("Empenhado x Pago por Gestor(a)")
            gestores_base = gestores_agg.groupby("Gestor(a)", as_index=False)[["Empenhado","Valor Empenhos Pagos"]].sum()
            opcoes_gestor = [3,5,10,15,20,25,30]
            index_gestor = 1 if len(gestores_base) >= 10 else 0
            top_gestor = st.selectbox("Selecione a quantidade de gestores para exibir:", opcoes_gestor, index=index_gestor, key="top_gestor_execucao")
            gestores_top = gestores_base.nlargest(top_gestor, "Empenhado").sort_values("Empenhado", ascending=True)
            fig = go.Figure()
            fig.add_trace(go.Bar(name="Empenhado", y=gestores_top["Gestor(a)"], x=gestores_top["Empenhado"], orientation="h", marker_color="#0068c9", text=gestores_top["Empenhado"].apply(formatar_real), textposition="auto"))
            fig.add_trace(go.Bar(name="Pago", y=gestores_top["Gestor(a)"], x=gestores_top["Valor Empenhos Pagos"], orientation="h", marker_color="#28a745", text=gestores_top["Valor Empenhos Pagos"].apply(formatar_real), textposition="auto"))
            fig.update_layout(barmode="group", height=700 + len(gestores_top) * 35, xaxis_title="Valor (R$)", yaxis_title=None, legend_title=None, hovermode="y unified", separators=",.")
            st.plotly_chart(fig, use_container_width=True)
                                        
            st.markdown("---")
            st.subheader("Valores por ano")
            df_gestores['A Pagar'] = df_gestores['Empenhado'] - df_gestores['Valor Empenhos Pagos']
            gestores_ano_agg = df_gestores.groupby(['Ano', 'Gestor(a)']).agg({'Limite': 'sum', 'Empenhado': 'sum',
                'Valor Empenhos Pagos': 'sum', 'Pré-empenhado': 'sum','A Pagar': 'sum'}).reset_index()
            gestores_ano_agg['Disponível'] = (gestores_ano_agg['Limite'] - gestores_ano_agg['Pré-empenhado'] - gestores_ano_agg['Empenhado'])
            #gestores_ano_agg['% Execução'] = gestores_ano_agg.apply(lambda row: (row['Empenhado'] / row['Limite'] * 100) if row['Limite'] > 0 else 0, axis=1)
            gestores_display = gestores_ano_agg.copy()
            for col in ['Limite', 'Empenhado', 'Valor Empenhos Pagos', 'Pré-empenhado', 'Disponível', 'A Pagar']:
                gestores_display[col] = gestores_display[col].apply(formatar_real)
            #gestores_display['% Execução'] = gestores_display['% Execução'].apply(formatar_percentual)
            st.dataframe(gestores_display, use_container_width=True, height=400)
    with subtab3_fin:
        st.header("Análise por Centro de Custos")
        col1_f, col2_f, col3_f = st.columns(3)
        with col1_f:
            ano_centro = st.multiselect("Ano", options=anos_disponiveis, 
                                        default=ano_selecionado if ano_selecionado else [], key="ano_centro")
        with col2_f:
            gestor_centro = st.multiselect("Gestor", options=['Todos'] + gestores_disponiveis, 
                                        default=gestor_selecionado if gestor_selecionado else [], key="gestor_centro")
        with col3_f:
            centro_centro = st.multiselect("Centro de Custo", options=['Todos'] + centros_disponiveis, 
                                        default=centro_selecionado if centro_selecionado else [], key="centro_centro")
        
        df_centros = df_resumo.copy()
        if ano_centro:
            df_centros = df_centros[df_centros['Ano'].isin(ano_centro)]
        if gestor_centro and 'Todos' not in gestor_centro:
            df_centros = df_centros[df_centros['Gestor(a)'].isin(gestor_centro)]
        if centro_centro and 'Todos' not in centro_centro:
            df_centros = df_centros[df_centros['Centro de Custo'].isin(centro_centro)]
        df_centros = df_centros[df_centros['Centro de Custo'] != 'Não informado'].copy()
        
        st.markdown("---")
        
        if len(df_centros) == 0:
            st.warning("Não há dados de centros de custo para os filtros selecionados.")
        else:
            centros_agg = df_centros.groupby('Centro de Custo').agg({'Limite': 'sum', 'Empenhado': 'sum',
                'Valor Empenhos Pagos': 'sum', 'Pré-empenhado': 'sum'}).reset_index()
            centros_agg['Disponível'] = (centros_agg['Limite'] - centros_agg['Pré-empenhado'] - centros_agg['Empenhado'])
            centros_agg['A Pagar'] = centros_agg['Empenhado'] - centros_agg['Valor Empenhos Pagos']
            centros_agg['% Execução'] = (centros_agg['Empenhado'] / centros_agg['Limite'] * 100)

            col1, col2, col3 = st.columns(3)
            with col1:
                st.metric("Quantidade de centro de custos", len(centros_agg))
            with col2:
                st.metric("Total empenhado", formatar_real(centros_agg['Empenhado'].sum()))
            with col3:
                st.metric("Total pago", formatar_real(centros_agg['Valor Empenhos Pagos'].sum()))
            st.markdown("---")

            st.subheader("Empenhado x Pago por Centro de Custos")
            centros_base = centros_agg.groupby("Centro de Custo", as_index=False)[["Empenhado","Valor Empenhos Pagos"]].sum()
            opcoes_gestor = [3,5,10,15,20,25,30]
            index_gestor = 1 if len(centros_base) >= 10 else 0
            top_gestor = st.selectbox("Selecione a quantidade de centros para exibir:", opcoes_gestor, index=index_gestor, key="top_centros_execucao")
            centros_top = centros_base.nlargest(top_gestor, "Empenhado").sort_values("Empenhado", ascending=True)
            fig = go.Figure()
            fig.add_trace(go.Bar(name="Empenhado", y=centros_top["Centro de Custo"], x=centros_top["Empenhado"], orientation="h", marker_color="#0068c9", text=centros_top["Empenhado"].apply(formatar_real), textposition="auto"))
            fig.add_trace(go.Bar(name="Pago", y=centros_top["Centro de Custo"], x=centros_top["Valor Empenhos Pagos"], orientation="h", marker_color="#28a745", text=centros_top["Valor Empenhos Pagos"].apply(formatar_real), textposition="auto"))
            fig.update_layout(barmode="group", height=700 + len(centros_top) * 35, xaxis_title="Valor (R$)", yaxis_title=None, legend_title=None, hovermode="y unified", separators=",.")
            st.plotly_chart(fig, use_container_width=True)
                                        
            st.markdown("---")
            st.subheader("Valores por ano")
            df_centros['A Pagar'] = df_centros['Empenhado'] - df_centros['Valor Empenhos Pagos']
            centros_ano_agg = df_centros.groupby(['Ano', 'Centro de Custo']).agg({'Limite': 'sum', 'Empenhado': 'sum',
                'Valor Empenhos Pagos': 'sum', 'Pré-empenhado': 'sum', 'A Pagar': 'sum'}).reset_index()
            centros_ano_agg['Disponível'] = (centros_ano_agg['Limite'] - centros_ano_agg['Pré-empenhado'] - centros_ano_agg['Empenhado'])
            #centros_ano_agg['% Execução'] = centros_ano_agg.apply(lambda row: (row['Empenhado'] / row['Limite'] * 100) if row['Limite'] > 0 else 0, axis=1)
            centros_display = centros_ano_agg.copy()
            for col in ['Limite', 'Empenhado', 'Valor Empenhos Pagos', 'Pré-empenhado', 'Disponível', 'A Pagar']:
                centros_display[col] = centros_display[col].apply(formatar_real)
            #centros_display['% Execução'] = centros_display['% Execução'].apply(formatar_percentual)
            st.dataframe(centros_display, use_container_width=True, height=400)            

# ==================== ABA 5: DADOS ORÇAMENTÁRIOS ====================
with tab5:
    st.header("Dados Orçamentários")
    subtab1_orc, subtab2_orc, subtab3_orc = st.tabs(["Empenhos", "Pré-Empenhos", "Restos a Pagar"])
    
    # ==================== SUB-ABA 1: EMPENHOS ====================
    with subtab1_orc:
        st.subheader("Empenhos")
        if len(df_empenhos) == 0:
            st.warning("Dados de empenhos não disponíveis.")
        else:
            col1_f, col2_f, col3_f = st.columns(3)
            with col1_f:
                if 'Ano' in df_empenhos.columns:
                    anos_emp = sorted(df_empenhos['Ano'].dropna().unique().tolist())
                    ano_emp = st.multiselect("Ano", options=anos_emp, default=[], key="ano_emp")
            with col2_f:
                if 'Favorecido' in df_empenhos.columns:
                    favorecidos = sorted([f for f in df_empenhos['Favorecido'].unique() if f != 'Não informado'][:100])
                    favorecido_emp = st.selectbox("Favorecido", options=['Todos'] + favorecidos, key="fav_emp")
            with col3_f:
                if 'Grupo' in df_empenhos.columns:
                    grupos = sorted(df_empenhos['Grupo'].dropna().unique().tolist())
                    grupo_emp = st.multiselect("Grupo", options=grupos, default=[], key="grupo_emp")
            
            df_empenhos_filtered = df_empenhos.copy()
            if 'Ano' in df_empenhos.columns and ano_emp:
                df_empenhos_filtered = df_empenhos_filtered[df_empenhos_filtered['Ano'].isin(ano_emp)]
            if 'Favorecido' in df_empenhos.columns and favorecido_emp != 'Todos':
                df_empenhos_filtered = df_empenhos_filtered[df_empenhos_filtered['Favorecido'] == favorecido_emp]
            if 'Grupo' in df_empenhos.columns and grupo_emp:
                df_empenhos_filtered = df_empenhos_filtered[df_empenhos_filtered['Grupo'].isin(grupo_emp)]
            st.markdown("---")

            col1, col2, col3 = st.columns(3)
            with col1:
                st.metric("Quantidade de registro de empenhos", f"{len(df_empenhos_filtered):,}".replace(",", "."))
            with col2:
                if 'Valor Empenhado' in df_empenhos_filtered.columns:
                    st.metric("Valor empenhado total", formatar_real(df_empenhos_filtered['Valor Empenhado'].sum()))
            with col3:
                if 'Valor Empenhado' in df_empenhos_filtered.columns:
                    valor_medio = df_empenhos_filtered['Valor Empenhado'].mean()
                    st.metric("Valor empenhado Médio", formatar_real(valor_medio))
            
            st.markdown("---")

            st.subheader("Dados")
            st.dataframe(df_empenhos_filtered, use_container_width=True)
            buffer = io.BytesIO()
            with pd.ExcelWriter(buffer, engine="openpyxl") as writer:
                df_empenhos_filtered.to_excel(writer, index=False, sheet_name="Empenhos")
            buffer.seek(0)
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            st.download_button(label="⬇️ Baixar dados", data=buffer, file_name=f"Dados empenhos {timestamp}.xlsx",
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")
    
    # ==================== SUB-ABA 2: PRÉ-EMPENHOS ====================
    with subtab2_orc:
        st.subheader("Pré-Empenhos")      
        if len(df_pre_empenhos) == 0:
            st.warning("Dados de pré-empenhos não disponíveis.")
        else:
            col1_f, col2_f, col3_f = st.columns(3)
            with col1_f:
                if 'Ano' in df_pre_empenhos.columns:
                    anos_emp = sorted(df_pre_empenhos['Ano'].dropna().unique().tolist())
                    ano_emp = st.multiselect("Ano", options=anos_emp, default=[], key="ano_pre_emp")
            with col2_f:
                if 'Natureza' in df_pre_empenhos.columns:
                    natureza = sorted([f for f in df_pre_empenhos['Natureza'].unique() if f != 'Não informado'][:100])
                    natureza_emp = st.multiselect("Natureza", options=natureza, default=[], key="fav_pre_emp")
            with col3_f:
                if 'Grupo' in df_pre_empenhos.columns:
                    grupos = sorted(df_pre_empenhos['Grupo'].dropna().unique().tolist())
                    grupo_emp = st.multiselect("Grupo", options=grupos, default=[], key="grupo_pre_emp")
            
            df_pre_empenhos_filtered = df_pre_empenhos.copy()
            if 'Ano' in df_pre_empenhos.columns and ano_emp:
                df_pre_empenhos_filtered = df_pre_empenhos_filtered[df_pre_empenhos_filtered['Ano'].isin(ano_emp)]
            if 'Natureza' in df_pre_empenhos.columns and natureza_emp:
                df_pre_empenhos_filtered = df_pre_empenhos_filtered[df_pre_empenhos_filtered['Natureza'].isin(ano_emp)]
            if 'Grupo' in df_pre_empenhos.columns and grupo_emp:
                df_pre_empenhos_filtered = df_pre_empenhos_filtered[df_pre_empenhos_filtered['Grupo'].isin(grupo_emp)]
            st.markdown("---")

            col1, col2, col3 = st.columns(3)
            with col1:
                st.metric("Total Pré-Empenhos", f"{len(df_pre_empenhos_filtered):,}".replace(",", "."))
            with col2:
                if 'Valor Pré-Empenhado' in df_pre_empenhos_filtered.columns:
                    st.metric("Valor Total", formatar_real(df_pre_empenhos_filtered['Valor Pré-Empenhado'].sum()))
            with col3:
                if 'Valor Pré-Empenhado' in df_pre_empenhos_filtered.columns:
                    valor_medio = df_pre_empenhos_filtered['Valor Pré-Empenhado'].mean()
                    st.metric("Valor Médio", formatar_real(valor_medio))
            
            st.markdown("---")
            st.subheader("Dados")
            st.dataframe(df_pre_empenhos_filtered, use_container_width=True)
            buffer = io.BytesIO()
            with pd.ExcelWriter(buffer, engine="openpyxl") as writer:
                df_empenhos_filtered.to_excel(writer, index=False, sheet_name="Pré-Empenhos")
            buffer.seek(0)
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            st.download_button(label="⬇️ Baixar dados", data=buffer, file_name=f"Dados pré-empenhos {timestamp}.xlsx",
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")
    
    # ==================== SUB-ABA 3: RESTOS A PAGAR ====================
    with subtab3_orc:
        st.subheader("Restos a Pagar")       
        if len(df_rp) == 0:
            st.warning("Dados de restos a pagar não disponíveis.")
        else:
            col1_f, col2_f, col3_f = st.columns(3)
            with col1_f:
                if 'Ano' in df_rp.columns:
                    anos_emp = sorted(df_rp['Ano'].dropna().unique().tolist())
                    ano_emp = st.multiselect("Ano", options=anos_emp, default=[], key="ano_rp")
            with col2_f:
                if 'Favorecido' in df_rp.columns:
                    favorecidos = sorted([f for f in df_rp['Favorecido'].unique() if f != 'Não informado'][:100])
                    favorecido_emp = st.selectbox("Favorecido", options=['Todos'] + favorecidos, key="fav_rp")
            with col3_f:
                if 'Grupo' in df_rp.columns:
                    grupos = sorted(df_rp['Grupo'].dropna().unique().tolist())
                    grupo_emp = st.multiselect("Grupo", options=grupos, default=[], key="grupo_rp")
            
            df_rp_filtered = df_rp.copy()
            if 'Ano' in df_rp.columns and ano_emp:
                df_rp_filtered = df_rp_filtered[df_rp_filtered['Ano'].isin(ano_emp)]
            if 'Favorecido' in df_rp.columns and favorecido_emp != 'Todos':
                df_rp_filtered = df_rp_filtered[df_rp_filtered['Favorecido'] == favorecido_emp]
            if 'Grupo' in df_rp.columns and grupo_emp:
                df_rp_filtered = df_rp_filtered[df_rp_filtered['Grupo'].isin(grupo_emp)]
            st.markdown("---")
            
            col1, col2, col3, col4 = st.columns(4)
            with col1:
                if 'RP Inscritos' in df_rp_filtered.columns:
                    st.metric("RP Inscritos", formatar_real(df_rp_filtered['RP Inscritos'].sum()))
            with col2:
                if 'RP Pagos' in df_rp_filtered.columns:
                    st.metric("RP Pagos", formatar_real(df_rp_filtered['RP Pagos'].sum()))
            with col3:
                if 'RP a Pagar' in df_rp_filtered.columns:
                    st.metric("RP a Pagar", formatar_real(df_rp_filtered['RP a Pagar'].sum()))
            with col4:
                if 'RP Cancelados' in df_rp_filtered.columns:
                    st.metric("RP Cancelados", formatar_real(df_rp_filtered['RP Cancelados'].sum()))
            st.markdown("---")
                        
            col1, col2 = st.columns(2)            
            with col1:
                if 'Favorecido' in df_rp_filtered.columns and 'RP a Pagar' in df_rp_filtered.columns and len(df_rp_filtered) > 0:
                    fav_rp_agg = df_rp_filtered.groupby('Favorecido')['RP a Pagar'].sum().nlargest(15)    
                    if len(fav_rp_agg) > 0:
                        st.markdown("### RP por favorecidos")
                        fav_rp_base = df_rp_filtered.groupby("Favorecido", as_index=False)[["RP a Pagar"]].sum()
                        opcoes_fav = [3,5,10,15,20,25,len(fav_rp_base)]
                        index_fav = 1 if len(fav_rp_base) >= 10 else 0
                        top_fav = st.selectbox("Selecione a quantidade de favorecidos para exibir:", opcoes_fav,
                            index=index_fav, key="top_fav_rp")
                        fav_rp_top = fav_rp_base.nlargest(top_fav, "RP a Pagar").sort_values("RP a Pagar", ascending=True)
                        fig_fav_rp = go.Figure()
                        fig_fav_rp.add_trace(go.Bar(y=fav_rp_top["Favorecido"], x=fav_rp_top["RP a Pagar"], orientation="h",
                                marker_color="#00689D", text=fav_rp_top["RP a Pagar"].apply(formatar_real), textposition="auto"))
                        fig_fav_rp.update_layout(height=400 + len(fav_rp_top) * 35, xaxis_title="Valor (R$)", yaxis_title=None,
                            legend_title=None, hovermode="y unified", separators=",.", yaxis={"categoryorder": "total ascending"})
                        st.plotly_chart(fig_fav_rp, use_container_width=True)

            with col2:
                if len(df_rp_filtered) > 0:
                    st.markdown("### 📊 Distribuição de RP")
                    valores_rp = {'Pagos': df_rp_filtered['RP Pagos'].sum() if 'RP Pagos' in df_rp_filtered.columns else 0,
                        'A Pagar': df_rp_filtered['RP a Pagar'].sum() if 'RP a Pagar' in df_rp_filtered.columns else 0,
                        'Cancelados': df_rp_filtered['RP Cancelados'].sum() if 'RP Cancelados' in df_rp_filtered.columns else 0}
                    if valores_rp:
                        fig_dist_rp = go.Figure(data=[go.Pie(labels=list(valores_rp.keys()), values=list(valores_rp.values()),
                            marker=dict(colors=['#28a745', '#ffc107', '#dc3545']), hole=0.4)])
                        fig_dist_rp.update_layout(height=500)
                        st.plotly_chart(fig_dist_rp, use_container_width=True)
            st.markdown("---")

            st.subheader("Dados")           
            # Formatar apenas as colunas de valores monetários
            for col in df_rp_filtered.columns:
                if 'Valor' in col or 'valor' in col or 'R$' in col or 'RP' in col:
                    if pd.api.types.is_numeric_dtype(df_rp_filtered[col]):
                        df_rp_filtered[col] = df_rp_filtered[col].apply(lambda x: formatar_real(x) if pd.notna(x) else '-')
            st.dataframe(df_rp_filtered, use_container_width=True)
            buffer = io.BytesIO()
            with pd.ExcelWriter(buffer, engine="openpyxl") as writer:
                df_rp_filtered.to_excel(writer, index=False, sheet_name="Restos a pagar")
            buffer.seek(0)
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            st.download_button(label="⬇️ Baixar dados", data=buffer, file_name=f"Dados restos a pagar {timestamp}.xlsx",
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")

# ==================== ABA 8: RECONCILIAÇÃO DE DADOS ====================
with tab6:
    st.header("Inconsistências nos dados dos sistemas")
    st.info("""Esta aba compara os dados do **ComprasNet** com os dados do Portal TRF5.""")
    
    # Função para normalizar número de contrato (remover zeros à esquerda)
    def normalizar_contrato(num_contrato):
        """Remove zeros à esquerda e normaliza o número do contrato"""
        if pd.isna(num_contrato):
            return ''
        # Converter para string e limpar
        num_str = str(num_contrato).strip()
        # Se contém /, separar e tratar cada parte
        if '/' in num_str:
            partes = num_str.split('/')
            # Remover zeros à esquerda da primeira parte (número)
            num_sem_zeros = partes[0].lstrip('0') or '0'
            # Manter o ano
            if len(partes) > 1:
                return f"{num_sem_zeros}/{partes[1]}"
            return num_sem_zeros
        return num_str.lstrip('0') or '0'
    
    # Preparar dados do ComprasNet
    df_comprasnet = df.copy()
    if 'numeroContrato' in df_comprasnet.columns:
        df_comprasnet['numeroContrato_original'] = df_comprasnet['numeroContrato']
        df_comprasnet['numeroContrato'] = df_comprasnet['numeroContrato'].apply(normalizar_contrato)
    
    # Preparar dados do Portal TRF5 (empenhos)
    df_portal_rec = df_empenhos.copy()
    
    # Tentar identificar a coluna de número de contrato no portal
    # Possíveis nomes: 'Contrato', 'Número Contrato', 'Nº Contrato', 'numeroContrato', 'Empenho'
    col_contrato_portal = None
    for col in ['Contrato', 'Número Contrato', 'Nº Contrato', 'numeroContrato', 'Numero Contrato', 'Empenho']:
        if col in df_portal_rec.columns:
            col_contrato_portal = col
            break
    
    if col_contrato_portal is None:
        st.warning("⚠️ Não foi possível identificar a coluna de número de contrato nos dados de empenhos.")
        st.info("Colunas disponíveis: " + ", ".join(df_portal_rec.columns.tolist()[:10]) + "...")
    else:
        df_portal_rec[f'{col_contrato_portal}_original'] = df_portal_rec[col_contrato_portal]
        df_portal_rec[col_contrato_portal] = df_portal_rec[col_contrato_portal].apply(normalizar_contrato)
        
        # Obter conjuntos únicos de contratos
        contratos_comprasnet = set(df_comprasnet['numeroContrato'].unique())
        contratos_portal = set(df_portal_rec[col_contrato_portal].unique())
        
        # Calcular intersecções
        contratos_ambos = contratos_comprasnet & contratos_portal
        contratos_so_comprasnet = contratos_comprasnet - contratos_portal
        contratos_so_portal = contratos_portal - contratos_comprasnet
        
        col1, col2, col3, col4 = st.columns(4)
        with col1:
            st.metric("Quantidade de contratos no ComprasNet", f"{len(contratos_comprasnet):,}")
        with col2:
            st.metric("Quantidade de contratos no Portal TRF5", f"{len(contratos_portal):,}")
        with col3:
            st.metric("Em Ambos", f"{len(contratos_ambos):,}")
        with col4:
            perc_match = (len(contratos_ambos) / len(contratos_comprasnet) * 100) if len(contratos_comprasnet) > 0 else 0
            st.metric("% Correspondência", f"{perc_match:.1f}%")
        st.markdown("---")
        
        col1, col2 = st.columns(2)
        with col1:
            fig_dist = go.Figure(data=[go.Pie(labels=['Em Ambos', 'Só ComprasNet', 'Só Portal'],
                values=[len(contratos_ambos), len(contratos_so_comprasnet), len(contratos_so_portal)],
                marker=dict(colors=['#28a745', '#ffc107', '#dc3545']), hole=0.4)])
            fig_dist.update_layout(title="Distribuição de Contratos", height=400)
            st.plotly_chart(fig_dist, use_container_width=True)
        with col2:
            dados_comp = pd.DataFrame({'Categoria': ['ComprasNet Total', 'Portal TRF5 Total', 'Correspondência'],
                'Quantidade': [len(contratos_comprasnet), len(contratos_portal), len(contratos_ambos)]})
            fig_comp = go.Figure()
            fig_comp.add_trace(go.Bar(x=dados_comp['Categoria'], y=dados_comp['Quantidade'],
                marker_color=['#0068c9', '#17a2b8', '#28a745'], text=dados_comp['Quantidade'], textposition='auto'))
            fig_comp.update_layout(title="Comparação de Quantidades", yaxis_title="Quantidade de Contratos", height=400)
            st.plotly_chart(fig_comp, use_container_width=True)        
        st.markdown("---")

        rec_tab1, rec_tab2, rec_tab3 = st.tabs([f"✅ Em Ambos ({len(contratos_ambos)})",
                                                f"⚠️ Só ComprasNet ({len(contratos_so_comprasnet)})",
                                                f"⚠️ Só Portal ({len(contratos_so_portal)})"])
        
        with rec_tab1:
            st.subheader("Contratos presentes em ambas as bases")
            if len(contratos_ambos) > 0:
                df_ambos = df_comprasnet[df_comprasnet['numeroContrato'].isin(contratos_ambos)][
                    ['numeroContrato', 'nomeRazaoSocialFornecedor', 'objeto', 'valorGlobal', 
                     'dataVigenciaInicial', 'dataVigenciaFinal', 'status']].sort_values('valorGlobal', ascending=False)
                df_portal_info = df_portal_rec[df_portal_rec[col_contrato_portal].isin(contratos_ambos)]
                st.metric("Contratos Reconciliados", f"{len(df_ambos):,}")
                st.metric("Valor Total (ComprasNet)", formatar_real(df_ambos['valorGlobal'].sum()))
                
                st.dataframe(df_ambos, use_container_width=True)
                buffer = io.BytesIO()
                with pd.ExcelWriter(buffer, engine="openpyxl") as writer:
                    df_ambos.to_excel(writer, index=False, sheet_name="Restos a pagar")
                buffer.seek(0)
                timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                st.download_button(label="⬇️ Baixar dados", data=buffer, file_name=f"Dados em ambos portais {timestamp}.xlsx",
                    mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")
            else:
                st.info("Nenhum contrato encontrado em ambas as bases.")
        
        with rec_tab2:
            st.subheader("Contratos presentes apenas no ComprasNet")
            st.markdown("""**Atenção:** Estes contratos estão cadastrados no ComprasNet mas não foram encontrados no Portal TRF5.""")
            
            if len(contratos_so_comprasnet) > 0:
                df_so_comprasnet = df_comprasnet[df_comprasnet['numeroContrato'].isin(contratos_so_comprasnet)][
                    ['numeroContrato', 'nomeRazaoSocialFornecedor', 'objeto', 'valorGlobal', 
                     'dataVigenciaInicial', 'dataVigenciaFinal', 'status']].sort_values('valorGlobal', ascending=False)
                
                st.metric("Total de Contratos", f"{len(df_so_comprasnet):,}")
                st.metric("Valor Total", formatar_real(df_so_comprasnet['valorGlobal'].sum()))
                
                # Análise por status
                status_counts = df_so_comprasnet['status'].value_counts()
                col1, col2 = st.columns(2)
                with col1:
                    st.metric("Vigentes", status_counts.get('Vigente', 0))
                with col2:
                    st.metric("Vencidos", status_counts.get('Vencido', 0))
                
                st.dataframe(df_so_comprasnet, use_container_width=True)
                buffer = io.BytesIO()
                with pd.ExcelWriter(buffer, engine="openpyxl") as writer:
                    df_so_comprasnet.to_excel(writer, index=False, sheet_name="Restos a pagar")
                buffer.seek(0)
                timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                st.download_button(label="⬇️ Baixar dados", data=buffer, file_name=f"Dados comprasnet {timestamp}.xlsx",
                    mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")
            else:
                st.success("Todos os contratos do ComprasNet foram encontrados no Portal!")
        
        with rec_tab3:
            st.subheader("Contratos presentes apenas no Portal TRF5")
            st.markdown("""**Atenção:** Estes contratos estão no Portal TRF5 mas não foram encontrados no ComprasNet.""")
            
            if len(contratos_so_portal) > 0:
                colunas_portal = [col_contrato_portal]
                for col in ['Favorecido Nome', 'Valor Empenhos Total', 'Data Emissão', 'Ano']:
                    if col in df_portal_rec.columns:
                        colunas_portal.append(col)
                
                df_so_portal = df_portal_rec[df_portal_rec[col_contrato_portal].isin(contratos_so_portal)][
                    colunas_portal].drop_duplicates(subset=[col_contrato_portal]).sort_values(
                    'Valor Empenhos Total' if 'Valor Empenhos Total' in colunas_portal else col_contrato_portal, ascending=False)
                
                st.metric("Total de Contratos", f"{len(df_so_portal):,}")
                
                if 'Valor Empenhos Total' in df_so_portal.columns:
                    total_val = pd.to_numeric(df_so_portal['Valor Empenhos Total'], errors='coerce').sum()
                    st.metric("Valor Total Empenhado", formatar_real(total_val))
                st.dataframe(df_so_portal, use_container_width=True)
                
                buffer = io.BytesIO()
                with pd.ExcelWriter(buffer, engine="openpyxl") as writer:
                    df_so_portal.to_excel(writer, index=False, sheet_name="Restos a pagar")
                buffer.seek(0)
                timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                st.download_button(label="⬇️ Baixar dados", data=buffer, file_name=f"Dados Portal TRF5 {timestamp}.xlsx",
                    mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")
            else:
                st.success("Todos os contratos do Portal foram encontrados no ComprasNet!")

# ==================== ABA 9: BUSCADOR ====================
# with tab7:
#     st.header("🔍 Buscador")
    
#     # OPÇÃO DE BUSCA: SIMPLIFICADA VS DETALHADA
#     tipo_busca = st.radio(
#         "Selecione o tipo de busca:",
#         ["📋 Simplificada (Resumo)", "🔬 Detalhada (Portal TRF5)"],
#         horizontal=True
#     )
    
#     st.markdown("---")
    
#     if tipo_busca == "📋 Simplificada (Resumo)":
#         # BUSCA SIMPLIFICADA - USA DADOS DO RESUMO
#         st.subheader("📋 Busca Simplificada - Dados Resumidos")
#         st.info("💡 Busca rápida nos dados consolidados por centro de custo")
        
#         # Filtros
#         col1, col2, col3 = st.columns(3)
        
#         with col1:
#             anos_busca = sorted(df_resumo['Ano'].unique())
#             ano_busca = st.multiselect("Ano", options=anos_busca, default=[], key="ano_busca_simp")
        
#         with col2:
#             gestores_busca = sorted([g for g in df_resumo['Gestor(a)'].unique() if g != 'Não informado'])
#             gestor_busca = st.selectbox("Gestor", options=['Todos'] + gestores_busca, key="gestor_busca_simp")
        
#         with col3:
#             centros_busca = sorted([c for c in df_resumo['Centro de Custo'].unique() if c != 'Não informado'])[:100]
#             centro_busca = st.selectbox("Centro de Custo", options=['Todos'] + centros_busca, key="centro_busca_simp")
        
#         # Busca textual
#         busca_texto_simp = st.text_input("🔍 Busca livre (Gestor, Centro de Custo):", "", key="texto_busca_simp")
        
#         # Aplicar filtros
#         df_busca_simp = df_resumo.copy()
        
#         if ano_busca:
#             df_busca_simp = df_busca_simp[df_busca_simp['Ano'].isin(ano_busca)]
        
#         if gestor_busca != 'Todos':
#             df_busca_simp = df_busca_simp[df_busca_simp['Gestor(a)'] == gestor_busca]
        
#         if centro_busca != 'Todos':
#             df_busca_simp = df_busca_simp[df_busca_simp['Centro de Custo'] == centro_busca]
        
#         if busca_texto_simp:
#             mask = (
#                 df_busca_simp['Gestor(a)'].astype(str).str.contains(busca_texto_simp, case=False, na=False) |
#                 df_busca_simp['Centro de Custo'].astype(str).str.contains(busca_texto_simp, case=False, na=False)
#             )
#             df_busca_simp = df_busca_simp[mask]
        
#         # Métricas
#         st.markdown("---")
#         col1, col2, col3, col4 = st.columns(4)
        
#         with col1:
#             st.metric("Registros", f"{len(df_busca_simp):,}")
#         with col2:
#             st.metric("Limite", formatar_real(df_busca_simp['Limite'].sum()))
#         with col3:
#             st.metric("Empenhado", formatar_real(df_busca_simp['Empenhado'].sum()))
#         with col4:
#             st.metric("Pago", formatar_real(df_busca_simp['Valor Empenhos Pagos'].sum()))
        
#         # Resultados
#         st.markdown("---")
#         st.subheader("📊 Resultados")
        
#         df_busca_display = df_busca_simp[['Ano', 'Gestor(a)', 'Centro de Custo', 'Limite', 
#                                           'Pré-empenhado', 'Empenhado', 'Valor Empenhos Pagos']].copy()
        
#         for col in ['Limite', 'Pré-empenhado', 'Empenhado', 'Valor Empenhos Pagos']:
#             df_busca_display[col] = df_busca_display[col].apply(formatar_real)
        
#         st.dataframe(df_busca_display, use_container_width=True)
        
#         # Download
#         csv = df_busca_simp.to_csv(index=False).encode('utf-8')
#         st.download_button(
#             label="📥 Baixar resultados (CSV)",
#             data=csv,
#             file_name=f"busca_simplificada_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv",
#             mime="text/csv"
#         )
    
#     else:
#         # BUSCA DETALHADA - USA DADOS DE RESUMO
#         st.subheader("🔬 Busca Detalhada - Histórico de Modificações")
#         st.info("💡 Busca nos dados do Portal TRF5, com registro histórico de cada modificação")
        
#         df_portal = df_resumo.copy()
        
#         if len(df_portal) == 0:
#             st.warning("Dados do portal não disponíveis.")
#         else:
#             # Filtros
#             col1, col2, col3, col4 = st.columns(4)
            
#             with col1:
#                 if 'Ano' in df_portal.columns:
#                     anos_portal = ['Todos'] + sorted(df_portal['Ano'].dropna().unique().tolist())
#                     ano_portal_sel = st.multiselect("Ano", anos_portal, default=['Todos'], key="ano_portal")
            
#             with col2:
#                 if 'Centro de Custo' in df_portal.columns:
#                     centros_portal = ['Todos'] + sorted(df_portal['Centro de Custo'].dropna().unique().tolist()[:100])
#                     centro_portal_sel = st.selectbox("Centro de Custo", centros_portal, key="centro_portal")
            
#             with col3:
#                 if 'Gestores' in df_portal.columns:
#                     gestores_portal = ['Todos'] + sorted(df_portal['Gestores'].dropna().unique().tolist()[:100])
#                     gestor_portal_sel = st.selectbox("Gestor", gestores_portal, key="gestor_portal")
            
#             with col4:
#                 if 'Tipo Nome' in df_portal.columns:
#                     tipos_portal = ['Todos'] + sorted(df_portal['Tipo Nome'].dropna().unique().tolist())
#                     tipo_portal_sel = st.selectbox("Tipo de Documento", tipos_portal, key="tipo_portal")
            
#             # Busca textual
#             col1, col2 = st.columns([3, 1])
            
#             with col1:
#                 busca_texto = st.text_input("🔍 Busca livre (Empenho, Favorecido, Processo):", "", key="texto_portal")
            
#             with col2:
#                 limite_registros = st.selectbox("Limite de registros", [100, 500, 1000, 5000], index=1, key="limite_portal")
            
#             # Aplicar filtros
#             df_portal_filtered = df_portal.copy()
            
#             if 'Ano' in df_portal.columns and 'Todos' not in ano_portal_sel and ano_portal_sel:
#                 df_portal_filtered = df_portal_filtered[df_portal_filtered['Ano'].isin(ano_portal_sel)]
            
#             if 'Centro de Custo' in df_portal.columns and centro_portal_sel != 'Todos':
#                 df_portal_filtered = df_portal_filtered[df_portal_filtered['Centro de Custo'] == centro_portal_sel]
            
#             if 'Gestores' in df_portal.columns and gestor_portal_sel != 'Todos':
#                 df_portal_filtered = df_portal_filtered[df_portal_filtered['Gestores'] == gestor_portal_sel]
            
#             if 'Tipo Nome' in df_portal.columns and tipo_portal_sel != 'Todos':
#                 df_portal_filtered = df_portal_filtered[df_portal_filtered['Tipo Nome'] == tipo_portal_sel]
            
#             # Busca textual
#             if busca_texto:
#                 mask = False
#                 for col in ['Nota Empenho', 'Favorecido Nome', 'Número Processo', 'Empenho']:
#                     if col in df_portal_filtered.columns:
#                         mask = mask | df_portal_filtered[col].astype(str).str.contains(busca_texto, case=False, na=False)
#                 df_portal_filtered = df_portal_filtered[mask]
            
#             # Limitar registros
#             df_portal_filtered = df_portal_filtered.head(limite_registros)
            
#             st.markdown("---")
            
#             # Métricas do resultado
#             col1, col2, col3, col4 = st.columns(4)
            
#             with col1:
#                 st.metric("Registros Encontrados", f"{len(df_portal_filtered):,}")
            
#             with col2:
#                 if 'Valor Empenhos Total' in df_portal_filtered.columns:
#                     total_emp_portal = pd.to_numeric(df_portal_filtered['Valor Empenhos Total'], errors='coerce').sum()
#                     st.metric("Valor Total Empenhos", formatar_real(total_emp_portal))
            
#             with col3:
#                 if 'Valor Empenhos Pagos' in df_portal_filtered.columns:
#                     total_pago_portal = pd.to_numeric(df_portal_filtered['Valor Empenhos Pagos'], errors='coerce').sum()
#                     st.metric("Valor Total Pago", formatar_real(total_pago_portal))
            
#             with col4:
#                 if 'Ano' in df_portal_filtered.columns:
#                     anos_unicos = df_portal_filtered['Ano'].nunique()
#                     st.metric("Anos Cobertos", f"{anos_unicos}")
            
#             # Seleção de colunas para exibição
#             st.markdown("---")
#             st.subheader("📋 Resultados da Busca")
            
#             colunas_disponiveis = df_portal_filtered.columns.tolist()
            
#             # Colunas padrão sugeridas
#             colunas_padrao = ['Ano', 'Centro de Custo', 'Gestores', 'Nota Empenho', 'Favorecido Nome', 
#                              'Tipo Nome', 'Valor Empenhos Total', 'Valor Empenhos Pagos', 'Data Emissão']
#             colunas_padrao = [c for c in colunas_padrao if c in colunas_disponiveis]
            
#             colunas_selecionadas = st.multiselect(
#                 "Selecione as colunas para visualização:",
#                 options=colunas_disponiveis,
#                 default=colunas_padrao,
#                 key="colunas_portal"
#             )
            
#             if colunas_selecionadas:
#                 df_exibir = df_portal_filtered[colunas_selecionadas].copy()
                
#                 # Formatar valores monetários
#                 colunas_monetarias = [col for col in colunas_selecionadas if 'Valor' in col or 'R$' in col]
#                 for col in colunas_monetarias:
#                     try:
#                         df_exibir[col] = pd.to_numeric(df_exibir[col], errors='coerce')
#                         df_exibir[col] = df_exibir[col].apply(lambda x: formatar_real(x) if pd.notna(x) else '-')
#                     except:
#                         pass
                
#                 st.dataframe(df_exibir, use_container_width=True)
                
#                 # Download
#                 csv = df_portal_filtered[colunas_selecionadas].to_csv(index=False).encode('utf-8')
#                 st.download_button(
#                     label="📥 Baixar resultados (CSV)",
#                     data=csv,
#                     file_name=f"busca_portal_trf5_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv",
#                     mime="text/csv",
#                     key="download_portal"
#                 )
#             else:
#                 st.warning("Selecione pelo menos uma coluna para visualização.")
            
#             # Análise rápida
#             if len(df_portal_filtered) > 0:
#                 st.markdown("---")
#                 st.subheader("📊 Análise Rápida dos Resultados")
                
#                 col1, col2 = st.columns(2)
                
#                 with col1:
#                     # Por tipo de documento
#                     if 'Tipo Nome' in df_portal_filtered.columns:
#                         tipo_count = df_portal_filtered['Tipo Nome'].value_counts().head(10)
                        
#                         fig_tipo = go.Figure(data=[go.Pie(
#                             labels=tipo_count.index,
#                             values=tipo_count.values,
#                             hole=0.4
#                         )])
                        
#                         fig_tipo.update_layout(
#                             title="Distribuição por Tipo de Documento",
#                             height=400
#                         )
                        
#                         st.plotly_chart(fig_tipo, use_container_width=True)
                
#                 with col2:
#                     # Por grupo de despesa
#                     if 'Grupo Despesa Nome' in df_portal_filtered.columns:
#                         grupo_count = df_portal_filtered['Grupo Despesa Nome'].value_counts().head(10)
                        
#                         fig_grupo_portal = go.Figure()
#                         fig_grupo_portal.add_trace(go.Bar(
#                             x=grupo_count.values,
#                             y=grupo_count.index,
#                             orientation='h',
#                             marker_color='#0068c9'
#                         ))
                        
#                         fig_grupo_portal.update_layout(
#                             title="Top 10 Grupos de Despesa",
#                             height=400,
#                             xaxis_title="Quantidade",
#                             yaxis_title="",
#                             yaxis={'categoryorder':'total ascending'}
#                         )
                        
#                         st.plotly_chart(fig_grupo_portal, use_container_width=True)

# ==================== ABA 10: ANÁLISE DETALHADA DE CONTRATOS ====================
with tab7:
    st.header("📈 Análise Detalhada de Contratos")
    st.markdown("""
    Esta aba apresenta uma análise aprofundada cruzando dados de contratos com informações 
    de empenhos, gestores e centros de custos.
    """)
    
    # Fazer LEFT JOIN entre contratos e empenhos
    # Normalizar números de contrato
    def normalizar_contrato(num_contrato):
        """Remove zeros à esquerda e normaliza o número do contrato"""
        if pd.isna(num_contrato):
            return ''
        num_str = str(num_contrato).strip()
        if '/' in num_str:
            partes = num_str.split('/')
            num_sem_zeros = partes[0].lstrip('0') or '0'
            if len(partes) > 1:
                return f"{num_sem_zeros}/{partes[1]}"
            return num_sem_zeros
        return num_str.lstrip('0') or '0'
    
    # Preparar dados
    df_contratos_join = df.copy()
    df_contratos_join['numeroContrato_norm'] = df_contratos_join['numeroContrato'].apply(normalizar_contrato)
    
    # Extrair ano do contrato se não existir
    if 'ano' not in df_contratos_join.columns:
        df_contratos_join['ano'] = df_contratos_join['numeroContrato'].str.extract(r'/(\d{4})')[0]
    
    # Converter ano para string para compatibilidade com merge
    df_contratos_join['ano'] = df_contratos_join['ano'].astype(str)
    
    # Preparar empenhos
    if len(df_empenhos) > 0:
        df_empenhos_join = df_empenhos.copy()
        
        # Tentar encontrar coluna de contrato
        col_contrato_emp = None
        for col in ['Contrato', 'Número Contrato', 'numeroContrato', 'Empenho']:
            if col in df_empenhos_join.columns:
                col_contrato_emp = col
                break
        
        if col_contrato_emp:
            df_empenhos_join['numeroContrato_norm'] = df_empenhos_join[col_contrato_emp].apply(normalizar_contrato)
            
            # Preparar colunas para agregação - verificar quais existem
            agg_dict = {}
            if 'Valor Empenhado' in df_empenhos_join.columns:
                agg_dict['Valor Empenhado'] = 'sum'
            if 'Valor Pago' in df_empenhos_join.columns:
                agg_dict['Valor Pago'] = 'sum'
            
            # Se tiver colunas para agregar
            if agg_dict:
                empenhos_agg = df_empenhos_join.groupby('numeroContrato_norm').agg(agg_dict).reset_index()
            else:
                st.warning("⚠️ Colunas financeiras não encontradas nos empenhos")
                empenhos_agg = pd.DataFrame({'numeroContrato_norm': [], 'Valor Empenhado': [], 'Valor Pago': []})
            
            # Garantir que as colunas existam
            if 'Valor Empenhado' not in empenhos_agg.columns:
                empenhos_agg['Valor Empenhado'] = 0
            if 'Valor Pago' not in empenhos_agg.columns:
                empenhos_agg['Valor Pago'] = 0
            
            # Fazer LEFT JOIN
            df_analise = df_contratos_join.merge(
                empenhos_agg,
                on='numeroContrato_norm',
                how='left',
                suffixes=('', '_emp')
            )
        else:
            st.warning("⚠️ Não foi possível identificar coluna de contrato nos empenhos")
            df_analise = df_contratos_join.copy()
            df_analise['Valor Empenhado'] = 0
            df_analise['Valor Pago'] = 0
    else:
        st.warning("⚠️ Dados de empenhos não disponíveis")
        df_analise = df_contratos_join.copy()
        df_analise['Valor Empenhado'] = 0
        df_analise['Valor Pago'] = 0
    
    # Tentar fazer join com resumo (para pegar gestor e centro de custos)
    if len(df_resumo) > 0:
        # Preparar resumo agrupado por ano
        resumo_por_ano = df_resumo.groupby('Ano').agg({
            'Gestor(a)': lambda x: ', '.join(x.dropna().unique()[:3]),  # Até 3 gestores
            'Centro de Custo': lambda x: ', '.join(x.dropna().unique()[:3])  # Até 3 centros
        }).reset_index()
        
        # Join com contratos pelo ano
        df_analise = df_analise.merge(
            resumo_por_ano,
            left_on='ano',
            right_on='Ano',
            how='left'
        )
    
    # Calcular métricas de prazo
    df_analise['Dias de Vigência'] = (df_analise['dataVigenciaFinal'] - df_analise['dataVigenciaInicial']).dt.days
    df_analise['Dias até Vencimento'] = (df_analise['dataVigenciaFinal'] - hoje).dt.days
    df_analise['% Tempo Decorrido'] = (
        (hoje - df_analise['dataVigenciaInicial']).dt.days / 
        df_analise['Dias de Vigência'] * 100
    ).clip(0, 100)
    
    # Preencher valores nulos - garantir que as colunas existam
    if 'Valor Empenhado' not in df_analise.columns:
        df_analise['Valor Empenhado'] = 0
    else:
        df_analise['Valor Empenhado'] = df_analise['Valor Empenhado'].fillna(0)
    
    if 'Valor Pago' not in df_analise.columns:
        df_analise['Valor Pago'] = 0
    else:
        df_analise['Valor Pago'] = df_analise['Valor Pago'].fillna(0)
    
    # Preencher Gestor e Centro de Custo
    if 'Gestor(a)' in df_analise.columns:
        df_analise['Gestor(a)'] = df_analise['Gestor(a)'].fillna('Não informado')
    else:
        df_analise['Gestor(a)'] = 'Não informado'
    
    if 'Centro de Custo' in df_analise.columns:
        df_analise['Centro de Custo'] = df_analise['Centro de Custo'].fillna('Não informado')
    else:
        df_analise['Centro de Custo'] = 'Não informado'
    
    # Calcular % de execução
    df_analise['% Empenhado'] = (df_analise['Valor Empenhado'] / df_analise['valorGlobal'] * 100).fillna(0).clip(0, 200)
    df_analise['% Pago'] = (df_analise['Valor Pago'] / df_analise['valorGlobal'] * 100).fillna(0).clip(0, 200)
    
    # ============ VISÃO GERAL ============
    st.markdown("## 📊 Visão Geral")
    
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        st.metric("Total de Contratos", len(df_analise))
        st.metric("Contratos com Empenhos", len(df_analise[df_analise['Valor Empenhado'] > 0]))
    
    with col2:
        st.metric("Valor Total Contratos", formatar_real(df_analise['valorGlobal'].sum()))
        st.metric("Valor Total Empenhado", formatar_real(df_analise['Valor Empenhado'].sum()))
    
    with col3:
        st.metric("Valor Total Pago", formatar_real(df_analise['Valor Pago'].sum()))
        media_exec = df_analise['% Empenhado'].mean()
        st.metric("% Execução Média", formatar_percentual(media_exec))
    
    with col4:
        prazo_medio = df_analise['Dias de Vigência'].mean()
        st.metric("Prazo Médio (dias)", f"{prazo_medio:.0f}" if not pd.isna(prazo_medio) else "N/A")
        tempo_medio = df_analise['% Tempo Decorrido'].mean()
        st.metric("% Tempo Médio Decorrido", formatar_percentual(tempo_medio))
    
    st.markdown("---")
    
    # ============ ANÁLISE POR PRAZO ============
    st.markdown("## ⏰ Análise por Prazo")
    
    # Classificar contratos por faixa de prazo
    df_analise['Faixa de Prazo'] = pd.cut(
        df_analise['Dias de Vigência'],
        bins=[0, 180, 365, 730, 1825, float('inf')],
        labels=['Até 6 meses', '6-12 meses', '1-2 anos', '2-5 anos', 'Acima de 5 anos']
    )
    
    prazo_analise = df_analise.groupby('Faixa de Prazo', observed=True).agg({
        'numeroContrato': 'count',
        'valorGlobal': 'sum',
        '% Empenhado': 'mean',
        '% Tempo Decorrido': 'mean'
    }).reset_index()
    prazo_analise.columns = ['Faixa de Prazo', 'Quantidade', 'Valor Total', '% Empenhado Médio', '% Tempo Decorrido']
    
    col1, col2 = st.columns(2)
    
    with col1:
        st.markdown("### Contratos por Faixa de Prazo")
        fig_prazo = px.bar(
            prazo_analise,
            x='Faixa de Prazo',
            y='Quantidade',
            text='Quantidade',
            labels={'Faixa de Prazo': 'Faixa', 'Quantidade': 'Contratos'}
        )
        fig_prazo.update_traces(textposition='outside')
        st.plotly_chart(fig_prazo, use_container_width=True)
    
    with col2:
        st.markdown("### % Execução por Faixa de Prazo")
        fig_exec_prazo = px.bar(
            prazo_analise,
            x='Faixa de Prazo',
            y='% Empenhado Médio',
            text=prazo_analise['% Empenhado Médio'].apply(lambda x: f"{x:.1f}%"),
            labels={'Faixa de Prazo': 'Faixa', '% Empenhado Médio': '% Execução'}
        )
        fig_exec_prazo.update_traces(textposition='outside', marker_color='#17a2b8')
        st.plotly_chart(fig_exec_prazo, use_container_width=True)
    
    with st.expander("📋 Ver Tabela - Análise por Prazo", expanded=False):
        prazo_display = prazo_analise.copy()
        prazo_display['Valor Total'] = prazo_display['Valor Total'].apply(formatar_real)
        prazo_display['% Empenhado Médio'] = prazo_display['% Empenhado Médio'].apply(formatar_percentual)
        prazo_display['% Tempo Decorrido'] = prazo_display['% Tempo Decorrido'].apply(formatar_percentual)
        st.dataframe(prazo_display, use_container_width=True)
    
    st.markdown("---")
    
    # ============ ANÁLISE POR GESTOR ============
    st.markdown("## 👤 Análise por Gestor")
    
    if 'Gestor(a)' in df_analise.columns:
        gestor_analise = df_analise.groupby('Gestor(a)').agg({
            'numeroContrato': 'count',
            'valorGlobal': 'sum',
            'Valor Empenhado': 'sum',
            'Valor Pago': 'sum',
            'Dias até Vencimento': 'mean'
        }).reset_index()
        gestor_analise = gestor_analise[gestor_analise['Gestor(a)'] != 'Não informado']
        gestor_analise.columns = ['Gestor', 'Contratos', 'Valor Total', 'Empenhado', 'Pago', 'Dias Médios p/ Vencimento']
        gestor_analise = gestor_analise.sort_values('Valor Total', ascending=False)
        
        # Top 15 gestores
        top_gestores_detalhado = gestor_analise.head(15)
        
        col1, col2 = st.columns(2)
        
        with col1:
            st.markdown("### Top 15 Gestores - Valor Total")
            fig_gest = go.Figure()
            fig_gest.add_trace(go.Bar(
                x=top_gestores_detalhado['Valor Total'],
                y=top_gestores_detalhado['Gestor'],
                orientation='h',
                marker_color='#0068c9',
                text=top_gestores_detalhado['Valor Total'].apply(formatar_real),
                textposition='auto'
            ))
            fig_gest.update_layout(
                xaxis_title="Valor (R$)",
                yaxis_title="",
                height=500,
                yaxis={'categoryorder':'total ascending'}
            )
            st.plotly_chart(fig_gest, use_container_width=True)
        
        with col2:
            st.markdown("### Top 15 Gestores - Execução")
            top_gestores_detalhado_exec = top_gestores_detalhado.copy()
            top_gestores_detalhado_exec['% Execução'] = (
                top_gestores_detalhado_exec['Empenhado'] / 
                top_gestores_detalhado_exec['Valor Total'] * 100
            )
            
            fig_gest_exec = go.Figure()
            fig_gest_exec.add_trace(go.Bar(
                x=top_gestores_detalhado_exec['% Execução'],
                y=top_gestores_detalhado_exec['Gestor'],
                orientation='h',
                marker_color='#28a745',
                text=top_gestores_detalhado_exec['% Execução'].apply(formatar_percentual),
                textposition='auto'
            ))
            fig_gest_exec.update_layout(
                xaxis_title="% Execução",
                yaxis_title="",
                height=500,
                yaxis={'categoryorder':'total ascending'}
            )
            st.plotly_chart(fig_gest_exec, use_container_width=True)
        
        with st.expander("📋 Ver Tabela - Análise por Gestor", expanded=False):
            gestor_display = gestor_analise.copy()
            gestor_display['Valor Total'] = gestor_display['Valor Total'].apply(formatar_real)
            gestor_display['Empenhado'] = gestor_display['Empenhado'].apply(formatar_real)
            gestor_display['Pago'] = gestor_display['Pago'].apply(formatar_real)
            gestor_display['Dias Médios p/ Vencimento'] = gestor_display['Dias Médios p/ Vencimento'].apply(
                lambda x: f"{x:.0f}" if not pd.isna(x) else "N/A"
            )
            st.dataframe(gestor_display, use_container_width=True)
    else:
        st.info("Dados de gestor não disponíveis para análise")
    
    st.markdown("---")
    
    # ============ ANÁLISE POR CENTRO DE CUSTOS ============
    st.markdown("## 🏢 Análise por Centro de Custos")
    
    if 'Centro de Custo' in df_analise.columns:
        centro_analise = df_analise.groupby('Centro de Custo').agg({
            'numeroContrato': 'count',
            'valorGlobal': 'sum',
            'Valor Empenhado': 'sum',
            'Dias de Vigência': 'mean',
            '% Tempo Decorrido': 'mean'
        }).reset_index()
        centro_analise = centro_analise[centro_analise['Centro de Custo'] != 'Não informado']
        centro_analise.columns = ['Centro de Custo', 'Contratos', 'Valor Total', 'Empenhado', 'Prazo Médio (dias)', '% Tempo Decorrido']
        centro_analise = centro_analise.sort_values('Valor Total', ascending=False)
        
        # Top 15 centros
        top_centros_detalhado = centro_analise.head(15)
        
        col1, col2 = st.columns(2)
        
        with col1:
            st.markdown("### Top 15 Centros - Contratos")
            fig_centro = px.bar(
                top_centros_detalhado,
                x='Contratos',
                y='Centro de Custo',
                orientation='h',
                text='Contratos',
                labels={'Contratos': 'Quantidade', 'Centro de Custo': ''}
            )
            fig_centro.update_traces(textposition='outside', marker_color='#ffc107')
            fig_centro.update_layout(height=500, yaxis={'categoryorder':'total ascending'})
            st.plotly_chart(fig_centro, use_container_width=True)
        
        with col2:
            st.markdown("### Top 15 Centros - Prazo Médio")
            fig_prazo_centro = px.bar(
                top_centros_detalhado,
                x='Prazo Médio (dias)',
                y='Centro de Custo',
                orientation='h',
                text=top_centros_detalhado['Prazo Médio (dias)'].apply(lambda x: f"{x:.0f}"),
                labels={'Prazo Médio (dias)': 'Dias', 'Centro de Custo': ''}
            )
            fig_prazo_centro.update_traces(textposition='outside', marker_color='#17a2b8')
            fig_prazo_centro.update_layout(height=500, yaxis={'categoryorder':'total ascending'})
            st.plotly_chart(fig_prazo_centro, use_container_width=True)
        
        with st.expander("📋 Ver Tabela - Análise por Centro de Custos", expanded=False):
            centro_display = centro_analise.copy()
            centro_display['Valor Total'] = centro_display['Valor Total'].apply(formatar_real)
            centro_display['Empenhado'] = centro_display['Empenhado'].apply(formatar_real)
            centro_display['Prazo Médio (dias)'] = centro_display['Prazo Médio (dias)'].apply(
                lambda x: f"{x:.0f}" if not pd.isna(x) else "N/A"
            )
            centro_display['% Tempo Decorrido'] = centro_display['% Tempo Decorrido'].apply(formatar_percentual)
            st.dataframe(centro_display, use_container_width=True)
    else:
        st.info("Dados de centro de custos não disponíveis para análise")
    
    st.markdown("---")
    
    # ============ BUSCA DETALHADA ============
    st.markdown("## 🔍 Busca Detalhada")
    
    col1, col2, col3 = st.columns(3)
    
    with col1:
        status_filtro_det = st.multiselect(
            "Status",
            options=df_analise['status'].unique().tolist(),
            default=[],
            key="status_filtro_detalhado"
        )
    
    with col2:
        if 'Gestor(a)' in df_analise.columns:
            gestores_disp = sorted([g for g in df_analise['Gestor(a)'].unique() if g != 'Não informado'])
            gestor_filtro_det = st.multiselect(
                "Gestor",
                options=gestores_disp,
                default=[],
                key="gestor_filtro_detalhado"
            )
        else:
            gestor_filtro_det = []
    
    with col3:
        faixa_prazo_filtro = st.multiselect(
            "Faixa de Prazo",
            options=['Até 6 meses', '6-12 meses', '1-2 anos', '2-5 anos', 'Acima de 5 anos'],
            default=[],
            key="prazo_filtro_detalhado"
        )
    
    # Aplicar filtros
    df_detalhado_filtrado = df_analise.copy()
    
    if status_filtro_det:
        df_detalhado_filtrado = df_detalhado_filtrado[df_detalhado_filtrado['status'].isin(status_filtro_det)]
    
    if gestor_filtro_det and 'Gestor(a)' in df_detalhado_filtrado.columns:
        df_detalhado_filtrado = df_detalhado_filtrado[df_detalhado_filtrado['Gestor(a)'].isin(gestor_filtro_det)]
    
    if faixa_prazo_filtro:
        df_detalhado_filtrado = df_detalhado_filtrado[df_detalhado_filtrado['Faixa de Prazo'].isin(faixa_prazo_filtro)]
    
    # Exibir resultados
    st.markdown(f"### Resultados: {len(df_detalhado_filtrado)} contratos")
    
    if len(df_detalhado_filtrado) > 0:
        # Selecionar colunas para exibição
        colunas_exibir = [
            'numeroContrato', 'nomeRazaoSocialFornecedor', 'valorGlobal',
            'Valor Empenhado', 'Valor Pago', '% Empenhado', '% Pago',
            'Dias de Vigência', 'Dias até Vencimento', '% Tempo Decorrido', 'status'
        ]
        
        if 'Gestor(a)' in df_detalhado_filtrado.columns:
            colunas_exibir.append('Gestor(a)')
        if 'Centro de Custo' in df_detalhado_filtrado.columns:
            colunas_exibir.append('Centro de Custo')
        
        # Filtrar apenas colunas que existem
        colunas_exibir = [col for col in colunas_exibir if col in df_detalhado_filtrado.columns]
        
        df_resultado_detalhado = df_detalhado_filtrado[colunas_exibir].copy()
        df_resultado_detalhado = df_resultado_detalhado.sort_values('Dias até Vencimento')
        
        st.dataframe(df_resultado_detalhado, use_container_width=True)
        
        # Download
        csv = df_resultado_detalhado.to_csv(index=False).encode('utf-8')
        st.download_button(
            label="📥 Baixar resultados completos (CSV)",
            data=csv,
            file_name=f"analise_detalhada_{datetime.now().strftime('%Y%m%d')}.csv",
            mime="text/csv",
            key="download_detalhado"
        )
    else:
        st.info("Nenhum contrato encontrado com os filtros selecionados")

# Rodapé
st.markdown("---")
st.markdown(
    """
    <div style='text-align: center; color: #666; padding: 20px;'>
        <p><strong>Justiça Federal do Ceará - TRF5</strong></p>
        <p>Painel Executivo de Contratos, Orçamento e Financeiro</p>
        <p style='font-size: 12px;'>Desenvolvido para análise e transparência na gestão de recursos públicos</p>
    </div>
    """,
    unsafe_allow_html=True
)