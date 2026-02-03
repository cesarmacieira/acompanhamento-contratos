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

st.markdown("""
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
tab1, tab2, tab3, tab4, tab5, tab6, tab7, tab8 = st.tabs([
    "📋 Lista de contratos", 
    "🚨 Alertas", 
    "📊 Análises dos contratos",
    "💰 Análise financeira",  
    "💳 Dados orçamentários", 
    "❗ Inconsistências nos sistemas",
    "🔍 Buscador detalhado",
    "📈 Análise detalhada de contratos"])

# ==================== ABA 5: DADOS ORÇAMENTÁRIOS ====================
with tab5:
    st.header("💳 Dados Orçamentários")
    st.markdown("Visualização consolidada de empenhos, pré-empenhos e restos a pagar")
    
    # Criar sub-abas
    subtab1_orc, subtab2_orc, subtab3_orc = st.tabs([
        "💰 Empenhos Detalhados",
        "📋 Pré-Empenhos", 
        "📈 Restos a Pagar"
    ])
    
    # ==================== SUB-ABA 1: EMPENHOS ====================
    with subtab1_orc:
        st.subheader("Empenhos Detalhados")
        
        if len(df_empenhos) == 0:
            st.warning("Dados de empenhos não disponíveis.")
        else:
            # FILTROS
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
            
            # Gráficos
            st.subheader("📊 Análises e Visualizações")
            col1, col2 = st.columns(2)
            
            with col1:
                if 'Favorecido' in df_empenhos_filtered.columns and 'Valor Empenhado' in df_empenhos_filtered.columns and len(df_empenhos_filtered) > 0:
                    st.markdown("### 👥 Top 15 Favorecidos")
                    favorecidos_agg = df_empenhos_filtered.groupby('Favorecido')['Valor Empenhado'].sum().nlargest(15)
                    
                    if len(favorecidos_agg) > 0:
                        fig_fav = go.Figure()
                        fig_fav.add_trace(go.Bar(
                            x=favorecidos_agg.values,
                            y=favorecidos_agg.index,
                            orientation='h',
                            marker_color='#0068c9'
                        ))
                        fig_fav.update_layout(
                            xaxis_title="Valor Empenhado (R$)",
                            yaxis_title="",
                            height=500,
                            yaxis={'categoryorder':'total ascending'}
                        )
                        st.plotly_chart(fig_fav, use_container_width=True)
            
            with col2:
                if 'Grupo' in df_empenhos_filtered.columns and 'Valor Empenhado' in df_empenhos_filtered.columns and len(df_empenhos_filtered) > 0:
                    st.subheader("📊 Por Grupo")
                    grupo_agg = df_empenhos_filtered.groupby('Grupo')['Valor Empenhado'].sum().nlargest(15)
                    
                    if len(grupo_agg) > 0:
                        fig_grupo = go.Figure()
                        fig_grupo.add_trace(go.Bar(
                            x=grupo_agg.values,
                            y=grupo_agg.index,
                            orientation='h',
                            marker_color='#17a2b8'
                        ))
                        fig_grupo.update_layout(
                            xaxis_title="Valor Empenhado (R$)",
                            yaxis_title="",
                            height=500,
                            yaxis={'categoryorder':'total ascending'}
                        )
                        st.plotly_chart(fig_grupo, use_container_width=True)
            
            # Adicionar gráfico de evolução anual se tiver coluna Ano
            if 'Ano' in df_empenhos_filtered.columns and len(df_empenhos_filtered) > 0:
                st.markdown("---")
                st.subheader("📈 Evolução Anual")
                
                col1, col2 = st.columns(2)
                
                with col1:
                    # Quantidade por ano
                    ano_qtd = df_empenhos_filtered.groupby('Ano').size()
                    if len(ano_qtd) > 0:
                        fig_ano_qtd = go.Figure()
                        fig_ano_qtd.add_trace(go.Bar(
                            x=ano_qtd.index,
                            y=ano_qtd.values,
                            marker_color='#0068c9',
                            text=ano_qtd.values,
                            textposition='auto'
                        ))
                        fig_ano_qtd.update_layout(
                            title="Quantidade de Empenhos por Ano",
                            xaxis_title="Ano",
                            yaxis_title="Quantidade",
                            height=400
                        )
                        st.plotly_chart(fig_ano_qtd, use_container_width=True)
                
                with col2:
                    # Valor por ano
                    if 'Valor Empenhado' in df_empenhos_filtered.columns:
                        ano_valor = df_empenhos_filtered.groupby('Ano')['Valor Empenhado'].sum()
                        if len(ano_valor) > 0:
                            fig_ano_valor = go.Figure()
                            fig_ano_valor.add_trace(go.Bar(
                                x=ano_valor.index,
                                y=ano_valor.values,
                                marker_color='#28a745',
                                text=ano_valor.values.apply(lambda x: f'R$ {x/1000:.0f}K'),
                                textposition='auto'
                            ))
                            fig_ano_valor.update_layout(
                                title="Valor Empenhado por Ano",
                                xaxis_title="Ano",
                                yaxis_title="Valor (R$)",
                                height=400
                            )
                            st.plotly_chart(fig_ano_valor, use_container_width=True)
            
            # Tabela
            st.markdown("---")
            st.subheader("📋 Tabela de Empenhos")
            
            col_busca, col_limite = st.columns([3, 1])
            with col_busca:
                busca_emp = st.text_input("🔍 Buscar:", "", key="busca_emp")
            with col_limite:
                limite_emp = st.selectbox("Registros", [100, 500, 1000, "Todos"], index=0, key="limite_emp")
            
            df_emp_display = df_empenhos_filtered.copy()
            if busca_emp:
                mask = False
                for col in ['Empenho', 'Favorecido', 'Processo', 'Contrato']:
                    if col in df_emp_display.columns:
                        mask = mask | df_emp_display[col].astype(str).str.contains(busca_emp, case=False, na=False)
                df_emp_display = df_emp_display[mask]
            
            # Aplicar limite de registros
            total_registros = len(df_emp_display)
            if limite_emp != "Todos":
                df_emp_display = df_emp_display.head(int(limite_emp))
            
            # Selecionar colunas principais para exibição
            colunas_exibir = []
            for col in ['Ano', 'Empenho', 'Favorecido', 'Contrato', 'Processo', 'Valor Empenhado', 'Valor Pago', 'R$ a pagar', 'Grupo']:
                if col in df_emp_display.columns:
                    colunas_exibir.append(col)
            
            if colunas_exibir:
                df_emp_final = df_emp_display[colunas_exibir].copy()
                
                # Formatar valores monetários
                for col in ['Valor Empenhado', 'Valor Pago', 'R$ a pagar']:
                    if col in df_emp_final.columns:
                        df_emp_final[col] = df_emp_final[col].apply(lambda x: formatar_real(x) if pd.notna(x) else '-')
                
                st.dataframe(df_emp_final, use_container_width=True, height=500)
                st.info(f"📊 Exibindo {len(df_emp_final):,} de {total_registros:,} registros")
                
                # Botão de download
                csv = df_empenhos_filtered[colunas_exibir].to_csv(index=False).encode('utf-8')
                st.download_button(
                    label="📥 Baixar dados filtrados (CSV)",
                    data=csv,
                    file_name=f"empenhos_{datetime.now().strftime('%Y%m%d')}.csv",
                    mime="text/csv",
                    key="download_emp"
                )
            else:
                st.warning("Nenhuma coluna disponível para exibição")
    
    # ==================== SUB-ABA 2: PRÉ-EMPENHOS ====================
    with subtab2_orc:
        st.subheader("Pré-Empenhos")
        
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
                    favorecidos_pre = sorted([f for f in df_pre_empenhos['Favorecido'].unique()][:100])
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
                if 'Valor Pré-Empenhado' in df_pre_filtered.columns:
                    valor_medio = df_pre_filtered['Valor Pré-Empenhado'].mean()
                    st.metric("Valor Médio", formatar_real(valor_medio))
            
            st.markdown("---")
            
            # Gráficos
            col1, col2 = st.columns(2)
            
            with col1:
                if 'Favorecido' in df_pre_filtered.columns and 'Valor Pré-Empenhado' in df_pre_filtered.columns and len(df_pre_filtered) > 0:
                    st.subheader("👥 Top 15 Favorecidos")
                    fav_agg = df_pre_filtered.groupby('Favorecido')['Valor Pré-Empenhado'].sum().nlargest(15)
                    
                    if len(fav_agg) > 0:
                        fig_fav_pre = go.Figure()
                        fig_fav_pre.add_trace(go.Bar(
                            x=fav_agg.values,
                            y=fav_agg.index,
                            orientation='h',
                            marker_color='#ffc107'
                        ))
                        fig_fav_pre.update_layout(
                            xaxis_title="Valor (R$)",
                            yaxis_title="",
                            height=500,
                            yaxis={'categoryorder':'total ascending'}
                        )
                        st.plotly_chart(fig_fav_pre, use_container_width=True)
            
            with col2:
                if 'Ano' in df_pre_filtered.columns and 'Valor Pré-Empenhado' in df_pre_filtered.columns and len(df_pre_filtered) > 0:
                    st.subheader("📈 Evolução Anual")
                    ano_agg = df_pre_filtered.groupby('Ano')['Valor Pré-Empenhado'].sum()
                    
                    if len(ano_agg) > 0:
                        fig_ano_pre = go.Figure()
                        fig_ano_pre.add_trace(go.Bar(
                            x=ano_agg.index,
                            y=ano_agg.values,
                            marker_color='#ffc107'
                        ))
                        fig_ano_pre.update_layout(
                            title="Pré-Empenhos por Ano",
                            xaxis_title="Ano",
                            yaxis_title="Valor (R$)",
                            height=500
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
            
            # Seleção de colunas principais
            colunas_exibir_pre = []
            for col in ['Ano', 'Pré-Empenho', 'Favorecido', 'Processo', 'Valor Pré-Empenhado']:
                if col in df_pre_display.columns:
                    colunas_exibir_pre.append(col)
            
            if colunas_exibir_pre:
                df_pre_final = df_pre_display[colunas_exibir_pre].head(100).copy()
                
                # Formatar valores monetários
                if 'Valor Pré-Empenhado' in df_pre_final.columns:
                    df_pre_final['Valor Pré-Empenhado'] = df_pre_final['Valor Pré-Empenhado'].apply(
                        lambda x: formatar_real(x) if pd.notna(x) else '-'
                    )
                
                st.dataframe(df_pre_final, use_container_width=True, height=400)
                st.info(f"📊 Exibindo {len(df_pre_final):,} de {len(df_pre_display):,} registros")
                
                # Botão de download
                csv_pre = df_pre_filtered[colunas_exibir_pre].to_csv(index=False).encode('utf-8')
                st.download_button(
                    label="📥 Baixar dados filtrados (CSV)",
                    data=csv_pre,
                    file_name=f"pre_empenhos_{datetime.now().strftime('%Y%m%d')}.csv",
                    mime="text/csv",
                    key="download_pre_empenhos"
                )
            else:
                st.dataframe(df_pre_display.head(100), use_container_width=True, height=400)
                st.info(f"📊 Exibindo primeiros 100 registros")
    
    # ==================== SUB-ABA 3: RESTOS A PAGAR ====================
    with subtab3_orc:
        st.subheader("Restos a Pagar")
        
        if len(df_rp) == 0:
            st.warning("Dados de restos a pagar não disponíveis.")
        else:
            # Filtros
            col1_f, col2_f = st.columns(2)
            
            with col1_f:
                if 'Ano' in df_rp.columns:
                    anos_rp = sorted(df_rp['Ano'].dropna().unique().tolist())
                    ano_rp = st.multiselect("Ano", options=anos_rp, default=[], key="ano_rp")
            
            with col2_f:
                if 'Favorecido' in df_rp.columns:
                    favorecidos_rp = sorted([f for f in df_rp['Favorecido'].unique()][:100])
                    favorecido_rp = st.selectbox("Favorecido", options=['Todos'] + favorecidos_rp, key="fav_rp")
            
            # Aplicar filtros
            df_rp_filtered = df_rp.copy()
            
            if 'Ano' in df_rp.columns and ano_rp:
                df_rp_filtered = df_rp_filtered[df_rp_filtered['Ano'].isin(ano_rp)]
            
            if 'Favorecido' in df_rp.columns and favorecido_rp != 'Todos':
                df_rp_filtered = df_rp_filtered[df_rp_filtered['Favorecido'] == favorecido_rp]
            
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
                if 'RP a Pagar' in df_rp_filtered.columns:
                    st.metric("RP a Pagar", formatar_real(df_rp_filtered['RP a Pagar'].sum()))
            with col4:
                if 'RP Cancelados' in df_rp_filtered.columns:
                    st.metric("RP Cancelados", formatar_real(df_rp_filtered['RP Cancelados'].sum()))
            
            st.markdown("---")
            
            # Gráficos
            col1, col2 = st.columns(2)
            
            with col1:
                if 'Favorecido' in df_rp_filtered.columns and 'RP a Pagar' in df_rp_filtered.columns and len(df_rp_filtered) > 0:
                    st.subheader("👥 Top 15 Favorecidos - RP a Pagar")
                    fav_rp_agg = df_rp_filtered.groupby('Favorecido')['RP a Pagar'].sum().nlargest(15)
                    
                    if len(fav_rp_agg) > 0:
                        fig_fav_rp = go.Figure()
                        fig_fav_rp.add_trace(go.Bar(
                            x=fav_rp_agg.values,
                            y=fav_rp_agg.index,
                            orientation='h',
                            marker_color='#dc3545'
                        ))
                        fig_fav_rp.update_layout(
                            xaxis_title="Valor (R$)",
                            yaxis_title="",
                            height=500,
                            yaxis={'categoryorder':'total ascending'}
                        )
                        st.plotly_chart(fig_fav_rp, use_container_width=True)
            
            with col2:
                # Gráfico de pizza com distribuição
                if len(df_rp_filtered) > 0:
                    st.subheader("📊 Distribuição de RP")
                    valores_rp = {
                        'Pagos': df_rp_filtered['RP Pagos'].sum() if 'RP Pagos' in df_rp_filtered.columns else 0,
                        'A Pagar': df_rp_filtered['RP a Pagar'].sum() if 'RP a Pagar' in df_rp_filtered.columns else 0,
                        'Cancelados': df_rp_filtered['RP Cancelados'].sum() if 'RP Cancelados' in df_rp_filtered.columns else 0
                    }
                    
                    # Filtrar apenas valores > 0
                    valores_rp = {k: v for k, v in valores_rp.items() if v > 0}
                    
                    if valores_rp:
                        fig_dist_rp = go.Figure(data=[go.Pie(
                            labels=list(valores_rp.keys()),
                            values=list(valores_rp.values()),
                            marker=dict(colors=['#28a745', '#ffc107', '#dc3545']),
                            hole=0.4
                        )])
                        fig_dist_rp.update_layout(height=500)
                        st.plotly_chart(fig_dist_rp, use_container_width=True)
            
            # Tabela
            st.markdown("---")
            st.subheader("📋 Tabela de Restos a Pagar")
            
            busca_rp = st.text_input("🔍 Buscar:", "", key="busca_rp")
            
            df_rp_display = df_rp_filtered.copy()
            if busca_rp:
                mask = False
                for col in ['RP', 'Favorecido', 'Processo']:
                    if col in df_rp_display.columns:
                        mask = mask | df_rp_display[col].astype(str).str.contains(busca_rp, case=False, na=False)
                df_rp_display = df_rp_display[mask]
            
            # Seleção de colunas principais
            colunas_exibir_rp = []
            for col in ['Ano', 'RP', 'Favorecido', 'Processo', 'RP Inscritos', 'RP Pagos', 'RP a Pagar', 'RP Cancelados']:
                if col in df_rp_display.columns:
                    colunas_exibir_rp.append(col)
            
            if colunas_exibir_rp:
                df_rp_final = df_rp_display[colunas_exibir_rp].head(100).copy()
                
                # Formatar valores monetários
                for col in ['RP Inscritos', 'RP Pagos', 'RP a Pagar', 'RP Cancelados']:
                    if col in df_rp_final.columns:
                        df_rp_final[col] = df_rp_final[col].apply(
                            lambda x: formatar_real(x) if pd.notna(x) else '-'
                        )
                
                st.dataframe(df_rp_final, use_container_width=True, height=400)
                st.info(f"📊 Exibindo {len(df_rp_final):,} de {len(df_rp_display):,} registros")
                
                # Botão de download
                csv_rp = df_rp_filtered[colunas_exibir_rp].to_csv(index=False).encode('utf-8')
                st.download_button(
                    label="📥 Baixar dados filtrados (CSV)",
                    data=csv_rp,
                    file_name=f"restos_a_pagar_{datetime.now().strftime('%Y%m%d')}.csv",
                    mime="text/csv",
                    key="download_restos_pagar"
                )
            else:
                st.dataframe(df_rp_display.head(100), use_container_width=True, height=400)
                st.info(f"📊 Exibindo primeiros 100 registros")
