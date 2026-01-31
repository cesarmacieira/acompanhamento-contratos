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

st.set_page_config(page_title="Gestão de Contratos Públicos",layout="wide")
#st.image("logo_policromia.png",width=180)
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
                   #"logos/logo_Justica_Federal_Ceara_branca.png", 
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

    # 👉 compensação do offset vertical real da fonte
    texto_y = (H - text_h) // 2 - bbox[1]
    draw.text((texto_x, texto_y),texto,fill=(255,255,255,255),font=font)

    return banner

st.image(header_banner(),use_container_width=True)

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

# Configuração da página
#st.set_page_config(page_title="Portal Financeiro TRF5", page_icon="💰", layout="wide", initial_sidebar_state="collapsed")

# CSS customizado
st.markdown("""
    <style>
    .main {
        padding: 0rem 1rem;
    }
    .stTabs [data-baseweb="tab-list"] {
        gap: 2px;
    }
    .stTabs [data-baseweb="tab"] {
        padding: 10px 20px;
        background-color: #f0f2f6;
        border-radius: 5px 5px 0px 0px;
    }
    .stTabs [aria-selected="true"] {
        background-color: #0068c9;
        color: white;
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
""", unsafe_allow_html=True)

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
    try:
        df = pd.read_parquet('dados/Dados empenhos.parquet')
    except:
        df = pd.read_excel('dados/Dados empenhos.xlsx')
    
    # Converter colunas financeiras
    financial_cols = ['Valor Empenhado', 'Valor Pago', 'R$ a pagar']
    for col in financial_cols:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors='coerce').fillna(0)
    
    return df

# Função para carregar dados de pré-empenhos
@st.cache_data
def load_pre_empenhos_data():
    try:
        df = pd.read_parquet('dados/Dados pré empenhos.parquet')
    except:
        df = pd.read_excel('dados/Dados pré empenhos.xlsx')
    
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
    try:
        df = pd.read_parquet('dados/Dados restos apagar.parquet')
    except:
        df = pd.read_excel('dados/Dados restos a pagar.xlsx')
    
    # Converter colunas financeiras
    financial_cols = ['Valor RP Processados Inscritos', 'RP Inscritos', 'RP Cancelados', 
                     'RP Bloqueados', 'RP Pagos', 'RP a Pagar']
    for col in financial_cols:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors='coerce').fillna(0)
    
    return df

# Função para carregar dados do portal (para buscas detalhadas)
@st.cache_data
def load_portal_data():
    try:
        df = pd.read_parquet('dados/Dados portal TRF5.parquet')
    except:
        df = pd.read_excel('dados/Dados portal TRF5.xlsx')
    
    # Converter Ano para string
    if 'Ano' in df.columns:
        df['Ano'] = df['Ano'].astype(str)
    
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

# Título principal
#st.title("💰 Portal Financeiro TRF5")
#st.markdown("### Sistema de Acompanhamento e Análise de Gestão Orçamentária")

# Criar abas
tab1, tab2, tab3, tab4, tab5, tab6, tab7, tab8, tab9, tab10 = st.tabs([
    "📋 Lista de Contratos", "🚨 Alertas", "📊 Análises",
    "💰 Análise financeira", "👥 Análise por Gestores", "🏢 Análise por Centro de Custos", 
    "💳 Empenhos Detalhados",  "📋 Pré-Empenhos",  "📈 Restos a Pagar", "🔍 Buscador Detalhado"
])

# ==================== ABA 1: LISTA DE CONTRATOS ====================
with tab1:
    st.subheader("Lista Geral de Contratos")
    c1, c2, c3, c4 = st.columns(4)
    fornecedor = c1.multiselect("Fornecedor",sorted(df["nomeRazaoSocialFornecedor"].dropna().unique()))
    unidade = c2.multiselect("Unidade realizadora",sorted(df["nomeUnidadeRealizadoraCompra"].dropna().unique()))
    ano = c3.multiselect("Ano",sorted(df["ano"].dropna().unique()))
    status = c4.multiselect("Status",["Vigente", "Vencido"])
    c5, c6, c7, c8 = st.columns(4)
    modalidade = c5.multiselect("Modalidade de compra",sorted(df["nomeModalidadeCompra"].dropna().unique()))
    tipo = c6.multiselect("Tipo de contrato",sorted(df["nomeTipo"].dropna().unique()))
    categoria = c7.multiselect("Categoria",sorted(df["nomeCategoria"].dropna().unique()))
    busca_texto = c8.text_input("Busca livre (objeto / processo)")
    c9, c10, c11, c12 = st.columns(4)
    valor_min = c9.number_input("Valor mínimo (R$)",min_value=0.0,value=0.0,step=10000.0,format="%.2f")
    valor_max = c10.number_input("Valor máximo (R$)",min_value=0.0,value=float(df["valorGlobal"].max()),step=10000.0,format="%.2f")
    parcelas = c11.multiselect("Nº de parcelas",sorted(df["numeroParcelas"].dropna().unique()))
    valor_parcela_min, valor_parcela_max = c12.slider("Valor do contrato (R$)",float(df["valorParcela"].min()),
        float(df["valorParcela"].max()),(float(df["valorParcela"].min()), float(df["valorParcela"].max())))
    c13, c14 = st.columns(2)
    data_ini = c13.date_input("Vigência final a partir de",value=df["dataVigenciaFinal"].min().date() if pd.notnull(df["dataVigenciaFinal"].min()) else None)
    data_fim = c14.date_input("Vigência final até",value=df["dataVigenciaFinal"].max().date() if pd.notnull(df["dataVigenciaFinal"].max()) else None)
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
        texto = busca_texto.lower()
        df_f = df_f[df_f["objeto"].str.lower().str.contains(texto,na=False) |
                    df_f["processo"].astype(str).str.contains(texto,na=False)]
    if parcelas:
        df_f = df_f[df_f["numeroParcelas"].isin(parcelas)]
    df_f = df_f[(df_f["valorGlobal"] >= valor_min) & (df_f["valorGlobal"] <= valor_max)]
    if data_ini:
        df_f = df_f[df_f["dataVigenciaFinal"] >= pd.to_datetime(data_ini)]
    if data_fim:
        df_f = df_f[df_f["dataVigenciaFinal"] <= pd.to_datetime(data_fim)]
    df_f = df_f[(df_f["valorParcela"] >= valor_parcela_min) & (df_f["valorParcela"] <= valor_parcela_max)]
    st.dataframe(df_f.sort_values("dataVigenciaFinal").reset_index(drop=True),use_container_width=True,height=600)
    st.caption(f"Contratos exibidos: {len(df_f)}")
    buffer = io.BytesIO()
    with pd.ExcelWriter(buffer, engine="openpyxl") as writer:
        df_f.sort_values("dataVigenciaFinal").to_excel(writer, index=False, sheet_name="Contratos")
    buffer.seek(0)

    st.download_button(label="⬇️ Baixar contratos", data=buffer, file_name="contratos.xlsx",
        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")

# ==================== ABA 2: ALERTAS ====================
with tab2:
    st.subheader("Alertas de Prazo e Risco")
    v30 = df[(df["dataVigenciaFinal"] >= hoje) & (df["dataVigenciaFinal"] <= hoje + timedelta(days=30))]
    v60 = df[(df["dataVigenciaFinal"] > hoje + timedelta(days=30)) & (df["dataVigenciaFinal"] <= hoje + timedelta(days=60))]
    v90 = df[(df["dataVigenciaFinal"] > hoje + timedelta(days=60)) & (df["dataVigenciaFinal"] <= hoje + timedelta(days=90))]
    vencidos = df[df["dataVigenciaFinal"] < hoje]
    vigentes = df[df["dataVigenciaFinal"] >= hoje]
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Total de contratos", len(df))
    c2.metric("Contratos vigentes", len(vigentes))
    c3.metric("Contratos vencidos", len(vencidos))
    c4.metric("Percentual vencido", f"{(len(vencidos)/len(df)*100):.1f}%" if len(df) > 0 else "0%")
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
    st.dataframe(vigentes.sort_values("dataVigenciaFinal"),use_container_width=True)
    st.divider()
    with st.container():
        st.markdown("### ⏰ Vencendo em até 30 dias")
        c13, c14, c15, c16 = st.columns(4)
        c13.metric("Qtd contratos", len(v30))
        c14.metric("Valor total", f"R$ {v30['valorGlobal'].sum():,.2f}".replace(",", "X").replace(".", ",").replace("X", "."))
        c15.metric("Maior contrato", f"R$ {v30['valorGlobal'].max():,.2f}".replace(",", "X").replace(".", ",").replace("X", ".") if not v30.empty else "R$ 0,00")
        c16.metric("Média por contrato", f"R$ {v30['valorGlobal'].mean():,.2f}".replace(",", "X").replace(".", ",").replace("X", ".") if not v30.empty else "R$ 0,00")
        st.dataframe(v30.sort_values("dataVigenciaFinal"),use_container_width=True)
    with st.container():
        st.markdown("### ⏳ Vencendo entre 31 e 60 dias")
        c17, c18, c19, c20 = st.columns(4)
        c17.metric("Qtd contratos", len(v60))
        c18.metric("Valor total", f"R$ {v60['valorGlobal'].sum():,.2f}".replace(",", "X").replace(".", ",").replace("X", "."))
        c19.metric("Maior contrato", f"R$ {v60['valorGlobal'].max():,.2f}".replace(",", "X").replace(".", ",").replace("X", ".") if not v60.empty else "R$ 0,00")
        c20.metric("Média por contrato", f"R$ {v60['valorGlobal'].mean():,.2f}".replace(",", "X").replace(".", ",").replace("X", ".") if not v60.empty else "R$ 0,00")
        st.dataframe(v60.sort_values("dataVigenciaFinal"),use_container_width=True)
    with st.container():
        st.markdown("### ⏳ Vencendo entre 61 e 90 dias")
        c21, c22, c23, c24 = st.columns(4)
        c21.metric("Qtd contratos", len(v90))
        c22.metric("Valor total", f"R$ {v90['valorGlobal'].sum():,.2f}".replace(",", "X").replace(".", ",").replace("X", "."))
        c23.metric("Maior contrato", f"R$ {v90['valorGlobal'].max():,.2f}".replace(",", "X").replace(".", ",").replace("X", ".") if not v90.empty else "R$ 0,00")
        c24.metric("Média por contrato", f"R$ {v90['valorGlobal'].mean():,.2f}".replace(",", "X").replace(".", ",").replace("X", ".") if not v90.empty else "R$ 0,00")
        st.dataframe(v90.sort_values("dataVigenciaFinal"),use_container_width=True)
    with st.container():
        st.markdown("### 🔴 Contratos vencidos")
        c25, c26, c27, c28 = st.columns(4)
        c25.metric("Qtd contratos", len(vencidos))
        c26.metric("Valor total", f"R$ {vencidos['valorGlobal'].sum():,.2f}".replace(",", "X").replace(".", ",").replace("X", "."))
        c27.metric("Maior contrato", f"R$ {vencidos['valorGlobal'].max():,.2f}".replace(",", "X").replace(".", ",").replace("X", ".") if not vencidos.empty else "R$ 0,00")
        c28.metric("Média por contrato", f"R$ {vencidos['valorGlobal'].mean():,.2f}".replace(",", "X").replace(".", ",").replace("X", ".") if not vencidos.empty else "R$ 0,00")
        st.dataframe(vencidos.sort_values("dataVigenciaFinal"),use_container_width=True)

# ==================== ABA 3: ANÁLISES ====================
with tab3:
    st.subheader("Análises dos contratos")

    c1, c2, c3, c4, c5 = st.columns(5)
    c1.metric("Total de contratos", len(df))
    c2.metric("Contratos vigentes", len(df[df["status"] == "Vigente"]))
    c3.metric("Contratos vencidos", len(df[df["status"] == "Vencido"]))
    c4.metric("Valor total", f"R$ {df['valorGlobal'].sum():,.2f}".replace(",", "X").replace(".", ",").replace("X", "."))
    c5.metric("Valor médio", f"R$ {df['valorGlobal'].mean():,.2f}".replace(",", "X").replace(".", ",").replace("X", "."))
    
    c6, c7, c8, c9, c10 = st.columns(5)
    c6.metric("Valor vigente", f"R$ {df[df['status']=='Vigente']['valorGlobal'].sum():,.2f}".replace(",", "X").replace(".", ",").replace("X", "."))
    c7.metric("Valor vencido", f"R$ {df[df['status']=='Vencido']['valorGlobal'].sum():,.2f}".replace(",", "X").replace(".", ",").replace("X", "."))
    c8.metric("Fornecedores únicos", df["nomeRazaoSocialFornecedor"].nunique())
    c9.metric("Categorias ativas", df["nomeCategoria"].nunique())
    c10.metric("Modalidades usadas", df["nomeModalidadeCompra"].nunique())
    st.divider()

    # ============ EVOLUÇÃO TEMPORAL ============
    st.markdown("## 📈 Evolução Temporal")
    
    evolucao = df.groupby("ano").agg(contratos=("numeroContrato", "count"),valor=("valorGlobal", "sum")).reset_index()
    
    col1, col2 = st.columns(2)
    
    with col1: 
        st.markdown("### Contratos por ano")
        fig=px.bar(evolucao,x="ano",y="contratos",labels={"ano":"Ano","contratos":"Quantidade"})
        fig.update_xaxes(tickangle=0,tickmode="linear",dtick=1)
        st.plotly_chart(fig,use_container_width=True)
        st.caption(f"Média anual: {evolucao['contratos'].mean():.0f} contratos")

    with col2:
        st.markdown("### Valor contratado por ano")
        fig_valor = px.bar(evolucao, x="ano", y="valor", labels={"ano": "Ano", "valor": "Valor contratado (R$)"})
        fig_valor.update_xaxes(tickangle=0, tickmode="linear", dtick=1)
        fig_valor.update_yaxes(tickprefix="R$ ", separatethousands=True)
        st.plotly_chart(fig_valor, use_container_width=True)
        st.caption(f"Média anual: R$ {evolucao['valor'].mean():,.2f}".replace(",", "X").replace(".", ",").replace("X", "."))
    
    # Comparação ano a ano
    st.markdown("### 📊 Comparação detalhada por ano")
    evolucao["var_contratos_%"] = evolucao["contratos"].pct_change() * 100
    evolucao["var_valor_%"] = evolucao["valor"].pct_change() * 100
    evolucao["ticket_medio"] = evolucao["valor"] / evolucao["contratos"]
    st.dataframe(evolucao.style.format({
        "valor": "R$ {:,.2f}",
        "var_contratos_%": "{:.1f}%",
        "var_valor_%": "{:.1f}%",
        "ticket_medio": "R$ {:,.2f}"
    }), use_container_width=True)
    st.divider()

    # ============ ANÁLISE POR STATUS ============
    st.markdown("## 🔄 Análise por Status dos Contratos")
    
    status_analise = df.groupby("status").agg(quantidade=("numeroContrato", "count"),
            valor_total=("valorGlobal", "sum"), valor_medio=("valorGlobal", "mean"),
            valor_maximo=("valorGlobal", "max"), valor_minimo=("valorGlobal", "min")).reset_index()
    
    col1, col2, col3 = st.columns(3)
    
    with col1:
        st.markdown("### Quantidade por status")
        st.plotly_chart(px.bar(status_analise,x="status",y="quantidade",labels={"status":"Status","quantidade":"Quantidade"}),use_container_width=True)

    with col2:
        st.markdown("### Valor total por status")
        fig_total = px.bar(status_analise,x="status",y="valor_total",labels={"status":"Status","valor_total":"Valor total (R$)"})
        fig_total.update_yaxes(tickprefix="R$ ",separatethousands=True); st.plotly_chart(fig_total,use_container_width=True)

    with col3:
        st.markdown("### Ticket médio por status")
        fig_medio = px.bar(status_analise,x="status",y="valor_medio",labels={"status":"Status","valor_medio":"Valor médio (R$)"})
        fig_medio.update_yaxes(tickprefix="R$ ",separatethousands=True); st.plotly_chart(fig_medio,use_container_width=True)
        
    st.dataframe(status_analise.style.format({
        "valor_total": "R$ {:,.2f}",
        "valor_medio": "R$ {:,.2f}",
        "valor_maximo": "R$ {:,.2f}",
        "valor_minimo": "R$ {:,.2f}"
    }), use_container_width=True)
    st.divider()

    # ============ ANÁLISE POR CATEGORIA ============
    st.markdown("## 🏢 Análise por Categoria")
    
    cat_analise = df.groupby("nomeCategoria").agg(
        quantidade=("numeroContrato", "count"),
        valor_total=("valorGlobal", "sum"),
        valor_medio=("valorGlobal", "mean"),
        vigentes=("status", lambda x: (x == "Vigente").sum()),
        vencidos=("status", lambda x: (x == "Vencido").sum())
    ).reset_index().sort_values("valor_total", ascending=False)
    
    cat_analise["perc_vigentes"] = (cat_analise["vigentes"] / cat_analise["quantidade"] * 100).round(1)
    
    col1, col2 = st.columns(2)
    
    with col1:
        st.markdown("### Top 10 categorias - Quantidade")
        top_cat_qtd = cat_analise.head(10).sort_values("quantidade")
        st.plotly_chart(px.bar(top_cat_qtd,x="quantidade",y="nomeCategoria",orientation="h",labels={"quantidade":"Quantidade","nomeCategoria":"Categoria"}),use_container_width=True)

    with col2:
        st.markdown("### Top 10 categorias - Valor")
        top_cat_valor = cat_analise.head(10).sort_values("valor_total")
        fig_valor = px.bar(top_cat_valor,x="valor_total",y="nomeCategoria",orientation="h",labels={"valor_total":"Valor (R$)","nomeCategoria":"Categoria"}); fig_valor.update_xaxes(tickprefix="R$ ",separatethousands=True); st.plotly_chart(fig_valor,use_container_width=True)

    
    st.markdown("### Detalhamento completo por categoria")
    st.dataframe(cat_analise.style.format({
        "valor_total": "R$ {:,.2f}",
        "valor_medio": "R$ {:,.2f}",
        "perc_vigentes": "{:.1f}%"
    }), use_container_width=True)
    st.divider()

    # ============ ANÁLISE POR FORNECEDOR ============
    st.markdown("## 🏆 Análise por Fornecedor")
    
    forn_analise = df.groupby("nomeRazaoSocialFornecedor").agg(
        quantidade=("numeroContrato", "count"),
        valor_total=("valorGlobal", "sum"),
        valor_medio=("valorGlobal", "mean"),
        vigentes=("status", lambda x: (x == "Vigente").sum()),
        categorias=("nomeCategoria", "nunique")
    ).reset_index().sort_values("valor_total", ascending=False)
    
    forn_analise["participacao_%"] = (forn_analise["valor_total"] / forn_analise["valor_total"].sum() * 100).round(2)
    
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
        return "\n".join(linhas[:2])  # Máximo 2 linhas
    
    col1, col2 = st.columns(2)
    
    with col1:
        st.markdown("### Top 15 fornecedores - Valor total")
        top_forn = forn_analise.head(15).copy()
        top_forn["nome_curto"] = top_forn["nomeRazaoSocialFornecedor"].apply(quebrar_linha)
        top_forn = top_forn.sort_values("valor_total")
        fig_forn_valor = px.bar(top_forn,x="valor_total",y="nome_curto",orientation="h",labels={"valor_total":"Valor (R$)","nome_curto":"Fornecedor"})
        fig_forn_valor.update_xaxes(tickprefix="R$ ",separatethousands=True)
        st.plotly_chart(fig_forn_valor,use_container_width=True)

    with col2:
        st.markdown("### Top 15 fornecedores - Quantidade")
        top_forn_qtd = forn_analise.head(15).copy()
        top_forn_qtd["nome_curto"] = top_forn_qtd["nomeRazaoSocialFornecedor"].apply(quebrar_linha)
        top_forn_qtd = top_forn_qtd.sort_values("quantidade")
        st.plotly_chart(px.bar(top_forn_qtd,x="quantidade",y="nome_curto",orientation="h",labels={"quantidade":"Quantidade","nome_curto":"Fornecedor"}),use_container_width=True)

    
    st.markdown("### Concentração de fornecedores")
    c1, c2, c3, c4 = st.columns(4)
    top5_valor = forn_analise.head(5)["valor_total"].sum()
    top10_valor = forn_analise.head(10)["valor_total"].sum()
    c1.metric("Top 5 fornecedores", f"{(top5_valor/df['valorGlobal'].sum()*100):.1f}% do total")
    c2.metric("Top 10 fornecedores", f"{(top10_valor/df['valorGlobal'].sum()*100):.1f}% do total")
    c3.metric("Fornecedor dominante", f"{forn_analise.iloc[0]['participacao_%']:.1f}%")
    c4.metric("Fornecedores com 1 contrato", len(forn_analise[forn_analise["quantidade"] == 1]))
    
    st.markdown("### Detalhamento dos principais fornecedores")
    st.dataframe(forn_analise.head(20).style.format({
        "valor_total": "R$ {:,.2f}",
        "valor_medio": "R$ {:,.2f}",
        "participacao_%": "{:.2f}%"
    }), use_container_width=True)
    st.divider()

    # ============ ANÁLISE POR MODALIDADE ============
    st.markdown("## 📋 Análise por Modalidade de Compra")
    
    mod_analise = df.groupby("nomeModalidadeCompra").agg(
        quantidade=("numeroContrato", "count"),
        valor_total=("valorGlobal", "sum"),
        valor_medio=("valorGlobal", "mean")
    ).reset_index().sort_values("valor_total", ascending=False)
    
    mod_analise["participacao_%"] = (mod_analise["valor_total"] / mod_analise["valor_total"].sum() * 100).round(2)
    
    col1, col2 = st.columns(2)
    
    with col1:
        st.markdown("### Distribuição por modalidade")
        st.plotly_chart(px.bar(mod_analise,x="nomeModalidadeCompra",y="quantidade",labels={"nomeModalidadeCompra":"Modalidade","quantidade":"Quantidade"}),use_container_width=True)

    with col2:
        st.markdown("### Valor por modalidade")
        fig_mod = px.bar(mod_analise,x="nomeModalidadeCompra",y="valor_total",labels={"nomeModalidadeCompra":"Modalidade","valor_total":"Valor (R$)"})
        fig_mod.update_yaxes(tickprefix="R$ ",separatethousands=True); st.plotly_chart(fig_mod,use_container_width=True)

    
    st.dataframe(mod_analise.style.format({
        "valor_total": "R$ {:,.2f}",
        "valor_medio": "R$ {:,.2f}",
        "participacao_%": "{:.2f}%"
    }), use_container_width=True)
    st.divider()

    # ============ ANÁLISE POR TIPO ============
    st.markdown("## 📑 Análise por Tipo de Contrato")
    
    tipo_analise = df.groupby("nomeTipo").agg(
        quantidade=("numeroContrato", "count"),
        valor_total=("valorGlobal", "sum"),
        valor_medio=("valorGlobal", "mean")
    ).reset_index().sort_values("valor_total", ascending=False)
    
    col1, col2 = st.columns(2)
    
    with col1:
        st.markdown("### Quantidade por tipo")
        st.plotly_chart(px.bar(tipo_analise,x="nomeTipo",y="quantidade",labels={"nomeTipo":"Tipo","quantidade":"Quantidade"}),use_container_width=True)

    with col2:
        st.markdown("### Valor por tipo")
        fig_tipo = px.bar(tipo_analise,x="nomeTipo",y="valor_total",labels={"nomeTipo":"Tipo","valor_total":"Valor (R$)"})
        fig_tipo.update_yaxes(tickprefix="R$ ",separatethousands=True); st.plotly_chart(fig_tipo,use_container_width=True)

    
    st.dataframe(tipo_analise.style.format({
        "valor_total": "R$ {:,.2f}",
        "valor_medio": "R$ {:,.2f}"
    }), use_container_width=True)
    st.divider()

    # ============ ANÁLISE CRUZADA ============
    st.markdown("## 🔀 Análises Cruzadas")
    
    st.markdown("### Categoria × Status")
    cat_status = pd.crosstab(df["nomeCategoria"], df["status"], values=df["valorGlobal"], aggfunc="sum").fillna(0)
    st.dataframe(cat_status.style.format("R$ {:,.2f}"), use_container_width=True)
    
    st.markdown("### Modalidade × Ano")
    mod_ano = pd.crosstab(df["nomeModalidadeCompra"], df["ano"], values=df["valorGlobal"], aggfunc="sum").fillna(0)
    st.dataframe(mod_ano.style.format("R$ {:,.2f}"), use_container_width=True)
    st.divider()

    # ============ ANÁLISE DE UNIDADES ============
    st.markdown("## 🏛️ Análise por Unidade Realizadora")
    
    unid_analise = df.groupby("nomeUnidadeRealizadoraCompra").agg(
        quantidade=("numeroContrato", "count"),
        valor_total=("valorGlobal", "sum"),
        fornecedores=("nomeRazaoSocialFornecedor", "nunique"),
        categorias=("nomeCategoria", "nunique")
    ).reset_index().sort_values("valor_total", ascending=False)
    
    col1, col2 = st.columns(2)
    
    with col1:
        st.markdown("### Top 10 unidades - Contratos")
        top_unid = unid_analise.head(10).copy()
        top_unid["nome_curto"] = top_unid["nomeUnidadeRealizadoraCompra"].apply(quebrar_linha)
        top_unid = top_unid.sort_values("quantidade")
        st.plotly_chart(px.bar(top_unid,x="quantidade",y="nome_curto",orientation="h",labels={"quantidade":"Quantidade","nome_curto":"Unidade"}),use_container_width=True)

    with col2:
        st.markdown("### Top 10 unidades - Valor")
        top_unid_valor = unid_analise.head(10).copy()
        top_unid_valor["nome_curto"] = top_unid_valor["nomeUnidadeRealizadoraCompra"].apply(quebrar_linha)
        top_unid_valor = top_unid_valor.sort_values("valor_total")
        fig_unid = px.bar(top_unid_valor,x="valor_total",y="nome_curto",orientation="h",labels={"valor_total":"Valor (R$)","nome_curto":"Unidade"})
        fig_unid.update_xaxes(tickprefix="R$ ",separatethousands=True); st.plotly_chart(fig_unid,use_container_width=True)

    
    st.dataframe(unid_analise.head(15).style.format({
        "valor_total": "R$ {:,.2f}"
    }), use_container_width=True)
    st.divider()

    # ============ INDICADORES AVANÇADOS ============
    st.markdown("## 🎯 Indicadores Avançados")
    
    col1, col2, col3, col4 = st.columns(4)
    
    # Concentração
    hhi_fornecedor = ((forn_analise["participacao_%"] / 100) ** 2).sum()
    col1.metric("Índice HHI Fornecedores", f"{hhi_fornecedor:.4f}", 
                help="Índice de concentração (0=pulverizado, 1=monopólio)")
    
    # Taxa de renovação
    taxa_vigente = len(df[df["status"] == "Vigente"]) / len(df) * 100
    col2.metric("Taxa de vigência", f"{taxa_vigente:.1f}%")
    
    # Ticket médio
    ticket_vigente = df[df["status"] == "Vigente"]["valorGlobal"].mean()
    ticket_vencido = df[df["status"] == "Vencido"]["valorGlobal"].mean()
    col3.metric("Ticket vigente", f"R$ {ticket_vigente:,.2f}".replace(",", "X").replace(".", ",").replace("X", "."))
    col4.metric("Ticket vencido", f"R$ {ticket_vencido:,.2f}".replace(",", "X").replace(".", ",").replace("X", "."))
    
    st.markdown("### Distribuição de valores")
    c1, c2, c3, c4, c5 = st.columns(5)
    c1.metric("Mínimo", f"R$ {df['valorGlobal'].min():,.2f}".replace(",", "X").replace(".", ",").replace("X", "."))
    c2.metric("25º percentil", f"R$ {df['valorGlobal'].quantile(0.25):,.2f}".replace(",", "X").replace(".", ",").replace("X", "."))
    c3.metric("Mediana", f"R$ {df['valorGlobal'].median():,.2f}".replace(",", "X").replace(".", ",").replace("X", "."))
    c4.metric("75º percentil", f"R$ {df['valorGlobal'].quantile(0.75):,.2f}".replace(",", "X").replace(".", ",").replace("X", "."))
    c5.metric("Máximo", f"R$ {df['valorGlobal'].max():,.2f}".replace(",", "X").replace(".", ",").replace("X", "."))

# ==================== ABA 4: VISÃO GERAL & FILTROS ====================
with tab4:
    st.header("Análise Financeira")
    
    # Filtros em colunas
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
    
    # Aplicar filtros
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
    
    # Mostrar indicadores principais em cards
    st.subheader("📊 Indicadores Financeiros Principais")
    
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        st.metric("Limite de Gastos", formatar_real(limite_gastos), 
                 help="Valor Limite Disponível")
        st.metric("Valor Empenhado", formatar_real(valor_empenhado), 
                 help="Soma dos empenhos totais")
    
    with col2:
        st.metric("Valor Pago", formatar_real(valor_pago),
                 help="Soma dos valores pagos")
        st.metric("Valor a Pagar", formatar_real(valor_a_pagar),
                 help="Empenhado - Pago")
    
    with col3:
        st.metric("Pré-Empenhado", formatar_real(valor_pre_empenhado),
                 help="Valor de pré-empenhos a empenhar")
        st.metric("Limite Disponível", formatar_real(limite_disponivel),
                 help="Limite - Pré-Empenhos - Empenhos")
    
    with col4:
        # Indicador de execução
        perc_execucao = (valor_empenhado / limite_gastos * 100) if limite_gastos > 0 else 0
        st.metric("Execução Orçamentária", formatar_percentual(perc_execucao),
                 help="Percentual do limite que foi empenhado")
        
        # Indicador de pagamento
        perc_pagamento = (valor_pago / valor_empenhado * 100) if valor_empenhado > 0 else 0
        st.metric("Taxa de Pagamento", formatar_percentual(perc_pagamento),
                 help="Percentual do empenhado que foi pago")
    
    st.markdown("---")
    
    # Gráficos de análise temporal
    st.subheader("📈 Análise Temporal")
    
    col1, col2 = st.columns(2)
    
    with col1:
        # Evolução por ano
        evolucao_ano = df_filtered.groupby('Ano').agg({
            'Limite': 'sum',
            'Empenhado': 'sum',
            'Valor Empenhos Pagos': 'sum'
        }).reset_index()
        
        fig_evolucao = go.Figure()
        fig_evolucao.add_trace(go.Bar(
            name='Limite',
            x=evolucao_ano['Ano'],
            y=evolucao_ano['Limite'],
            marker_color='lightblue'
        ))
        fig_evolucao.add_trace(go.Bar(
            name='Empenhado',
            x=evolucao_ano['Ano'],
            y=evolucao_ano['Empenhado'],
            marker_color='#0068c9'
        ))
        fig_evolucao.add_trace(go.Bar(
            name='Pago',
            x=evolucao_ano['Ano'],
            y=evolucao_ano['Valor Empenhos Pagos'],
            marker_color='#28a745'
        ))
        
        fig_evolucao.update_layout(
            title="Evolução Anual dos Valores",
            xaxis_title="Ano",
            yaxis_title="Valor (R$)",
            barmode='group',
            height=400
        )
        
        st.plotly_chart(fig_evolucao, use_container_width=True)
    
    with col2:
        # Distribuição do orçamento - apenas valores positivos
        valores_dist = {
            'Empenhado': max(0, valor_empenhado),
            'Pago': max(0, valor_pago),
            'A Pagar': max(0, valor_a_pagar)
        }
        
        # Filtrar apenas valores > 0
        valores_dist = {k: v for k, v in valores_dist.items() if v > 0}
        
        if valores_dist:
            fig_dist = go.Figure(data=[go.Pie(
                labels=list(valores_dist.keys()),
                values=list(valores_dist.values()),
                hole=0.4,
                marker=dict(colors=['#0068c9', '#28a745', '#ffc107']),
                textinfo='label+percent',
                textposition='outside'
            )])
            
            fig_dist.update_layout(
                title="Distribuição dos Empenhos",
                height=400,
                showlegend=True
            )
            
            st.plotly_chart(fig_dist, use_container_width=True)
        else:
            st.info("Sem dados para exibir no gráfico de distribuição")
    
    # Tabela resumo
    st.subheader("📋 Resumo Detalhado por Ano")
    
    resumo_ano = df_filtered.groupby('Ano').agg({
        'Limite': 'sum',
        'Pré-empenhado': 'sum',
        'Empenhado': 'sum',
        'Valor Empenhos Pagos': 'sum'
    }).reset_index()
    
    resumo_ano['Disponível'] = (resumo_ano['Limite'] - 
                                 resumo_ano['Pré-empenhado'] - 
                                 resumo_ano['Empenhado'])
    resumo_ano['A Pagar'] = resumo_ano['Empenhado'] - resumo_ano['Valor Empenhos Pagos']
    resumo_ano['% Execução'] = resumo_ano.apply(
        lambda row: (row['Empenhado'] / row['Limite'] * 100) if row['Limite'] > 0 else 0,
        axis=1
    )
    
    # Formatar valores
    resumo_display = resumo_ano.copy()
    for col in ['Limite', 'Pré-empenhado', 'Empenhado', 'Valor Empenhos Pagos', 'Disponível', 'A Pagar']:
        resumo_display[col] = resumo_display[col].apply(formatar_real)
    resumo_display['% Execução'] = resumo_display['% Execução'].apply(formatar_percentual)
    
    st.dataframe(resumo_display, use_container_width=True)

# ==================== ABA 5: ANÁLISE POR GESTORES ====================
with tab5:
    st.header("Perfil dos Gestores")
    
    # FILTROS EDITÁVEIS NESTA ABA
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
    
    # Aplicar filtros locais
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
        # Métricas por gestor
        gestores_agg = df_gestores.groupby('Gestor(a)').agg({
            'Limite': 'sum',
            'Empenhado': 'sum',
            'Valor Empenhos Pagos': 'sum',
            'Pré-empenhado': 'sum'
        }).reset_index()
        
        gestores_agg['Disponível'] = (gestores_agg['Limite'] - 
                                      gestores_agg['Pré-empenhado'] - 
                                      gestores_agg['Empenhado'])
        gestores_agg['% Execução'] = gestores_agg.apply(
            lambda row: (row['Empenhado'] / row['Limite'] * 100) if row['Limite'] > 0 else 0,
            axis=1
        )
        
        # KPIs resumo
        col1, col2, col3, col4 = st.columns(4)
        with col1:
            st.metric("Total Gestores", len(gestores_agg))
        with col2:
            st.metric("Total Empenhado", formatar_real(gestores_agg['Empenhado'].sum()))
        with col3:
            st.metric("Total Pago", formatar_real(gestores_agg['Valor Empenhos Pagos'].sum()))
        with col4:
            st.metric("% Execução Média", formatar_percentual(gestores_agg['% Execução'].mean()))
        
        st.markdown("---")
        
        # Top 10 gestores por execução
        st.subheader("🏆 Top 10 Gestores por Valor Empenhado")
        
        top_gestores = gestores_agg.nlargest(10, 'Empenhado')
        
        fig_top_gestores = go.Figure()
        fig_top_gestores.add_trace(go.Bar(
            x=top_gestores['Empenhado'],
            y=top_gestores['Gestor(a)'],
            orientation='h',
            marker_color='#0068c9',
            text=top_gestores['Empenhado'].apply(lambda x: formatar_real(x)),
            textposition='auto'
        ))
        
        fig_top_gestores.update_layout(
            title="Top 10 Gestores - Valor Empenhado",
            xaxis_title="Valor (R$)",
            yaxis_title="",
            height=500,
            yaxis={'categoryorder':'total ascending'}
        )
        
        st.plotly_chart(fig_top_gestores, use_container_width=True)
        
        # Gráficos comparativos
        col1, col2 = st.columns(2)
        
        with col1:
            # % Execução dos gestores - CORRIGIDO (não vazio mais)
            st.subheader("📊 Top 15 Gestores - % Execução")
            top_exec = gestores_agg.nlargest(15, '% Execução')
            
            fig_exec = go.Figure()
            fig_exec.add_trace(go.Bar(
                x=top_exec['% Execução'],
                y=top_exec['Gestor(a)'],
                orientation='h',
                marker_color='#17a2b8',
                text=top_exec['% Execução'].apply(formatar_percentual),
                textposition='auto'
            ))
            
            fig_exec.update_layout(
                xaxis_title="% Execução",
                yaxis_title="",
                height=500,
                yaxis={'categoryorder':'total ascending'}
            )
            
            st.plotly_chart(fig_exec, use_container_width=True)
        
        with col2:
            # Empenhado vs Pago - EIXOS TROCADOS (Y=Gestor, X=Valor)
            st.subheader("💰 Top 15 Gestores - Empenhado vs Pago")
            top_gestores_pag = gestores_agg.nlargest(15, 'Empenhado')
            
            fig_emp_pago = go.Figure()
            fig_emp_pago.add_trace(go.Bar(
                name='Empenhado',
                y=top_gestores_pag['Gestor(a)'],
                x=top_gestores_pag['Empenhado'],
                orientation='h',
                marker_color='#0068c9'
            ))
            fig_emp_pago.add_trace(go.Bar(
                name='Pago',
                y=top_gestores_pag['Gestor(a)'],
                x=top_gestores_pag['Valor Empenhos Pagos'],
                orientation='h',
                marker_color='#28a745'
            ))
            
            fig_emp_pago.update_layout(
                barmode='group',
                height=500,
                xaxis_title="Valor (R$)",
                yaxis_title="",
                yaxis={'categoryorder':'total ascending'}
            )
            
            st.plotly_chart(fig_emp_pago, use_container_width=True)
        
        # Mais análises
        st.markdown("---")
        st.subheader("📈 Análises Adicionais")
        
        col1, col2 = st.columns(2)
        
        with col1:
            # Distribuição de limites
            st.markdown("#### Distribuição de Limites por Gestor")
            top_limites = gestores_agg.nlargest(10, 'Limite')
            
            fig_limites = go.Figure(data=[go.Pie(
                labels=top_limites['Gestor(a)'],
                values=top_limites['Limite'],
                hole=0.4
            )])
            
            fig_limites.update_layout(height=400)
            st.plotly_chart(fig_limites, use_container_width=True)
        
        with col2:
            # Taxa de pagamento
            st.markdown("#### Taxa de Pagamento por Gestor")
            gestores_agg['Taxa Pagamento'] = gestores_agg.apply(
                lambda row: (row['Valor Empenhos Pagos'] / row['Empenhado'] * 100) if row['Empenhado'] > 0 else 0,
                axis=1
            )
            top_pagamento = gestores_agg.nlargest(10, 'Taxa Pagamento')
            
            fig_taxa = go.Figure()
            fig_taxa.add_trace(go.Bar(
                x=top_pagamento['Taxa Pagamento'],
                y=top_pagamento['Gestor(a)'],
                orientation='h',
                marker_color='#28a745',
                text=top_pagamento['Taxa Pagamento'].apply(formatar_percentual),
                textposition='auto'
            ))
            
            fig_taxa.update_layout(
                xaxis_title="Taxa de Pagamento (%)",
                yaxis_title="",
                height=400,
                yaxis={'categoryorder':'total ascending'}
            )
            
            st.plotly_chart(fig_taxa, use_container_width=True)
        
        # Tabela detalhada COM COLUNA ANO
        st.markdown("---")
        st.subheader("📋 Tabela Detalhada por Gestor e Ano")
        
        # Agrupar por Ano E Gestor
        gestores_ano_agg = df_gestores.groupby(['Ano', 'Gestor(a)']).agg({
            'Limite': 'sum',
            'Empenhado': 'sum',
            'Valor Empenhos Pagos': 'sum',
            'Pré-empenhado': 'sum'
        }).reset_index()
        
        gestores_ano_agg['Disponível'] = (gestores_ano_agg['Limite'] - 
                                          gestores_ano_agg['Pré-empenhado'] - 
                                          gestores_ano_agg['Empenhado'])
        gestores_ano_agg['% Execução'] = gestores_ano_agg.apply(
            lambda row: (row['Empenhado'] / row['Limite'] * 100) if row['Limite'] > 0 else 0,
            axis=1
        )
        
        gestores_display = gestores_ano_agg.copy()
        for col in ['Limite', 'Empenhado', 'Valor Empenhos Pagos', 'Pré-empenhado', 'Disponível']:
            gestores_display[col] = gestores_display[col].apply(formatar_real)
        gestores_display['% Execução'] = gestores_display['% Execução'].apply(formatar_percentual)
        
        st.dataframe(gestores_display, use_container_width=True, height=400)

# ==================== ABA 6: ANÁLISE POR CENTRO DE CUSTOS ====================
with tab6:
    st.header("Análise por Centro de Custos")
    
    # FILTROS EDITÁVEIS NESTA ABA
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
    
    # Aplicar filtros locais
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
        # Métricas por centro de custo
        centros_agg = df_centros.groupby('Centro de Custo').agg({
            'Limite': 'sum',
            'Empenhado': 'sum',
            'Valor Empenhos Pagos': 'sum',
            'Pré-empenhado': 'sum'
        }).reset_index()
        
        centros_agg['Disponível'] = (centros_agg['Limite'] - 
                                     centros_agg['Pré-empenhado'] - 
                                     centros_agg['Empenhado'])
        centros_agg['A Pagar'] = centros_agg['Empenhado'] - centros_agg['Valor Empenhos Pagos']
        centros_agg['% Execução'] = (centros_agg['Empenhado'] / 
                                    centros_agg['Limite'] * 100)
        
        # Top 20 centros
        st.subheader("🏆 Top 20 Centros de Custo por Valor Empenhado")
        
        top_centros = centros_agg.nlargest(20, 'Empenhado')
        
        fig_top_centros = go.Figure()
        fig_top_centros.add_trace(go.Bar(
            x=top_centros['Empenhado'],
            y=top_centros['Centro de Custo'],
            orientation='h',
            marker_color='#0068c9',
            text=top_centros['Empenhado'].apply(lambda x: f'R$ {x/1e6:.1f}M'),
            textposition='auto'
        ))
        
        fig_top_centros.update_layout(
            height=700,
            xaxis_title="Valor Empenhado (R$)",
            yaxis_title="",
            yaxis={'categoryorder':'total ascending'}
        )
        
        st.plotly_chart(fig_top_centros, use_container_width=True)
        
        # Análises comparativas
        st.subheader("📊 Análises Comparativas")
        
        col1, col2 = st.columns(2)
        
        with col1:
            # Centros com maior valor a pagar
            top_a_pagar = centros_agg.nlargest(15, 'A Pagar')
            
            fig_a_pagar = go.Figure()
            fig_a_pagar.add_trace(go.Bar(
                x=top_a_pagar['A Pagar'],
                y=top_a_pagar['Centro de Custo'],
                orientation='h',
                marker_color='#ffc107',
                text=top_a_pagar['A Pagar'].apply(lambda x: f'R$ {x/1000:.0f}K'),
                textposition='auto'
            ))
            
            fig_a_pagar.update_layout(
                title="Top 15 Centros - Maior Valor a Pagar",
                height=500,
                xaxis_title="Valor a Pagar (R$)",
                yaxis_title="",
                yaxis={'categoryorder':'total ascending'}
            )
            
            st.plotly_chart(fig_a_pagar, use_container_width=True)
        
        with col2:
            # Distribuição de limites
            top_limites = centros_agg.nlargest(10, 'Limite')
            
            fig_limites = go.Figure(data=[go.Pie(
                labels=top_limites['Centro de Custo'],
                values=top_limites['Limite'],
                hole=0.4
            )])
            
            fig_limites.update_layout(
                title="Top 10 Centros - Distribuição de Limites",
                height=500
            )
            
            st.plotly_chart(fig_limites, use_container_width=True)
        
        # Tabela detalhada
        st.subheader("📋 Tabela Detalhada por Centro de Custo")
        
        # Filtro de busca
        busca_centro = st.text_input("🔍 Buscar Centro de Custo:", "")
        
        centros_display = centros_agg.copy()
        if busca_centro:
            centros_display = centros_display[
                centros_display['Centro de Custo'].str.contains(busca_centro, case=False, na=False)
            ]
        
        for col in ['Limite', 'Empenhado', 
                    'Valor Empenhos Pagos', 'Pré-empenhado', 
                    'Disponível', 'A Pagar']:
            centros_display[col] = centros_display[col].apply(lambda x: f'R$ {x:,.2f}')
        centros_display['% Execução'] = centros_display['% Execução'].apply(lambda x: f'{x:.1f}%')
        
        centros_display.columns = ['Centro de Custo', 'Limite', 'Empenhado', 'Pago', 
                                  'Pré-Empenhado', 'Disponível', 'A Pagar', '% Execução']
        
        st.dataframe(centros_display, use_container_width=True)

# ==================== ABA 7: EMPENHOS DETALHADOS ====================
with tab7:
    st.header("Empenhos Detalhados")
    
    if len(df_empenhos) == 0:
        st.warning("Dados de empenhos não disponíveis.")
    else:
        # FILTROS EDITÁVEIS
        col1_f, col2_f, col3_f = st.columns(3)
        
        with col1_f:
            if 'Ano' in df_empenhos.columns:
                anos_emp = sorted(df_empenhos['Ano'].dropna().unique().tolist())
                ano_emp = st.multiselect("Ano", options=anos_emp, default=[], key="ano_emp")
        
        with col2_f:
            if 'Favorecido' in df_empenhos.columns:
                # Não mostrar "Não informado" nas opções
                favorecidos = sorted([f for f in df_empenhos['Favorecido'].unique() if f != 'Não informado'][:100])
                favorecido_emp = st.selectbox("Favorecido", options=['Todos'] + favorecidos, key="fav_emp")
        
        with col3_f:
            if 'Grupo' in df_empenhos.columns:
                grupos = sorted(df_empenhos['Grupo'].dropna().unique().tolist())
                grupo_emp = st.multiselect("Grupo", options=grupos, default=[], key="grupo_emp")
        
        # Aplicar filtros
        df_empenhos_filtered = df_empenhos.copy()
        
        if 'Ano' in df_empenhos.columns and ano_emp:
            df_empenhos_filtered = df_empenhos_filtered[df_empenhos_filtered['Ano'].isin(ano_emp)]
        
        if 'Favorecido' in df_empenhos.columns and favorecido_emp != 'Todos':
            df_empenhos_filtered = df_empenhos_filtered[df_empenhos_filtered['Favorecido'] == favorecido_emp]
        
        if 'Grupo' in df_empenhos.columns and grupo_emp:
            df_empenhos_filtered = df_empenhos_filtered[df_empenhos_filtered['Grupo'].isin(grupo_emp)]
        
        st.markdown("---")
        
        # KPIs
        col1, col2, col3, col4 = st.columns(4)
        with col1:
            st.metric("Total Empenhos", f"{len(df_empenhos_filtered):,}")
        with col2:
            if 'Valor Empenhado' in df_empenhos_filtered.columns:
                st.metric("Valor Empenhado", formatar_real(df_empenhos_filtered['Valor Empenhado'].sum()))
        with col3:
            if 'Valor Pago' in df_empenhos_filtered.columns:
                st.metric("Valor Pago", formatar_real(df_empenhos_filtered['Valor Pago'].sum()))
        with col4:
            if 'R$ a pagar' in df_empenhos_filtered.columns:
                st.metric("A Pagar", formatar_real(df_empenhos_filtered['R$ a pagar'].sum()))
        
        st.markdown("---")
        
        # Análises gráficas
        col1, col2 = st.columns(2)
        
        with col1:
            # Top 15 Favorecidos - CORRIGIDO
            if 'Favorecido' in df_empenhos_filtered.columns and 'Valor Empenhado' in df_empenhos_filtered.columns:
                st.subheader("👥 Top 15 Favorecidos")
                favorecidos_agg = df_empenhos_filtered.groupby('Favorecido')['Valor Empenhado'].sum().nlargest(15)
                
                fig_fav = go.Figure()
                fig_fav.add_trace(go.Bar(
                    x=favorecidos_agg.values,
                    y=favorecidos_agg.index,
                    orientation='h',
                    marker_color='#0068c9',
                    text=[formatar_real(v) for v in favorecidos_agg.values],
                    textposition='auto'
                ))
                
                fig_fav.update_layout(
                    xaxis_title="Valor Empenhado (R$)",
                    yaxis_title="",
                    height=500,
                    yaxis={'categoryorder':'total ascending'}
                )
                
                st.plotly_chart(fig_fav, use_container_width=True)
        
        with col2:
            # Por Grupo de Despesa
            if 'Grupo' in df_empenhos_filtered.columns and 'Valor Empenhado' in df_empenhos_filtered.columns:
                st.subheader("📊 Por Grupo de Despesa")
                grupo_agg = df_empenhos_filtered.groupby('Grupo')['Valor Empenhado'].sum().nlargest(10)
                
                fig_grupo = go.Figure(data=[go.Pie(
                    labels=grupo_agg.index,
                    values=grupo_agg.values,
                    hole=0.4,
                    textinfo='label+percent',
                    textposition='outside'
                )])
                
                fig_grupo.update_layout(height=500, showlegend=False)
                st.plotly_chart(fig_grupo, use_container_width=True)
        
        # Gráfico de Natureza - COMPLETAMENTE REFORMULADO
        st.markdown("---")
        st.subheader("💰 Por Natureza de Despesa")
        
        if 'Natureza' in df_empenhos_filtered.columns and 'Valor Empenhado' in df_empenhos_filtered.columns:
            natureza_agg = df_empenhos_filtered.groupby('Natureza')['Valor Empenhado'].sum().nlargest(20)
            
            if len(natureza_agg) > 0:
                fig_natureza = go.Figure()
                fig_natureza.add_trace(go.Bar(
                    x=natureza_agg.values,
                    y=natureza_agg.index,
                    orientation='h',
                    marker_color='#17a2b8',
                    text=[formatar_real(v) for v in natureza_agg.values],
                    textposition='auto'
                ))
                
                fig_natureza.update_layout(
                    title="Top 20 Naturezas de Despesa",
                    xaxis_title="Valor Empenhado (R$)",
                    yaxis_title="Natureza",
                    height=700,
                    yaxis={'categoryorder':'total ascending'}
                )
                
                st.plotly_chart(fig_natureza, use_container_width=True)
            else:
                st.info("Sem dados de natureza para exibir")
        
        # Análise temporal
        if 'Data Emissão' in df_empenhos_filtered.columns:
            st.markdown("---")
            st.subheader("📅 Evolução Temporal")
            
            df_temp = df_empenhos_filtered.copy()
            df_temp['Data Emissão'] = pd.to_datetime(df_temp['Data Emissão'], errors='coerce')
            df_temp = df_temp.dropna(subset=['Data Emissão'])
            
            if len(df_temp) > 0:
                df_temp['Mês/Ano'] = df_temp['Data Emissão'].dt.to_period('M').astype(str)
                temporal_agg = df_temp.groupby('Mês/Ano')['Valor Empenhado'].sum().tail(12)
                
                fig_temp = go.Figure()
                fig_temp.add_trace(go.Scatter(
                    x=temporal_agg.index,
                    y=temporal_agg.values,
                    mode='lines+markers',
                    name='Valor Empenhado',
                    line=dict(color='#0068c9', width=3),
                    marker=dict(size=8)
                ))
                
                fig_temp.update_layout(
                    title="Evolução dos Empenhos (Últimos 12 meses)",
                    xaxis_title="Mês/Ano",
                    yaxis_title="Valor (R$)",
                    height=400
                )
                
                st.plotly_chart(fig_temp, use_container_width=True)
        
        # Tabela detalhada
        st.markdown("---")
        st.subheader("📋 Tabela Detalhada de Empenhos")
        
        busca_emp = st.text_input("🔍 Buscar (Empenho, Favorecido, Processo):", "", key="busca_emp")
        
        df_emp_display = df_empenhos_filtered.copy()
        if busca_emp:
            mask = False
            for col in ['Empenho', 'Favorecido', 'Processo']:
                if col in df_emp_display.columns:
                    mask = mask | df_emp_display[col].astype(str).str.contains(busca_emp, case=False, na=False)
            df_emp_display = df_emp_display[mask]
        
        # Mostrar primeiros 100 registros
        df_emp_display = df_emp_display.head(100)
        
        # Formatar valores monetários
        for col in ['Valor Empenhado', 'Valor Pago', 'R$ a pagar']:
            if col in df_emp_display.columns:
                df_emp_display[col] = df_emp_display[col].apply(formatar_real)
        
        st.dataframe(df_emp_display, use_container_width=True, height=400)
        st.info(f"📊 Exibindo {len(df_emp_display):,} de {len(df_empenhos_filtered):,} registros (limite: 100)")

# ==================== ABA 8: PRÉ-EMPENHOS ====================
with tab8:
    st.header("Pré-Empenhos")
    
    if len(df_pre_empenhos) == 0:
        st.warning("Dados de pré-empenhos não disponíveis.")
    else:
        # Filtros
        col1_f, col2_f = st.columns(2)
        
        with col1_f:
            if 'Ano' in df_pre_empenhos.columns:
                anos_pre = sorted(df_pre_empenhos['Ano'].dropna().unique().tolist())
                ano_pre = st.multiselect("Ano", options=anos_pre, default=[], key="ano_pre")
        
        with col2_f:
            if 'Favorecido' in df_pre_empenhos.columns:
                favorecidos_pre = sorted(df_pre_empenhos['Favorecido'].dropna().unique().tolist()[:100])
                favorecido_pre = st.selectbox("Favorecido", options=['Todos'] + favorecidos_pre, key="fav_pre")
        
        # Aplicar filtros
        df_pre_filtered = df_pre_empenhos.copy()
        
        if 'Ano' in df_pre_empenhos.columns and ano_pre:
            df_pre_filtered = df_pre_filtered[df_pre_filtered['Ano'].isin(ano_pre)]
        
        if 'Favorecido' in df_pre_empenhos.columns and favorecido_pre != 'Todos':
            df_pre_filtered = df_pre_filtered[df_pre_filtered['Favorecido'] == favorecido_pre]
        
        st.markdown("---")
        
        # KPIs
        col1, col2, col3 = st.columns(3)
        with col1:
            st.metric("Total Pré-Empenhos", f"{len(df_pre_filtered):,}")
        with col2:
            if 'Valor Pré-Empenhado' in df_pre_filtered.columns:
                st.metric("Valor Total", formatar_real(df_pre_filtered['Valor Pré-Empenhado'].sum()))
        with col3:
            if 'Ano' in df_pre_filtered.columns:
                st.metric("Anos Cobertos", df_pre_filtered['Ano'].nunique())
        
        st.markdown("---")
        
        # Gráficos
        col1, col2 = st.columns(2)
        
        with col1:
            # Top Favorecidos
            if 'Favorecido' in df_pre_filtered.columns and 'Valor Pré-Empenhado' in df_pre_filtered.columns:
                st.subheader("👥 Top 15 Favorecidos")
                fav_agg = df_pre_filtered.groupby('Favorecido')['Valor Pré-Empenhado'].sum().nlargest(15)
                
                fig_fav_pre = go.Figure()
                fig_fav_pre.add_trace(go.Bar(
                    x=fav_agg.values,
                    y=fav_agg.index,
                    orientation='h',
                    marker_color='#ffc107',
                    text=[formatar_real(v) for v in fav_agg.values],
                    textposition='auto'
                ))
                
                fig_fav_pre.update_layout(
                    xaxis_title="Valor (R$)",
                    yaxis_title="",
                    height=500,
                    yaxis={'categoryorder':'total ascending'}
                )
                
                st.plotly_chart(fig_fav_pre, use_container_width=True)
        
        with col2:
            # Gráfico de Grupo de Despesas - MELHORADO
            if 'Grupo Despesa' in df_pre_filtered.columns and 'Valor Pré-Empenhado' in df_pre_filtered.columns:
                st.subheader("📊 Por Grupo de Despesa")
                grupo_pre_agg = df_pre_filtered.groupby('Grupo Despesa')['Valor Pré-Empenhado'].sum().nlargest(15)
                
                if len(grupo_pre_agg) > 0:
                    fig_grupo_pre = go.Figure()
                    fig_grupo_pre.add_trace(go.Bar(
                        x=grupo_pre_agg.values,
                        y=grupo_pre_agg.index,
                        orientation='h',
                        marker_color='#17a2b8',
                        text=[formatar_real(v) for v in grupo_pre_agg.values],
                        textposition='auto'
                    ))
                    
                    fig_grupo_pre.update_layout(
                        xaxis_title="Valor (R$)",
                        yaxis_title="Grupo de Despesa",
                        height=500,
                        yaxis={'categoryorder':'total ascending'}
                    )
                    
                    st.plotly_chart(fig_grupo_pre, use_container_width=True)
                else:
                    st.info("Sem dados de grupo de despesa")
        
        # Evolução temporal
        if 'Ano' in df_pre_filtered.columns and 'Valor Pré-Empenhado' in df_pre_filtered.columns:
            st.markdown("---")
            st.subheader("📈 Evolução Anual")
            
            ano_agg = df_pre_filtered.groupby('Ano')['Valor Pré-Empenhado'].sum()
            
            fig_ano_pre = go.Figure()
            fig_ano_pre.add_trace(go.Bar(
                x=ano_agg.index,
                y=ano_agg.values,
                marker_color='#ffc107',
                text=[formatar_real(v) for v in ano_agg.values],
                textposition='auto'
            ))
            
            fig_ano_pre.update_layout(
                title="Pré-Empenhos por Ano",
                xaxis_title="Ano",
                yaxis_title="Valor (R$)",
                height=400
            )
            
            st.plotly_chart(fig_ano_pre, use_container_width=True)
        
        # Tabela
        st.markdown("---")
        st.subheader("📋 Tabela de Pré-Empenhos")
        
        busca_pre = st.text_input("🔍 Buscar:", "", key="busca_pre")
        
        df_pre_display = df_pre_filtered.copy()
        if busca_pre:
            mask = False
            for col in ['Pré-Empenho', 'Favorecido', 'Processo']:
                if col in df_pre_display.columns:
                    mask = mask | df_pre_display[col].astype(str).str.contains(busca_pre, case=False, na=False)
            df_pre_display = df_pre_display[mask]
        
        df_pre_display = df_pre_display.head(100)
        
        if 'Valor Pré-Empenhado' in df_pre_display.columns:
            df_pre_display['Valor Pré-Empenhado'] = df_pre_display['Valor Pré-Empenhado'].apply(formatar_real)
        
        st.dataframe(df_pre_display, use_container_width=True, height=400)

# ==================== ABA 9: RESTOS A PAGAR ====================
with tab9:
    st.header("Restos a Pagar")
    
    if len(df_rp) == 0:
        st.warning("Dados de restos a pagar não disponíveis.")
    else:
        # Filtros
        col1_f, col2_f = st.columns(2)
        
        with col1_f:
            if 'Favorecido' in df_rp.columns:
                favorecidos_rp = sorted(df_rp['Favorecido'].dropna().unique().tolist()[:100])
                favorecido_rp = st.selectbox("Favorecido", options=['Todos'] + favorecidos_rp, key="fav_rp")
        
        with col2_f:
            if 'Grupo' in df_rp.columns:
                grupos_rp = sorted(df_rp['Grupo'].dropna().unique().tolist())
                grupo_rp = st.multiselect("Grupo", options=grupos_rp, default=[], key="grupo_rp")
        
        # Aplicar filtros
        df_rp_filtered = df_rp.copy()
        
        if 'Favorecido' in df_rp.columns and favorecido_rp != 'Todos':
            df_rp_filtered = df_rp_filtered[df_rp_filtered['Favorecido'] == favorecido_rp]
        
        if 'Grupo' in df_rp.columns and grupo_rp:
            df_rp_filtered = df_rp_filtered[df_rp_filtered['Grupo'].isin(grupo_rp)]
        
        st.markdown("---")
        
        # KPIs
        col1, col2, col3, col4 = st.columns(4)
        with col1:
            if 'RP Inscritos' in df_rp_filtered.columns:
                st.metric("RP Inscritos", formatar_real(df_rp_filtered['RP Inscritos'].sum()))
        with col2:
            if 'RP Pagos' in df_rp_filtered.columns:
                st.metric("RP Pagos", formatar_real(df_rp_filtered['RP Pagos'].sum()))
        with col3:
            if 'RP Cancelados' in df_rp_filtered.columns:
                st.metric("RP Cancelados", formatar_real(df_rp_filtered['RP Cancelados'].sum()))
        with col4:
            if 'RP a Pagar' in df_rp_filtered.columns:
                st.metric("RP a Pagar", formatar_real(df_rp_filtered['RP a Pagar'].sum()))
        
        st.markdown("---")
        
        # Gráficos
        col1, col2 = st.columns(2)
        
        with col1:
            # Top Favorecidos
            if 'Favorecido' in df_rp_filtered.columns and 'RP a Pagar' in df_rp_filtered.columns:
                st.subheader("👥 Top 15 Favorecidos - RP a Pagar")
                fav_rp_agg = df_rp_filtered.groupby('Favorecido')['RP a Pagar'].sum().nlargest(15)
                
                fig_fav_rp = go.Figure()
                fig_fav_rp.add_trace(go.Bar(
                    x=fav_rp_agg.values,
                    y=fav_rp_agg.index,
                    orientation='h',
                    marker_color='#dc3545',
                    text=[formatar_real(v) for v in fav_rp_agg.values],
                    textposition='auto'
                ))
                
                fig_fav_rp.update_layout(
                    xaxis_title="Valor (R$)",
                    yaxis_title="",
                    height=500,
                    yaxis={'categoryorder':'total ascending'}
                )
                
                st.plotly_chart(fig_fav_rp, use_container_width=True)
        
        with col2:
            # Gráfico de Natureza - MELHORADO
            if 'Natureza' in df_rp_filtered.columns and 'RP a Pagar' in df_rp_filtered.columns:
                st.subheader("💰 Por Natureza de Despesa")
                natureza_rp_agg = df_rp_filtered.groupby('Natureza')['RP a Pagar'].sum().nlargest(15)
                
                if len(natureza_rp_agg) > 0:
                    fig_nat_rp = go.Figure()
                    fig_nat_rp.add_trace(go.Bar(
                        x=natureza_rp_agg.values,
                        y=natureza_rp_agg.index,
                        orientation='h',
                        marker_color='#6c757d',
                        text=[formatar_real(v) for v in natureza_rp_agg.values],
                        textposition='auto'
                    ))
                    
                    fig_nat_rp.update_layout(
                        xaxis_title="Valor (R$)",
                        yaxis_title="Natureza",
                        height=500,
                        yaxis={'categoryorder':'total ascending'}
                    )
                    
                    st.plotly_chart(fig_nat_rp, use_container_width=True)
                else:
                    st.info("Sem dados de natureza")
        
        # Status dos RP
        st.markdown("---")
        st.subheader("📊 Status dos Restos a Pagar")
        
        status_values = {}
        if 'RP Inscritos' in df_rp_filtered.columns:
            status_values['Inscritos'] = df_rp_filtered['RP Inscritos'].sum()
        if 'RP Pagos' in df_rp_filtered.columns:
            status_values['Pagos'] = df_rp_filtered['RP Pagos'].sum()
        if 'RP Cancelados' in df_rp_filtered.columns:
            status_values['Cancelados'] = df_rp_filtered['RP Cancelados'].sum()
        if 'RP a Pagar' in df_rp_filtered.columns:
            status_values['A Pagar'] = df_rp_filtered['RP a Pagar'].sum()
        
        if status_values:
            fig_status = go.Figure(data=[go.Pie(
                labels=list(status_values.keys()),
                values=list(status_values.values()),
                hole=0.4,
                marker=dict(colors=['#17a2b8', '#28a745', '#6c757d', '#dc3545'])
            )])
            
            fig_status.update_layout(
                title="Distribuição dos Restos a Pagar",
                height=400
            )
            
            st.plotly_chart(fig_status, use_container_width=True)
        
        # Tabela
        st.markdown("---")
        st.subheader("📋 Tabela de Restos a Pagar")
        
        busca_rp = st.text_input("🔍 Buscar:", "", key="busca_rp")
        
        df_rp_display = df_rp_filtered.copy()
        if busca_rp:
            mask = False
            for col in ['Empenho', 'Favorecido']:
                if col in df_rp_display.columns:
                    mask = mask | df_rp_display[col].astype(str).str.contains(busca_rp, case=False, na=False)
            df_rp_display = df_rp_display[mask]
        
        df_rp_display = df_rp_display.head(100)
        
        for col in ['RP Inscritos', 'RP Pagos', 'RP Cancelados', 'RP Bloqueados', 'RP a Pagar']:
            if col in df_rp_display.columns:
                df_rp_display[col] = df_rp_display[col].apply(formatar_real)
        
        st.dataframe(df_rp_display, use_container_width=True, height=400)

# ==================== ABA 10: BUSCADOR ====================
with tab10:
    st.header("🔍 Buscador")
    
    # OPÇÃO DE BUSCA: SIMPLIFICADA VS DETALHADA
    tipo_busca = st.radio(
        "Selecione o tipo de busca:",
        ["📋 Simplificada (Resumo)", "🔬 Detalhada (Portal TRF5)"],
        horizontal=True
    )
    
    st.markdown("---")
    
    if tipo_busca == "📋 Simplificada (Resumo)":
        # BUSCA SIMPLIFICADA - USA DADOS DO RESUMO
        st.subheader("📋 Busca Simplificada - Dados Resumidos")
        st.info("💡 Busca rápida nos dados consolidados por centro de custo")
        
        # Filtros
        col1, col2, col3 = st.columns(3)
        
        with col1:
            anos_busca = sorted(df_resumo['Ano'].unique())
            ano_busca = st.multiselect("Ano", options=anos_busca, default=[], key="ano_busca_simp")
        
        with col2:
            gestores_busca = sorted([g for g in df_resumo['Gestor(a)'].unique() if g != 'Não informado'])
            gestor_busca = st.selectbox("Gestor", options=['Todos'] + gestores_busca, key="gestor_busca_simp")
        
        with col3:
            centros_busca = sorted([c for c in df_resumo['Centro de Custo'].unique() if c != 'Não informado'])[:100]
            centro_busca = st.selectbox("Centro de Custo", options=['Todos'] + centros_busca, key="centro_busca_simp")
        
        # Busca textual
        busca_texto_simp = st.text_input("🔍 Busca livre (Gestor, Centro de Custo):", "", key="texto_busca_simp")
        
        # Aplicar filtros
        df_busca_simp = df_resumo.copy()
        
        if ano_busca:
            df_busca_simp = df_busca_simp[df_busca_simp['Ano'].isin(ano_busca)]
        
        if gestor_busca != 'Todos':
            df_busca_simp = df_busca_simp[df_busca_simp['Gestor(a)'] == gestor_busca]
        
        if centro_busca != 'Todos':
            df_busca_simp = df_busca_simp[df_busca_simp['Centro de Custo'] == centro_busca]
        
        if busca_texto_simp:
            mask = (
                df_busca_simp['Gestor(a)'].astype(str).str.contains(busca_texto_simp, case=False, na=False) |
                df_busca_simp['Centro de Custo'].astype(str).str.contains(busca_texto_simp, case=False, na=False)
            )
            df_busca_simp = df_busca_simp[mask]
        
        # Métricas
        st.markdown("---")
        col1, col2, col3, col4 = st.columns(4)
        
        with col1:
            st.metric("Registros", f"{len(df_busca_simp):,}")
        with col2:
            st.metric("Limite", formatar_real(df_busca_simp['Limite'].sum()))
        with col3:
            st.metric("Empenhado", formatar_real(df_busca_simp['Empenhado'].sum()))
        with col4:
            st.metric("Pago", formatar_real(df_busca_simp['Valor Empenhos Pagos'].sum()))
        
        # Resultados
        st.markdown("---")
        st.subheader("📊 Resultados")
        
        df_busca_display = df_busca_simp[['Ano', 'Gestor(a)', 'Centro de Custo', 'Limite', 
                                          'Pré-empenhado', 'Empenhado', 'Valor Empenhos Pagos']].copy()
        
        for col in ['Limite', 'Pré-empenhado', 'Empenhado', 'Valor Empenhos Pagos']:
            df_busca_display[col] = df_busca_display[col].apply(formatar_real)
        
        st.dataframe(df_busca_display, use_container_width=True, height=500)
        
        # Download
        csv = df_busca_simp.to_csv(index=False).encode('utf-8')
        st.download_button(
            label="📥 Baixar resultados (CSV)",
            data=csv,
            file_name=f"busca_simplificada_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv",
            mime="text/csv"
        )
    
    else:
        # BUSCA DETALHADA - USA DADOS DO PORTAL
        st.subheader("🔬 Busca Detalhada - Histórico de Modificações")
        st.info("💡 Busca nos dados do Portal TRF5, com registro histórico de cada modificação")
        
        df_portal = load_portal_data()
        
        if len(df_portal) == 0:
            st.warning("Dados do portal não disponíveis.")
        else:
            # Filtros
            col1, col2, col3, col4 = st.columns(4)
            
            with col1:
                if 'Ano' in df_portal.columns:
                    anos_portal = ['Todos'] + sorted(df_portal['Ano'].dropna().unique().tolist())
                    ano_portal_sel = st.multiselect("Ano", anos_portal, default=['Todos'], key="ano_portal")
            
            with col2:
                if 'Centro de Custo' in df_portal.columns:
                    centros_portal = ['Todos'] + sorted(df_portal['Centro de Custo'].dropna().unique().tolist()[:100])
                    centro_portal_sel = st.selectbox("Centro de Custo", centros_portal, key="centro_portal")
            
            with col3:
                if 'Gestores' in df_portal.columns:
                    gestores_portal = ['Todos'] + sorted(df_portal['Gestores'].dropna().unique().tolist()[:100])
                    gestor_portal_sel = st.selectbox("Gestor", gestores_portal, key="gestor_portal")
            
            with col4:
                if 'Tipo Nome' in df_portal.columns:
                    tipos_portal = ['Todos'] + sorted(df_portal['Tipo Nome'].dropna().unique().tolist())
                    tipo_portal_sel = st.selectbox("Tipo de Documento", tipos_portal, key="tipo_portal")
            
            # Busca textual
            col1, col2 = st.columns([3, 1])
            
            with col1:
                busca_texto = st.text_input("🔍 Busca livre (Empenho, Favorecido, Processo):", "", key="texto_portal")
            
            with col2:
                limite_registros = st.selectbox("Limite de registros", [100, 500, 1000, 5000], index=1, key="limite_portal")
            
            # Aplicar filtros
            df_portal_filtered = df_portal.copy()
            
            if 'Ano' in df_portal.columns and 'Todos' not in ano_portal_sel and ano_portal_sel:
                df_portal_filtered = df_portal_filtered[df_portal_filtered['Ano'].isin(ano_portal_sel)]
            
            if 'Centro de Custo' in df_portal.columns and centro_portal_sel != 'Todos':
                df_portal_filtered = df_portal_filtered[df_portal_filtered['Centro de Custo'] == centro_portal_sel]
            
            if 'Gestores' in df_portal.columns and gestor_portal_sel != 'Todos':
                df_portal_filtered = df_portal_filtered[df_portal_filtered['Gestores'] == gestor_portal_sel]
            
            if 'Tipo Nome' in df_portal.columns and tipo_portal_sel != 'Todos':
                df_portal_filtered = df_portal_filtered[df_portal_filtered['Tipo Nome'] == tipo_portal_sel]
            
            # Busca textual
            if busca_texto:
                mask = False
                for col in ['Nota Empenho', 'Favorecido Nome', 'Número Processo', 'Empenho']:
                    if col in df_portal_filtered.columns:
                        mask = mask | df_portal_filtered[col].astype(str).str.contains(busca_texto, case=False, na=False)
                df_portal_filtered = df_portal_filtered[mask]
            
            # Limitar registros
            df_portal_filtered = df_portal_filtered.head(limite_registros)
            
            st.markdown("---")
            
            # Métricas do resultado
            col1, col2, col3, col4 = st.columns(4)
            
            with col1:
                st.metric("Registros Encontrados", f"{len(df_portal_filtered):,}")
            
            with col2:
                if 'Valor Empenhos Total' in df_portal_filtered.columns:
                    total_emp_portal = pd.to_numeric(df_portal_filtered['Valor Empenhos Total'], errors='coerce').sum()
                    st.metric("Valor Total Empenhos", formatar_real(total_emp_portal))
            
            with col3:
                if 'Valor Empenhos Pagos' in df_portal_filtered.columns:
                    total_pago_portal = pd.to_numeric(df_portal_filtered['Valor Empenhos Pagos'], errors='coerce').sum()
                    st.metric("Valor Total Pago", formatar_real(total_pago_portal))
            
            with col4:
                if 'Ano' in df_portal_filtered.columns:
                    anos_unicos = df_portal_filtered['Ano'].nunique()
                    st.metric("Anos Cobertos", f"{anos_unicos}")
            
            # Seleção de colunas para exibição
            st.markdown("---")
            st.subheader("📋 Resultados da Busca")
            
            colunas_disponiveis = df_portal_filtered.columns.tolist()
            
            # Colunas padrão sugeridas
            colunas_padrao = ['Ano', 'Centro de Custo', 'Gestores', 'Nota Empenho', 'Favorecido Nome', 
                             'Tipo Nome', 'Valor Empenhos Total', 'Valor Empenhos Pagos', 'Data Emissão']
            colunas_padrao = [c for c in colunas_padrao if c in colunas_disponiveis]
            
            colunas_selecionadas = st.multiselect(
                "Selecione as colunas para visualização:",
                options=colunas_disponiveis,
                default=colunas_padrao,
                key="colunas_portal"
            )
            
            if colunas_selecionadas:
                df_exibir = df_portal_filtered[colunas_selecionadas].copy()
                
                # Formatar valores monetários
                colunas_monetarias = [col for col in colunas_selecionadas if 'Valor' in col or 'R$' in col]
                for col in colunas_monetarias:
                    try:
                        df_exibir[col] = pd.to_numeric(df_exibir[col], errors='coerce')
                        df_exibir[col] = df_exibir[col].apply(lambda x: formatar_real(x) if pd.notna(x) else '-')
                    except:
                        pass
                
                st.dataframe(df_exibir, use_container_width=True, height=500)
                
                # Download
                csv = df_portal_filtered[colunas_selecionadas].to_csv(index=False).encode('utf-8')
                st.download_button(
                    label="📥 Baixar resultados (CSV)",
                    data=csv,
                    file_name=f"busca_portal_trf5_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv",
                    mime="text/csv",
                    key="download_portal"
                )
            else:
                st.warning("Selecione pelo menos uma coluna para visualização.")
            
            # Análise rápida
            if len(df_portal_filtered) > 0:
                st.markdown("---")
                st.subheader("📊 Análise Rápida dos Resultados")
                
                col1, col2 = st.columns(2)
                
                with col1:
                    # Por tipo de documento
                    if 'Tipo Nome' in df_portal_filtered.columns:
                        tipo_count = df_portal_filtered['Tipo Nome'].value_counts().head(10)
                        
                        fig_tipo = go.Figure(data=[go.Pie(
                            labels=tipo_count.index,
                            values=tipo_count.values,
                            hole=0.4
                        )])
                        
                        fig_tipo.update_layout(
                            title="Distribuição por Tipo de Documento",
                            height=400
                        )
                        
                        st.plotly_chart(fig_tipo, use_container_width=True)
                
                with col2:
                    # Por grupo de despesa
                    if 'Grupo Despesa Nome' in df_portal_filtered.columns:
                        grupo_count = df_portal_filtered['Grupo Despesa Nome'].value_counts().head(10)
                        
                        fig_grupo_portal = go.Figure()
                        fig_grupo_portal.add_trace(go.Bar(
                            x=grupo_count.values,
                            y=grupo_count.index,
                            orientation='h',
                            marker_color='#0068c9'
                        ))
                        
                        fig_grupo_portal.update_layout(
                            title="Top 10 Grupos de Despesa",
                            height=400,
                            xaxis_title="Quantidade",
                            yaxis_title="",
                            yaxis={'categoryorder':'total ascending'}
                        )
                        
                        st.plotly_chart(fig_grupo_portal, use_container_width=True)

# Rodapé
st.markdown("---")
st.markdown(
    """
    <div style='text-align: center; color: #666; padding: 20px;'>
        <p><strong>Portal Financeiro TRF5</strong></p>
        <p>Sistema de Acompanhamento e Análise de Gestão Orçamentária</p>
        <p style='font-size: 12px;'>Desenvolvido para análise e transparência na gestão de recursos públicos</p>
    </div>
    """,
    unsafe_allow_html=True
)