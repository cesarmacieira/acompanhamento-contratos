import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from datetime import datetime, timedelta
from plotly.subplots import make_subplots
import numpy as np
from datetime import datetime, timezone
from PIL import Image,ImageDraw,ImageFont
from buscador_contratos import BuscadorContratos
import io
import os
import unicodedata
import json
import logging
import warnings
warnings.filterwarnings("ignore")

# Silencia logs internos do Streamlit e bibliotecas ruidosas
logging.root.setLevel(logging.WARNING)

_SILENT_LOGGERS = [
    "streamlit",
    "streamlit.runtime",
    "streamlit.runtime.app_session",
    "streamlit.runtime.legacy_caching",
    "streamlit.runtime.caching",
    "streamlit.runtime.media_file_manager",
    "streamlit.runtime.media_file_storage",
    "streamlit.runtime.scriptrunner",
    "streamlit.runtime.state",
    "streamlit.server",
    "streamlit.server.server",
    "streamlit.watcher",
    "streamlit.watcher.local_sources_watcher",
    "tornado.access",
    "tornado.application",
    "tornado.general",
    "urllib3",
    "urllib3.connectionpool",
]
for _name in _SILENT_LOGGERS:
    logging.getLogger(_name).setLevel(logging.CRITICAL)
    logging.getLogger(_name).propagate = False

# ========= Access logger (stdout) =========
_ACCESS_LOGGER = logging.getLogger("access")
if not _ACCESS_LOGGER.handlers:
    _handler = logging.StreamHandler()  # stdout -> Kubernetes coleta
    _ACCESS_LOGGER.addHandler(_handler)

# nível via env (opcional)
_ACCESS_LOGGER.setLevel(os.getenv("ACCESS_LOG_LEVEL", "INFO").upper())

def _h(headers: dict, key: str, default=None):
    """Header case-insensitive getter"""
    key_l = key.lower()
    for k, v in headers.items():
        if str(k).lower() == key_l:
            return v
    return default


def get_client_ip(headers: dict) -> str:
    """
    IP "real" quando existe proxy:
    - X-Forwarded-For: "client, proxy1, proxy2" -> pega o primeiro
    - X-Real-IP como fallback
    """
    xff = _h(headers, "X-Forwarded-For")
    if xff:
        return str(xff).split(",")[0].strip()

    xri = _h(headers, "X-Real-IP")
    if xri:
        return str(xri).strip()

    # CDNs comuns (opcional)
    cf = _h(headers, "CF-Connecting-IP")
    if cf:
        return str(cf).strip()

    return "unknown"


def get_request_url(headers: dict) -> str:
    """
    Streamlit não expõe path com garantia; montamos:
    proto://host/ + ?query
    """
    proto = _h(headers, "X-Forwarded-Proto") or "http"
    host = _h(headers, "Host") or "unknown-host"

    # Query params (compatível com versões novas)
    query = ""
    try:
        qp = st.query_params
        parts = []
        for k in qp.keys():
            if hasattr(qp, "get_all"):
                vals = qp.get_all(k)
            else:
                vals = qp.get(k)
            if isinstance(vals, list):
                for vv in vals:
                    parts.append(f"{k}={vv}")
            else:
                parts.append(f"{k}={vals}")
        query = "&".join(parts)
    except Exception:
        query = ""

    base = f"{proto}://{host}/"
    return base if not query else f"{base}?{query}"


def log_access_once_per_session():
    if st.session_state.get("_access_logged"):
        return
    headers = dict(st.context.headers) if hasattr(st, "context") else {}
    ip = get_client_ip(headers)
    url = get_request_url(headers)
    ua = _h(headers, "User-Agent", "")
    payload = {"time": datetime.now(timezone.utc).isoformat(), "ip": ip,
        "url": url, "ua": ua, "session_id": st.session_state.get("_sid", "none")}
    _ACCESS_LOGGER.info(json.dumps(payload, ensure_ascii=False))
    st.session_state["_access_logged"] = True

st.set_page_config(page_title="Gestão de Contratos Públicos",layout="wide")
log_access_once_per_session()

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
    logo_esquerda = os.path.join(BASE_DIR, "logos", "logo_horizontal_branca.png")
    im_left=Image.open(logo_esquerda).convert("RGBA")
    h_left=80
    w_left=int(im_left.size[0]*h_left/im_left.size[1])
    im_left=im_left.resize((w_left,h_left))
    left_x=32
    banner.alpha_composite(im_left,(left_x,(H-h_left)//2))
    logos_direita_relativos = [
        ("logos", "logo_Justica_Federal_5Regiao_branca.png"),
        ("logos", "logo_Justica_Federal_Ceara_branca.png"),
        ("logos", "Logo_PNUD_branca.png")]
    logos_direita = []
    for parts in logos_direita_relativos:
        path = os.path.join(BASE_DIR, *parts)
        if os.path.exists(path):
            logos_direita.append(path)
        else:
            st.warning(f"Logo não encontrada: {path}")
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

st.markdown("""
<style>

/* =========================
   Layout (seguro)
========================= */
section.main > div {
    padding: 0rem 1rem;
}

/* =========================
   Tabs com rolagem horizontal
========================= */
.stTabs [data-baseweb="tab-list"] {
    gap: 2px;
    overflow-x: auto;
    overflow-y: hidden;
    white-space: nowrap;
    flex-wrap: nowrap !important;
    -webkit-overflow-scrolling: touch;
    scrollbar-width: thin;
}

/* Scrollbar tabs - Webkit */
.stTabs [data-baseweb="tab-list"]::-webkit-scrollbar {
    height: 4px;
}

.stTabs [data-baseweb="tab-list"]::-webkit-scrollbar-thumb {
    background-color: #0068c9;
    border-radius: 2px;
}

/* Tabs individuais */
.stTabs [data-baseweb="tab"] {
    padding: 8px 16px;
    background-color: #f0f2f6;
    border-radius: 5px 5px 0px 0px;
    white-space: nowrap;
    flex-shrink: 0;
    font-size: 14px;
}

/* Tabs - telas pequenas */
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

/* Hover */
.stTabs [data-baseweb="tab"]:not([aria-selected="true"]):hover {
    color: #00689D !important;
}

/* =========================
   Cards métricos
========================= */
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

/* =========================
   Títulos
========================= */
h1 {
    color: #0068c9;
    border-bottom: 3px solid #0068c9;
    padding-bottom: 10px;
}

h2 {
    color: #555;
    margin-top: 20px;
}

/* =========================
   DARK MODE (SEM QUEBRAR JS)
========================= */
@media (prefers-color-scheme: dark) {

    section.main > div {
        background-color: #0e1117;
        color: #e6e6e6;
    }

    /* Scrollbar tabs dark */
    .stTabs [data-baseweb="tab-list"]::-webkit-scrollbar-thumb {
        background-color: #58a6ff;
    }

    .metric-card {
        background-color: #161b22;
        border-left: 4px solid #58a6ff;
        box-shadow: none;
    }

    .metric-title {
        color: #9aa4ad;
    }

    .metric-value {
        color: #58a6ff;
    }

    h1 {
        color: #58a6ff;
        border-bottom: 3px solid #58a6ff;
    }

    h2 {
        color: #c9d1d9;
    }

    .stTabs [data-baseweb="tab"] {
        background-color: #161b22;
        color: #c9d1d9;
    }

    .stTabs [aria-selected="true"] {
        background-color: #1f6feb;
        color: #ffffff;
    }

    .stTabs [data-baseweb="tab"]:not([aria-selected="true"]):hover {
        color: #58a6ff !important;
    }
}
</style>
""", unsafe_allow_html=True)

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
    BASE_DIR = os.path.dirname(os.path.abspath(__file__))
    arquivo_resumo = os.path.join(BASE_DIR, "dados", "Dados resumo centro de custos.xlsx")
    if not os.path.exists(arquivo_resumo):
        st.error(f"Arquivo não encontrado: {arquivo_resumo}")
        return pd.DataFrame()
    df = pd.read_excel(arquivo_resumo)
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
    BASE_DIR = os.path.dirname(os.path.abspath(__file__))
    arquivo_resumo = os.path.join(BASE_DIR, "dados", "Dados empenhos.parquet")
    if not os.path.exists(arquivo_resumo):
        st.error(f"Arquivo não encontrado: {arquivo_resumo}")
        return pd.DataFrame()
    df = pd.read_parquet(arquivo_resumo)
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
    BASE_DIR = os.path.dirname(os.path.abspath(__file__))
    arquivo_resumo = os.path.join(BASE_DIR, "dados", "Dados pré empenhos.parquet")
    if not os.path.exists(arquivo_resumo):
        st.error(f"Arquivo não encontrado: {arquivo_resumo}")
        return pd.DataFrame()
    df = pd.read_parquet(arquivo_resumo)
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
    BASE_DIR = os.path.dirname(os.path.abspath(__file__))
    arquivo_resumo = os.path.join(BASE_DIR, "dados", "Dados restos a pagar.parquet")
    if not os.path.exists(arquivo_resumo):
        st.error(f"Arquivo não encontrado: {arquivo_resumo}")
        return pd.DataFrame()
    df = pd.read_parquet(arquivo_resumo)
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
    contratos = buscador.buscar_multiplos_anos("12000","090006",2015,datetime.now().year + 5)
    return pd.DataFrame(contratos)
df_comprasnet = load_comprasnet_data()
df_comprasnet = df_comprasnet.dropna(how="all")
df_comprasnet = df_comprasnet.dropna(subset=["numeroContrato","dataVigenciaFinal"])
if df_comprasnet.empty:
    st.warning("Nenhum contrato encontrado.")
    st.stop()

df_comprasnet["dataVigenciaInicial"] = pd.to_datetime(df_comprasnet["dataVigenciaInicial"], errors="coerce")
df_comprasnet["dataVigenciaFinal"] = pd.to_datetime(df_comprasnet["dataVigenciaFinal"], errors="coerce")
df_comprasnet["valorGlobal"] = pd.to_numeric(df_comprasnet["valorGlobal"], errors="coerce").fillna(0)

hoje = pd.Timestamp.today()

df_comprasnet["status"] = df_comprasnet["dataVigenciaFinal"].apply(lambda x: "Vencido" if x < hoje else "Vigente")
df_comprasnet["ano"] = df_comprasnet["dataVigenciaInicial"].dt.year

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

df_comprasnet["vigencia_mais_de_um_ano"] = (df_comprasnet["dataVigenciaFinal"] >= df_comprasnet["dataVigenciaInicial"] + pd.DateOffset(years=1)).map({True: "Sim", False: "Não"})
colunas_renomeadas = ["Código do Órgão","Nome do Órgão","Código da Unidade Gestora","Nome da Unidade Gestora",
    "Código da Unidade Gestora de Origem do Contrato","Nome da Unidade Gestora de Origem do Contrato",
    "Tipo de Receita ou Despesa","Número do Contrato","Código da Unidade Realizadora da Compra",
    "Nome da Unidade Realizadora da Compra","Número da Compra","Código da Modalidade de Compra",
    "Nome da Modalidade de Compra","Código do Tipo","Nome do Tipo","Código da Categoria","Nome da Categoria",
    "Código da Subcategoria","Nome da Subcategoria","CNPJ ou CPF do Fornecedor","Razão Social do Fornecedor",
    "Número do Processo","Objeto do Contrato","Informações Complementares","Data de Vigência Inicial",
    "Data de Vigência Final","Valor Global do Contrato","Número de Parcelas","Valor da Parcela",
    "Valor Acumulado","Total de Despesas Acessórias","Data e Hora de Inclusão","Número de Controle PNCP do Contrato",
    "ID da Compra","Data e Hora de Exclusão","Contrato Excluído","Unidades Requisitantes","Status","Ano","Vigência em mais de um ano"]

# Criação da variável Núcleo Divisão Seção
df_resumo["Núcleo_Divisão_Seção"] = df_resumo["Centro de Custo"].astype(str).str.strip().str.split("-", n=1).str[0].str.strip()

# Criar abas principais
tab1, tab2, tab3, tab4, tab5, tab6, tab7 = st.tabs([
    "📋 Lista de contratos", 
    "🚨 Alertas", 
    "📊 Análises dos contratos",
    "💰 Finanças",  
    "💳 Dados orçamentários", 
    "❗ Inconsistências nos sistemas",
    "📈 Resumo geral"])

# ==================== ABA 1: LISTA DE CONTRATOS ====================
with tab1:
    st.subheader("Lista geral de contratos")
    c1, c2, c3, c4 = st.columns(4)
    fornecedor = c1.multiselect("Fornecedor",sorted(df_comprasnet["nomeRazaoSocialFornecedor"].dropna().unique()),
                                placeholder="Selecione uma ou mais opções")
    unidade = c2.multiselect("Unidade realizadora",sorted(df_comprasnet["nomeUnidadeRealizadoraCompra"].dropna().unique()),
                                placeholder="Selecione uma ou mais opções")
    ano = c3.multiselect("Ano",sorted(df_comprasnet["ano"].dropna().unique()),
                                placeholder="Selecione uma ou mais opções")
    status = c4.multiselect("Status",["Vigente", "Vencido"])
    c5, c6, c7, c8 = st.columns(4)
    modalidade = c5.multiselect("Modalidade de compra",sorted(df_comprasnet["nomeModalidadeCompra"].dropna().unique()),
                                placeholder="Selecione uma ou mais opções")
    tipo = c6.multiselect("Tipo de contrato",sorted(df_comprasnet["nomeTipo"].dropna().unique()),
                                placeholder="Selecione uma ou mais opções")
    categoria = c7.multiselect("Categoria",sorted(df_comprasnet["nomeCategoria"].dropna().unique()),
                                placeholder="Selecione uma ou mais opções")
    busca_texto = c8.text_input("Busca livre (objeto / informações complementares)")
    c9, c10, c11, c12 = st.columns(4)
    data_ini = c9.date_input("Vigência final a partir de",value=df_comprasnet["dataVigenciaFinal"].min().date() if pd.notnull(df_comprasnet["dataVigenciaFinal"].min()) else None)
    data_fim = c10.date_input("Vigência final até",value=df_comprasnet["dataVigenciaFinal"].max().date() if pd.notnull(df_comprasnet["dataVigenciaFinal"].max()) else None)
    numero_contrato = c11.multiselect("Número do contrato",sorted(df_comprasnet["numeroContrato"].dropna().unique()),
                                placeholder="Selecione uma ou mais opções")
    valor_parcela_min, valor_parcela_max = c12.slider("Valor do contrato (R$)",float(df_comprasnet["valorGlobal"].min()),
        float(df_comprasnet["valorGlobal"].max()),(float(df_comprasnet["valorGlobal"].min()), float(df_comprasnet["valorGlobal"].max())))
    df_comprasnet_f = df_comprasnet.copy()
    if fornecedor:
        df_comprasnet_f = df_comprasnet_f[df_comprasnet_f["nomeRazaoSocialFornecedor"].isin(fornecedor)]
    if unidade:
        df_comprasnet_f = df_comprasnet_f[df_comprasnet_f["nomeUnidadeRealizadoraCompra"].isin(unidade)]
    if ano:
        df_comprasnet_f = df_comprasnet_f[df_comprasnet_f["ano"].isin(ano)]
    if status:
        df_comprasnet_f = df_comprasnet_f[df_comprasnet_f["status"].isin(status)]
    if modalidade:
        df_comprasnet_f = df_comprasnet_f[df_comprasnet_f["nomeModalidadeCompra"].isin(modalidade)]
    if tipo:
        df_comprasnet_f = df_comprasnet_f[df_comprasnet_f["nomeTipo"].isin(tipo)]
    if categoria:
        df_comprasnet_f = df_comprasnet_f[df_comprasnet_f["nomeCategoria"].isin(categoria)]
    if busca_texto:
        texto = norm(busca_texto)
        df_comprasnet_f = df_comprasnet_f[df_comprasnet_f["objeto"].apply(norm).str.contains(texto, na=False) | df_comprasnet_f["informacoesComplementares"].apply(norm).str.contains(texto, na=False)]
    if data_ini:
        df_comprasnet_f = df_comprasnet_f[df_comprasnet_f["dataVigenciaFinal"] >= pd.to_datetime(data_ini)]
    if data_fim:
        df_comprasnet_f = df_comprasnet_f[df_comprasnet_f["dataVigenciaFinal"] <= pd.to_datetime(data_fim)]
    df_comprasnet_f = df_comprasnet_f[(df_comprasnet_f["valorParcela"] >= valor_parcela_min) & (df_comprasnet_f["valorParcela"] <= valor_parcela_max)]
    if numero_contrato:
        df_comprasnet_f = df_comprasnet_f[df_comprasnet_f["numeroContrato"].isin(numero_contrato)]

    df_comprasnet_f.columns = colunas_renomeadas
    st.dataframe(df_comprasnet_f.sort_values("Data de Vigência Final").reset_index(drop=True),use_container_width=True)
    st.caption(f"Quantidade de contratos exibidos: {len(df_comprasnet_f)}")
    buffer = io.BytesIO()
    with pd.ExcelWriter(buffer, engine="openpyxl") as writer:
        df_comprasnet_f.sort_values("Data de Vigência Final").to_excel(writer, index=False, sheet_name="Contratos")
    buffer.seek(0)

    st.download_button(label="⬇️ Baixar contratos", data=buffer, file_name="contratos.xlsx",
        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")

# ==================== ABA 2: ALERTAS ====================
with tab2:
    st.subheader("Alertas de prazo e risco")
    v30 = df_comprasnet[(df_comprasnet["dataVigenciaFinal"] >= hoje) & (df_comprasnet["dataVigenciaFinal"] <= hoje + timedelta(days=30))]
    v60 = df_comprasnet[(df_comprasnet["dataVigenciaFinal"] > hoje + timedelta(days=30)) & (df_comprasnet["dataVigenciaFinal"] <= hoje + timedelta(days=60))]
    v90 = df_comprasnet[(df_comprasnet["dataVigenciaFinal"] > hoje + timedelta(days=60)) & (df_comprasnet["dataVigenciaFinal"] <= hoje + timedelta(days=90))]
    vencidos = df_comprasnet[df_comprasnet["dataVigenciaFinal"] < hoje]
    vigentes = df_comprasnet[df_comprasnet["dataVigenciaFinal"] >= hoje]
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Quantidade total de contratos", len(df_comprasnet))
    c2.metric("Contratos vigentes", len(vigentes))
    c3.metric("Contratos vencidos", len(vencidos))
    c4.metric("Percentual de contratos vencidos", f"{(len(vencidos)/len(df_comprasnet)*100):.1f}%" if len(df_comprasnet) > 0 else "0%")
    c5, c6, c7, c8 = st.columns(4)
    c5.metric("Vencendo em 30 dias", len(v30))
    c6.metric("Vencendo em 60 dias", len(v60))
    c7.metric("Vencendo em 90 dias", len(v90))
    c8.metric("Total contratos críticos", len(v30)+len(v60)+len(v90))
    c9, c10, c11, c12 = st.columns(4)
    c9.metric("Valor global total contratado", f"R$ {df_comprasnet['valorGlobal'].sum():,.2f}".replace(",", "X").replace(".", ",").replace("X", "."))
    c10.metric("Valor global vigente", f"R$ {vigentes['valorGlobal'].sum():,.2f}".replace(",", "X").replace(".", ",").replace("X", "."))
    c11.metric("Valor global vencido", f"R$ {vencidos['valorGlobal'].sum():,.2f}".replace(",", "X").replace(".", ",").replace("X", "."))
    c12.metric("Valor global total em risco", f"R$ {(v30['valorGlobal'].sum()+v60['valorGlobal'].sum()+v90['valorGlobal'].sum()):,.2f}".replace(",", "X").replace(".", ",").replace("X", "."))
    st.divider()
    st.markdown("### 📋 Contratos vigentes")
    c29, c30, c31, c32 = st.columns(4)
    c29.metric("Qtd contratos", len(vigentes))
    c30.metric("Percentual do total", f"{(len(vigentes)/len(df_comprasnet)*100):.1f}%" if len(df_comprasnet) > 0 else "0%")
    c31.metric("Valor global total vigente", f"R$ {vigentes['valorGlobal'].sum():,.2f}".replace(",", "X").replace(".", ",").replace("X", "."))
    c32.metric("Valor global médio", f"R$ {vigentes['valorGlobal'].mean():,.2f}".replace(",", "X").replace(".", ",").replace("X", ".") if not vigentes.empty else "R$ 0,00")
    c33, c34, c35, c36 = st.columns(4)
    c33.metric("Maior contrato (valor global)", f"R$ {vigentes['valorGlobal'].max():,.2f}".replace(",", "X").replace(".", ",").replace("X", ".") if not vigentes.empty else "R$ 0,00")
    c34.metric("Qtd de contratos vigentes fora de risco (>90d)", len(vigentes)-(len(v30)+len(v60)+len(v90)))
    c35.metric("Valor global fora de risco", f"R$ {(vigentes['valorGlobal'].sum()-(v30['valorGlobal'].sum()+v60['valorGlobal'].sum()+v90['valorGlobal'].sum())):,.2f}".replace(",", "X").replace(".", ",").replace("X", "."))
    c36.metric("Percentual de contratos fora de risco", f"{((len(vigentes)-(len(v30)+len(v60)+len(v90)))/len(vigentes)*100):.1f}%" if len(vigentes) > 0 else "0%")
    colvigentes_1, colvigentes_2 = st.columns(2)
    numero_contrato = colvigentes_1.multiselect("Número do contrato",sorted(vigentes["numeroContrato"].dropna().unique()),
                                placeholder="Selecione uma ou mais opções")
    fornecedor = colvigentes_2.multiselect("Fornecedor",sorted(vigentes["nomeRazaoSocialFornecedor"].dropna().unique()),
                                placeholder="Selecione uma ou mais opções")
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
        c14.metric("Valor global total", f"R$ {v30['valorGlobal'].sum():,.2f}".replace(",", "X").replace(".", ",").replace("X", "."))
        c15.metric("Valor global do maior contrato", f"R$ {v30['valorGlobal'].max():,.2f}".replace(",", "X").replace(".", ",").replace("X", ".") if not v30.empty else "R$ 0,00")
        c16.metric("Média global por contrato", f"R$ {v30['valorGlobal'].mean():,.2f}".replace(",", "X").replace(".", ",").replace("X", ".") if not v30.empty else "R$ 0,00")
        colv30_1, colv30_2 = st.columns(2)
        numero_contrato = colv30_1.multiselect("Número do contrato",sorted(v30["numeroContrato"].dropna().unique()),
                                placeholder="Selecione uma ou mais opções")
        fornecedor = colv30_2.multiselect("Fornecedor",sorted(v30["nomeRazaoSocialFornecedor"].dropna().unique()),
                                placeholder="Selecione uma ou mais opções")
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
        c18.metric("Valor global total", f"R$ {v60['valorGlobal'].sum():,.2f}".replace(",", "X").replace(".", ",").replace("X", "."))
        c19.metric("Valor global do maior contrato", f"R$ {v60['valorGlobal'].max():,.2f}".replace(",", "X").replace(".", ",").replace("X", ".") if not v60.empty else "R$ 0,00")
        c20.metric("Média global por contrato", f"R$ {v60['valorGlobal'].mean():,.2f}".replace(",", "X").replace(".", ",").replace("X", ".") if not v60.empty else "R$ 0,00")
        colv60_1, colv60_2 = st.columns(2)
        numero_contrato = colv60_1.multiselect("Número do contrato",sorted(v60["numeroContrato"].dropna().unique()),
                                placeholder="Selecione uma ou mais opções")
        fornecedor = colv60_2.multiselect("Fornecedor",sorted(v60["nomeRazaoSocialFornecedor"].dropna().unique()),
                                placeholder="Selecione uma ou mais opções")
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
        c22.metric("Valor global total", f"R$ {v90['valorGlobal'].sum():,.2f}".replace(",", "X").replace(".", ",").replace("X", "."))
        c23.metric("Valor global do maior contrato", f"R$ {v90['valorGlobal'].max():,.2f}".replace(",", "X").replace(".", ",").replace("X", ".") if not v90.empty else "R$ 0,00")
        c24.metric("Média global por contrato", f"R$ {v90['valorGlobal'].mean():,.2f}".replace(",", "X").replace(".", ",").replace("X", ".") if not v90.empty else "R$ 0,00")
        colv90_1, colv90_2 = st.columns(2)
        numero_contrato = colv90_1.multiselect("Número do contrato",sorted(v90["numeroContrato"].dropna().unique()),
                                placeholder="Selecione uma ou mais opções")
        fornecedor = colv90_2.multiselect("Fornecedor",sorted(v90["nomeRazaoSocialFornecedor"].dropna().unique()),
                                placeholder="Selecione uma ou mais opções")
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
        c26.metric("Valor global total", f"R$ {vencidos['valorGlobal'].sum():,.2f}".replace(",", "X").replace(".", ",").replace("X", "."))
        c27.metric("Valor global do maior contrato", f"R$ {vencidos['valorGlobal'].max():,.2f}".replace(",", "X").replace(".", ",").replace("X", ".") if not vencidos.empty else "R$ 0,00")
        c28.metric("Média global por contrato", f"R$ {vencidos['valorGlobal'].mean():,.2f}".replace(",", "X").replace(".", ",").replace("X", ".") if not vencidos.empty else "R$ 0,00")
        colvencidos_1, colvencidos_2 = st.columns(2)
        numero_contrato = colvencidos_1.multiselect("Número do contrato",sorted(vencidos["numeroContrato"].dropna().unique()),
                                placeholder="Selecione uma ou mais opções")
        fornecedor = colvencidos_2.multiselect("Fornecedor",sorted(vencidos["nomeRazaoSocialFornecedor"].dropna().unique()),
                                placeholder="Selecione uma ou mais opções")
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
    analises_tab1, analises_tab2 = st.tabs(["Geral","Evolução temporal"])
    with analises_tab1:
        c1, c2, c3, c4 = st.columns(4)
        c1.metric("Quantidade total de contratos", len(df_comprasnet))
        c2.metric("Contratos vigentes", len(df_comprasnet[df_comprasnet["status"] == "Vigente"]))
        c3.metric("Contratos vencidos", len(df_comprasnet[df_comprasnet["status"] == "Vencido"]))
        c4.metric("Percentual de contratos vigentes", f'{(len(df_comprasnet[df_comprasnet["status"] == "Vigente"]) / len(df_comprasnet) * 100):.1f}%' if len(df_comprasnet) > 0 else "0%")
        
        c5, c6, c7, c8 = st.columns(4)
        c5.metric("Valor global total", f"R$ {df_comprasnet['valorGlobal'].sum():,.2f}".replace(",", "X").replace(".", ",").replace("X", "."))
        c6.metric("Valor global vigente", f"R$ {df_comprasnet[df_comprasnet['status']=='Vigente']['valorGlobal'].sum():,.2f}".replace(",", "X").replace(".", ",").replace("X", "."))
        c7.metric("Valor global vencido", f"R$ {df_comprasnet[df_comprasnet['status']=='Vencido']['valorGlobal'].sum():,.2f}".replace(",", "X").replace(".", ",").replace("X", "."))
        c8.metric("Fornecedores únicos", df_comprasnet["nomeRazaoSocialFornecedor"].nunique())
        st.divider()

        st.markdown("## Status dos Contratos")
        status_analise = df_comprasnet.groupby("status").agg(quantidade=("numeroContrato", "count"),
                valor_total=("valorGlobal", "sum"), valor_medio=("valorGlobal", "mean"),
                valor_minimo=("valorGlobal", "min"), valor_maximo=("valorGlobal", "max")).reset_index()
        col1, col2, col3 = st.columns(3)
        with col1:
            st.markdown("### Quantidade de contratos")
            st.plotly_chart(px.bar(status_analise,x="status",y="quantidade", color_discrete_sequence=["#00689D"],
                                labels={"status":"Status","quantidade":"Quantidade"}),use_container_width=True)
        with col2:
            st.markdown("### Valor global total")
            fig_total = px.bar(status_analise,x="status",y="valor_total",labels={"status":"Status","valor_total":"Valor global total (R$)"},
            color_discrete_sequence=["#00689D"])
            fig_total.update_yaxes(tickprefix="R$ ",separatethousands=True)
            st.plotly_chart(fig_total,use_container_width=True)
        with col3:
            st.markdown("### Ticket global médio")
            fig_medio = px.bar(status_analise,x="status",y="valor_medio",labels={"status":"Status","valor_medio":"Valor global médio (R$)"},
                            color_discrete_sequence=["#00689D"])
            fig_medio.update_yaxes(tickprefix="R$ ",separatethousands=True)
            st.plotly_chart(fig_medio,use_container_width=True)
        
        status_analise.columns = ['Status', 'Quantidade de contratos', 'Valor global total', 'Valor global médio', 
                                  'Valor global mínimo', 'Valor global máximo']
            
        with st.expander("Ver detalhes", expanded=False):
            st.dataframe(status_analise.style.format({"Valor global total": "R$ {:,.2f}", "Valor global médio": "R$ {:,.2f}",
                "Valor global mínimo": "R$ {:,.2f}", "Valor global máximo": "R$ {:,.2f}"}), use_container_width=True)
        st.divider()

        st.markdown("## Categoria dos contratos")
        cat_analise = df_comprasnet.groupby("nomeCategoria").agg(quantidade=("numeroContrato", "count"),
            valor_total=("valorGlobal", "sum"), valor_medio=("valorGlobal", "mean"),
            vigentes=("status", lambda x: (x == "Vigente").sum()),
            vencidos=("status", lambda x: (x == "Vencido").sum())).reset_index().sort_values("valor_total", ascending=False)
        cat_analise["perc_vigentes"] = (cat_analise["vigentes"] / cat_analise["quantidade"] * 100).round(1)
        col1, col2 = st.columns(2)
        with col1:
            st.markdown("### Quantidade de contratos")
            top_cat_qtd = cat_analise.sort_values("quantidade")
            st.plotly_chart(px.bar(top_cat_qtd,x="quantidade",y="nomeCategoria",orientation="h", color_discrete_sequence=["#00689D"],
                                labels={"quantidade":"Quantidade","nomeCategoria":"Categoria"}),
                                use_container_width=True)
        with col2:
            st.markdown("### Valor global total")
            top_cat_valor = cat_analise.sort_values("valor_total")
            fig_valor = px.bar(top_cat_valor,x="valor_total",y="nomeCategoria",orientation="h", 
                            labels={"valor_total":"Valor global(R$)","nomeCategoria":"Categoria"},
                            color_discrete_sequence=["#00689D"])
            fig_valor.update_xaxes(tickprefix="R$ ",separatethousands=True)
            st.plotly_chart(fig_valor,use_container_width=True)

        # Renomear colunas
        cat_display = cat_analise.copy()
        cat_display.columns = ['Categoria', 'Quantidade de contratos', 'Valor global total', 'Valor global médio', 'Vigentes', 
                               'Vencidos', '% Vigentes']
        with st.expander("Ver detalhes", expanded=False):
            st.dataframe(cat_display.reset_index(drop=True).style.format({"Valor global total": "R$ {:,.2f}","Valorglobal  médio": "R$ {:,.2f}",
                "% Vigentes": "{:.1f}%"}), use_container_width=True)
        st.divider()

        st.markdown("## Fornecedores dos contratos")
        forn_analise = df_comprasnet.groupby("nomeRazaoSocialFornecedor").agg(quantidade=("numeroContrato", "count"),
            valor_total=("valorGlobal", "sum"), valor_medio=("valorGlobal", "mean"), vigentes=("status", lambda x: (x == "Vigente").sum()),
            categorias=("nomeCategoria", "nunique")).reset_index().sort_values("valor_total", ascending=False)
        forn_analise["participacao_%"] = (forn_analise["valor_total"] / forn_analise["valor_total"].sum() * 100).round(2)
        forn_analise.columns = ['Fornecedor', 'Quantidade', 'Valor global total', 'Valor global médio', 'Vigentes', 
                                'Categorias', 'Frequência relativa %']
        
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
            st.markdown("### Quantidade de contratos")
            top_forn_qtd = forn_analise.copy()
            top_forn_qtd["nome_curto"] = top_forn_qtd["Fornecedor"].apply(quebrar_linha)
            top_forn_qtd = top_forn_qtd.head(15).sort_values("Quantidade")
            st.plotly_chart(px.bar(top_forn_qtd.head(15),x="Quantidade",y="nome_curto",orientation="h", color_discrete_sequence=["#00689D"],
                                labels={"quantidade":"Quantidade","nome_curto":"Fornecedor"}),
                                use_container_width=True)        
        with col2:
            st.markdown("### Valor global total")
            top_forn = forn_analise.copy()
            top_forn["nome_curto"] = top_forn["Fornecedor"].apply(quebrar_linha)
            top_forn = top_forn.head(15).sort_values("Valor global total")
            fig_forn_valor = px.bar(top_forn,x="Valor global total",y="nome_curto",orientation="h",
                                    labels={"Valor global total":"Valor (R$)","nome_curto":"Fornecedor"},
                                    color_discrete_sequence=["#00689D"])
            fig_forn_valor.update_xaxes(tickprefix="R$ ",separatethousands=True)
            st.plotly_chart(fig_forn_valor,use_container_width=True)

        with st.expander("Ver detalhes", expanded=False):
            st.dataframe(forn_analise.reset_index(drop=True).style.format({"Valor Total": "R$ {:,.2f}",
                "Valor Médio": "R$ {:,.2f}", "Frequência relativa %": "{:.2f}%"}), use_container_width=True)
        st.divider()

        st.markdown("## Modalidade de compra dos contratos")
        mod_analise = df_comprasnet.groupby("nomeModalidadeCompra").agg(quantidade=("numeroContrato", "count"), valor_total=("valorGlobal", "sum"), 
            valor_medio=("valorGlobal", "mean")).reset_index().sort_values("valor_total", ascending=False)
        mod_analise["participacao_%"] = (mod_analise["valor_total"] / mod_analise["valor_total"].sum() * 100).round(2)
        mod_analise.columns = ['Modalidade', 'Quantidade', 'Valor global total', 'Valor global médio', 'Frequência relativa %']
        col1, col2 = st.columns(2)
        with col1:
            st.markdown("### Quantidade de contratos")
            st.plotly_chart(px.bar(mod_analise,x="Modalidade",y="Quantidade",color_discrete_sequence=["#00689D"],
                                labels={"Modalidade":"Modalidade","Quantidade":"Quantidade"}),use_container_width=True)
            st.write("A modalidade 'Não se aplica' se refere a licitação decorrente de outros órgãos.")
        with col2:
            st.markdown("### Valor global total")
            fig_mod = px.bar(mod_analise,x="Modalidade",y="Valor global total",labels={"Modalidade":"Modalidade","Valor global total":"Valor (R$)"},
                            color_discrete_sequence=["#00689D"])
            fig_mod.update_yaxes(tickprefix="R$ ",separatethousands=True)
            st.plotly_chart(fig_mod,use_container_width=True)
        with st.expander("Ver detalhes", expanded=False):
            st.dataframe(mod_analise.reset_index(drop=True).style.format({"Valor global total": "R$ {:,.2f}",
                "Valor global médio": "R$ {:,.2f}", "Frequência relativa %": "{:.2f}%"}), use_container_width=True)

    with analises_tab2:
        st.markdown("## Evolução Temporal")
        evolucao = df_comprasnet.groupby("ano").agg(contratos=("numeroContrato", "count"),valor=("valorGlobal", "sum")).reset_index()
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
            fig_valor = px.bar(evolucao, x="ano", y="valor", labels={"ano": "Ano", "valor": "Valor global (R$)"},
                            color_discrete_sequence=["#00689D"])
            fig_valor.update_xaxes(tickangle=0, tickmode="linear", dtick=1)
            fig_valor.update_yaxes(tickprefix="R$ ", separatethousands=True)
            st.plotly_chart(fig_valor, use_container_width=True)
            st.caption(f"Média anual: R$ {evolucao['valor'].mean():,.2f}".replace(",", "X").replace(".", ",").replace("X", "."))
        evolucao["var_contratos_%"] = evolucao["contratos"].pct_change() * 100
        evolucao["var_valor_%"] = evolucao["valor"].pct_change() * 100
        evolucao["ticket_medio"] = evolucao["valor"] / evolucao["contratos"]
        evolucao_display = evolucao.copy()
        evolucao_display.columns = ['Ano', 'Contratos', 'Valor global', 'Variação da quantidade de contratos em relação ao ano anterior (%)', 
                                    'Variação dos valores globais dos contratos em relação ao ano anterior %', 'Ticket global médio']
        with st.expander("Ver detalhes", expanded=False):
            st.dataframe(evolucao_display.style.format({"Valor global": "R$ {:,.2f}",
            "Variação da quantidade de contratos em relação ao ano anterior (%)": "{:.1f}%",
            "Variação dos valores globais dos contratos em relação ao ano anterior %": "{:.1f}%",
            "Ticket médio global": "R$ {:,.2f}"}), use_container_width=True)

        st.divider()

        st.markdown("### Status × Ano")
        status_ano = pd.crosstab(df_comprasnet["status"], df_comprasnet["ano"], values=df_comprasnet["valorGlobal"], aggfunc="sum").fillna(0)
        fig_status_ano = go.Figure()
        for status in status_ano.index: 
            fig_status_ano.add_bar(x=status_ano.columns, y=status_ano.loc[status], name=status)
        fig_status_ano.update_layout(barmode="group", xaxis_title="Ano", yaxis_title="Valor global (R$)", height=450)
        st.plotly_chart(fig_status_ano, use_container_width=True)

        status_ano_display = status_ano.copy()
        for col in status_ano_display.columns: 
            status_ano_display[col] = status_ano_display[col].apply(lambda x: f"R$ {x:,.2f}".replace(",", "X").replace(".", ",").replace("X", "."))
        with st.expander("Ver detalhes", expanded=False): 
            st.dataframe(status_ano_display, use_container_width=True)
        st.divider()

        st.markdown("### Categoria × Ano")
        cat_ano = pd.crosstab(df_comprasnet["nomeCategoria"], df_comprasnet["ano"], values=df_comprasnet["valorGlobal"], aggfunc="sum").fillna(0)
        fig_cat_ano = go.Figure()
        for categoria in cat_ano.index: 
            fig_cat_ano.add_bar(x=cat_ano.columns, y=cat_ano.loc[categoria], name=categoria)
        fig_cat_ano.update_layout(barmode="group", xaxis_title="Ano", yaxis_title="Valor global (R$)", height=450)
        st.plotly_chart(fig_cat_ano, use_container_width=True)

        cat_ano_display = cat_ano.copy()
        for col in cat_ano_display.columns: 
            cat_ano_display[col] = cat_ano_display[col].apply(lambda x: f"R$ {x:,.2f}".replace(",", "X").replace(".", ",").replace("X", "."))
        with st.expander("Ver detalhes", expanded=False): 
            st.dataframe(cat_ano_display, use_container_width=True)
        st.divider()

        st.markdown("### Fornecedor × Ano")
        fornecedor_ano = pd.crosstab(df_comprasnet["nomeRazaoSocialFornecedor"], df_comprasnet["ano"], values=df_comprasnet["valorGlobal"], aggfunc="sum").fillna(0)
        fornecedores_base = fornecedor_ano.sum(axis=1).reset_index()
        fornecedores_base.columns = ["Fornecedor","Total"]
        opcoes_base = [3,5,10,15,20,25,30,50]
        opcoes_fornecedor = [i for i in opcoes_base if i < len(fornecedores_base)] + [len(fornecedores_base)]
        index_fornecedor = opcoes_fornecedor.index(len(fornecedores_base))
        top_fornecedor = st.selectbox("Selecione a quantidade de fornecedores para exibir:", opcoes_fornecedor, key="top_fornecedor_ano")
        fornecedores_top = fornecedores_base.nlargest(top_fornecedor,"Total")["Fornecedor"]
        fornecedor_ano_top = fornecedor_ano.loc[fornecedores_top]
        fig_fornecedor_ano = go.Figure()
        for fornecedor in fornecedor_ano_top.index:
            fig_fornecedor_ano.add_bar(x=fornecedor_ano_top.columns, y=fornecedor_ano_top.loc[fornecedor], name=fornecedor)
        fig_fornecedor_ano.update_layout(barmode="group", xaxis_title="Ano", yaxis_title="Valor global (R$)", height=450, legend_title_text="Fornecedor")
        st.plotly_chart(fig_fornecedor_ano, use_container_width=True)

        fornecedor_ano_display = fornecedor_ano.copy()
        for col in fornecedor_ano_display.columns: 
            fornecedor_ano_display[col] = fornecedor_ano_display[col].apply(lambda x: f"R$ {x:,.2f}".replace(",", "X").replace(".", ",").replace("X", "."))
        with st.expander("Ver detalhes", expanded=False): 
            st.dataframe(fornecedor_ano_display, use_container_width=True)
        st.divider()

        st.markdown("### Modalidade × Ano")
        mod_ano = pd.crosstab(df_comprasnet["nomeModalidadeCompra"], df_comprasnet["ano"], values=df_comprasnet["valorGlobal"], aggfunc="sum").fillna(0)

        fig_mod_ano = go.Figure()
        for modalidade in mod_ano.index: 
            fig_mod_ano.add_bar(x=mod_ano.columns, y=mod_ano.loc[modalidade], name=modalidade)
        fig_mod_ano.update_layout(barmode="group", xaxis_title="Ano", yaxis_title="Valor global (R$)", height=450)
        st.plotly_chart(fig_mod_ano, use_container_width=True)
        st.write("A modalidade 'Não se aplica' se refere a licitação decorrente de outros órgãos.")
        mod_ano_display = mod_ano.copy()
        for col in mod_ano_display.columns: 
            mod_ano_display[col] = mod_ano_display[col].apply(lambda x: f"R$ {x:,.2f}".replace(",", "X").replace(".", ",").replace("X", "."))
        with st.expander("Ver detalhes", expanded=False): 
            st.dataframe(mod_ano_display, use_container_width=True)

# ==================== ABA 4: VISÃO GERAL & FILTROS ====================
with tab4:
    st.subheader("Análise Financeira")
    subtab1_fin, subtab2_fin, subtab3_fin, subtab4_fin = st.tabs(["Análises", "Perfil dos Gestores", "Núcleo/Divisão/Seção", "Centro de Custos"])
    with subtab1_fin:    
        col1, col2, col3, col4 = st.columns(4)
        with col1:
            anos_disponiveis = sorted(df_resumo['Ano'].unique())
            ano_selecionado = st.multiselect("Ano", options=anos_disponiveis, default=[], key="ano_tab1",
                                placeholder="Selecione uma ou mais opções")
        with col2:
            gestores_disponiveis = sorted([g for g in df_resumo['Gestor(a)'].unique() if g != 'Não informado'])
            gestor_selecionado = st.multiselect("Gestor", options=['Todos'] + gestores_disponiveis, default=[], key="gestor_tab1",
                                placeholder="Selecione uma ou mais opções")
        with col3:
            nucleo_div_disponiveis = sorted([c for c in df_resumo['Núcleo_Divisão_Seção'].unique() if c != 'Não informado'])
            nucleo_div_selecionado = st.multiselect("Núcleo/Divisão/Seção", options=['Todos'] + nucleo_div_disponiveis, default=[], key="nucleo_div_tab1",
                                placeholder="Selecione uma ou mais opções")
        with col4:
            centros_disponiveis = sorted([c for c in df_resumo['Centro de Custo'].unique() if c != 'Não informado'])
            centro_selecionado = st.multiselect("Centro de Custo", options=['Todos'] + centros_disponiveis, default=[], key="centro_tab1",
                                placeholder="Selecione uma ou mais opções")

        df_filtered = df_resumo.copy()
        if ano_selecionado:
            df_filtered = df_filtered[df_filtered['Ano'].isin(ano_selecionado)]
        if gestor_selecionado and 'Todos' not in gestor_selecionado:
            df_filtered = df_filtered[df_filtered['Gestor(a)'].isin(gestor_selecionado)]
        if nucleo_div_selecionado and 'Todos' not in nucleo_div_selecionado:
            df_filtered = df_filtered[df_filtered['Núcleo_Divisão_Seção'].isin(nucleo_div_selecionado)]
        if centro_selecionado and 'Todos' not in centro_selecionado:
            df_filtered = df_filtered[df_filtered['Centro de Custo'].isin(centro_selecionado)]
        
        st.markdown("---")
        
        limite_gastos = df_filtered['Limite'].sum()
        valor_pre_empenhado = df_filtered['Pré-empenhado'].sum()
        valor_empenhado = df_filtered['Empenhado'].sum()
        valor_pago = df_filtered['Valor Empenhos Pagos'].sum()
        limite_disponivel = limite_gastos - valor_pre_empenhado - valor_empenhado
        valor_a_pagar = valor_empenhado - valor_pago
        valor_a_pagar = 0.0 if abs(valor_a_pagar) <= 1e-9 else valor_a_pagar
        
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
        st.dataframe(resumo_display.style.map(marcar_negativo,subset=['Disponível']),use_container_width=True)
    with subtab2_fin:
        st.header("Perfil dos Gestores")
        col1_g, col2_g, col3_g, col4_g= st.columns(4)
        with col1_g:
            ano_gest = st.multiselect("Ano", options=anos_disponiveis, 
                                    default=ano_selecionado if ano_selecionado else [], key="ano_gest",
                                    placeholder="Selecione uma ou mais opções")
        with col2_g:
            gestor_gest = st.multiselect("Gestor", options=['Todos'] + gestores_disponiveis, 
                                default=gestor_selecionado if gestor_selecionado else [], key="gestor_gest",
                                placeholder="Selecione uma ou mais opções")
        with col3_g:
            nucleo_div_gest = st.multiselect("Núcleo/Divisão/Seção", options=['Todos'] + nucleo_div_disponiveis, 
                                default=nucleo_div_selecionado if nucleo_div_selecionado else [], key="nucleo_div_gest",
                                placeholder="Selecione uma ou mais opções")
        with col4_g:
            centro_gest = st.multiselect("Centro de Custo", options=['Todos'] + centros_disponiveis, 
                                default=centro_selecionado if centro_selecionado else [], key="centro_gest",
                                placeholder="Selecione uma ou mais opções")

        df_gestores = df_resumo.copy()
        if ano_gest:
            df_gestores = df_gestores[df_gestores['Ano'].isin(ano_gest)]
        if gestor_gest and 'Todos' not in gestor_gest:
            df_gestores = df_gestores[df_gestores['Gestor(a)'].isin(gestor_gest)]
        if nucleo_div_gest and 'Todos' not in nucleo_div_gest:
            df_gestores = df_gestores[df_gestores['Núcleo_Divisão_Seção'].isin(nucleo_div_gest)]
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
            if len(gestores_top) < 14:
                fig.update_layout(barmode="group", height=300 + len(gestores_top) * 35, xaxis_title="Valor (R$)", yaxis_title=None, legend_title=None, hovermode="y unified", separators=",.")
            else:
                fig.update_layout(barmode="group", height=500 + len(gestores_top) * 35, xaxis_title="Valor (R$)", yaxis_title=None, legend_title=None, hovermode="y unified", separators=",.")
            
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
            st.dataframe(gestores_display, use_container_width=True)

    with subtab3_fin:
        st.header("Análise por Núcleo/Divisão/Seção")
        col1_nds, col2_nds, col3_nds, col4_nds = st.columns(4)
        with col1_nds:
            ano_nucleo_div = st.multiselect("Ano", options=anos_disponiveis, 
                                default=ano_selecionado if ano_selecionado else [], key="ano_nucleo_div",
                                placeholder="Selecione uma ou mais opções")
        with col2_nds:
            gestor_nucleo_div = st.multiselect("Gestor", options=['Todos'] + gestores_disponiveis, 
                                default=gestor_selecionado if gestor_selecionado else [], key="gestor_nucleo_div",
                                placeholder="Selecione uma ou mais opções")
        with col3_nds:
            nucleo_div_nucleo_div = st.multiselect("Núcleo/Divisão/Seção", options=['Todos'] + nucleo_div_disponiveis, 
                                default=nucleo_div_selecionado if nucleo_div_selecionado else [], key="nucleo_div_nucleo_div",
                                placeholder="Selecione uma ou mais opções")
        with col4_nds:
            centro_nucleo_div = st.multiselect("Centro de Custo", options=['Todos'] + centros_disponiveis, 
                                default=centro_selecionado if centro_selecionado else [], key="centro_nucleo_div",
                                placeholder="Selecione uma ou mais opções")
        
        df_nucleo_div = df_resumo.copy()
        if ano_nucleo_div:
            df_nucleo_div = df_nucleo_div[df_nucleo_div['Ano'].isin(ano_nucleo_div)]
        if gestor_nucleo_div and 'Todos' not in gestor_nucleo_div:
            df_nucleo_div = df_nucleo_div[df_nucleo_div['Gestor(a)'].isin(gestor_nucleo_div)]
        if nucleo_div_nucleo_div and 'Todos' not in nucleo_div_nucleo_div:
            df_nucleo_div = df_nucleo_div[df_nucleo_div['Núcleo_Divisão_Seção'].isin(nucleo_div_nucleo_div)]
        if centro_nucleo_div and 'Todos' not in centro_nucleo_div:
            df_nucleo_div = df_nucleo_div[df_nucleo_div['Centro de Custo'].isin(centro_nucleo_div)]
        df_nucleo_div = df_nucleo_div[df_nucleo_div['Centro de Custo'] != 'Não informado'].copy()
        
        st.markdown("---")
        
        if len(df_nucleo_div) == 0:
            st.warning("Não há dados de centros de custo para os filtros selecionados.")
        else:
            nucleo_div_agg = df_nucleo_div.groupby('Núcleo_Divisão_Seção').agg({'Limite': 'sum', 'Empenhado': 'sum',
                'Valor Empenhos Pagos': 'sum', 'Pré-empenhado': 'sum'}).reset_index()
            nucleo_div_agg['Disponível'] = (nucleo_div_agg['Limite'] - nucleo_div_agg['Pré-empenhado'] - nucleo_div_agg['Empenhado'])
            nucleo_div_agg['A Pagar'] = nucleo_div_agg['Empenhado'] - nucleo_div_agg['Valor Empenhos Pagos']
            nucleo_div_agg['% Execução'] = (nucleo_div_agg['Empenhado'] / nucleo_div_agg['Limite'] * 100)

            col1, col2, col3 = st.columns(3)
            with col1:
                st.metric("Quantidade de núcleos/divisões/seções", len(nucleo_div_agg))
            with col2:
                st.metric("Total empenhado", formatar_real(nucleo_div_agg['Empenhado'].sum()))
            with col3:
                st.metric("Total pago", formatar_real(nucleo_div_agg['Valor Empenhos Pagos'].sum()))
            st.markdown("---")

            st.subheader("Empenhado x Pago por Núcleo/Divisão/Seção")
            nucleo_div_base = nucleo_div_agg.groupby("Núcleo_Divisão_Seção", as_index=False)[["Empenhado","Valor Empenhos Pagos"]].sum()
            opcoes_nucleo_div = [3,5,10,15,20,25,30]
            index_nucleo_div = 1 if len(nucleo_div_base) >= 10 else 0
            top_nucleo_div = st.selectbox("Selecione a quantidade de centros para exibir:", opcoes_nucleo_div, index=index_nucleo_div, key="top_nucleo_div_execucao")
            nucleo_div_top = nucleo_div_base.nlargest(top_nucleo_div, "Empenhado").sort_values("Empenhado", ascending=True)
            fig = go.Figure()
            fig.add_trace(go.Bar(name="Empenhado", y=nucleo_div_top["Núcleo_Divisão_Seção"], x=nucleo_div_top["Empenhado"], orientation="h", marker_color="#0068c9", text=nucleo_div_top["Empenhado"].apply(formatar_real), textposition="auto"))
            fig.add_trace(go.Bar(name="Pago", y=nucleo_div_top["Núcleo_Divisão_Seção"], x=nucleo_div_top["Valor Empenhos Pagos"], orientation="h", marker_color="#28a745", text=nucleo_div_top["Valor Empenhos Pagos"].apply(formatar_real), textposition="auto"))
            if len(nucleo_div_top) < 14:
                fig.update_layout(barmode="group", height=300 + len(nucleo_div_top) * 35, xaxis_title="Valor (R$)", yaxis_title=None, legend_title=None, hovermode="y unified", separators=",.")
            else:
                fig.update_layout(barmode="group", height=500 + len(nucleo_div_top) * 35, xaxis_title="Valor (R$)", yaxis_title=None, legend_title=None, hovermode="y unified", separators=",.")
            st.plotly_chart(fig, use_container_width=True)
                                        
            st.markdown("---")
            st.subheader("Valores por ano")
            df_nucleo_div['A Pagar'] = df_nucleo_div['Empenhado'] - df_nucleo_div['Valor Empenhos Pagos']
            nucleo_div_ano_agg = df_nucleo_div.groupby(['Ano', 'Núcleo_Divisão_Seção']).agg({'Limite': 'sum', 'Empenhado': 'sum',
                'Valor Empenhos Pagos': 'sum', 'Pré-empenhado': 'sum', 'A Pagar': 'sum'}).reset_index()
            nucleo_div_ano_agg['Disponível'] = (nucleo_div_ano_agg['Limite'] - nucleo_div_ano_agg['Pré-empenhado'] - nucleo_div_ano_agg['Empenhado'])
            nucleo_div__display = nucleo_div_ano_agg.copy()
            for col in ['Limite', 'Empenhado', 'Valor Empenhos Pagos', 'Pré-empenhado', 'Disponível', 'A Pagar']:
                nucleo_div__display[col] = nucleo_div__display[col].apply(formatar_real)
            st.dataframe(nucleo_div__display, use_container_width=True)   

    with subtab4_fin:
        st.header("Análise por Centro de Custos")
        col1_c, col2_c, col3_c, col4_c = st.columns(4)
        with col1_c:
            ano_centro = st.multiselect("Ano", options=anos_disponiveis, 
                                default=ano_selecionado if ano_selecionado else [], key="ano_centro",
                                placeholder="Selecione uma ou mais opções")
        with col2_c:
            gestor_centro = st.multiselect("Gestor", options=['Todos'] + gestores_disponiveis, 
                                default=gestor_selecionado if gestor_selecionado else [], key="gestor_centro",
                                placeholder="Selecione uma ou mais opções")
        with col3_c:
            nucleo_div_centro = st.multiselect("Núcleo/Divisão/Seção", options=['Todos'] + nucleo_div_disponiveis, 
                                default=nucleo_div_selecionado if nucleo_div_selecionado else [], key="nucleo_div_centro",
                                placeholder="Selecione uma ou mais opções")
        with col4_c:
            centro_centro = st.multiselect("Centro de Custo", options=['Todos'] + centros_disponiveis, 
                                default=centro_selecionado if centro_selecionado else [], key="centro_centro",
                                placeholder="Selecione uma ou mais opções")
        
        df_centros = df_resumo.copy()
        if ano_centro:
            df_centros = df_centros[df_centros['Ano'].isin(ano_centro)]
        if gestor_centro and 'Todos' not in gestor_centro:
            df_centros = df_centros[df_centros['Gestor(a)'].isin(gestor_centro)]
        if nucleo_div_centro and 'Todos' not in nucleo_div_centro:
            df_centros = df_centros[df_centros['Núcleo_Divisão_Seção'].isin(nucleo_div_centro)]
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
            if len(centros_top) < 14:
                fig.update_layout(barmode="group", height=300 + len(centros_top) * 35, xaxis_title="Valor (R$)", yaxis_title=None, legend_title=None, hovermode="y unified", separators=",.")
            else:
                fig.update_layout(barmode="group", height=500 + len(centros_top) * 35, xaxis_title="Valor (R$)", yaxis_title=None, legend_title=None, hovermode="y unified", separators=",.")
            st.plotly_chart(fig, use_container_width=True)
                                        
            st.markdown("---")
            st.subheader("Valores por ano")
            df_centros['A Pagar'] = df_centros['Empenhado'] - df_centros['Valor Empenhos Pagos']
            centros_ano_agg = df_centros.groupby(['Ano', 'Centro de Custo']).agg({'Limite': 'sum', 'Empenhado': 'sum',
                'Valor Empenhos Pagos': 'sum', 'Pré-empenhado': 'sum', 'A Pagar': 'sum'}).reset_index()
            centros_ano_agg['Disponível'] = (centros_ano_agg['Limite'] - centros_ano_agg['Pré-empenhado'] - centros_ano_agg['Empenhado'])
            centros_display = centros_ano_agg.copy()
            for col in ['Limite', 'Empenhado', 'Valor Empenhos Pagos', 'Pré-empenhado', 'Disponível', 'A Pagar']:
                centros_display[col] = centros_display[col].apply(formatar_real)
            st.dataframe(centros_display, use_container_width=True)            

# ==================== ABA 5: DADOS ORÇAMENTÁRIOS ====================
with tab5:
    st.subheader("Dados Orçamentários")
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
                    ano_emp = st.multiselect("Ano", options=anos_emp, default=[], key="ano_emp",
                                placeholder="Selecione uma ou mais opções")
            with col2_f:
                if 'Favorecido' in df_empenhos.columns:
                    favorecidos = sorted([f for f in df_empenhos['Favorecido'].unique() if f != 'Não informado'][:100])
                    favorecido_emp = st.selectbox("Favorecido", options=['Todos'] + favorecidos, key="fav_emp",
                                placeholder="Selecione uma ou mais opções")
            with col3_f:
                if 'Grupo' in df_empenhos.columns:
                    grupos = sorted(df_empenhos['Grupo'].dropna().unique().tolist())
                    grupo_emp = st.multiselect("Grupo", options=grupos, default=[], key="grupo_emp",
                                placeholder="Selecione uma ou mais opções")
            
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
                    ano_emp = st.multiselect("Ano", options=anos_emp, default=[], key="ano_pre_emp",
                                placeholder="Selecione uma ou mais opções")
            with col2_f:
                if 'Natureza' in df_pre_empenhos.columns:
                    natureza = sorted([f for f in df_pre_empenhos['Natureza'].unique() if f != 'Não informado'][:100])
                    natureza_emp = st.multiselect("Natureza", options=natureza, default=[], key="fav_pre_emp",
                                placeholder="Selecione uma ou mais opções")
            with col3_f:
                if 'Grupo' in df_pre_empenhos.columns:
                    grupos = sorted(df_pre_empenhos['Grupo'].dropna().unique().tolist())
                    grupo_emp = st.multiselect("Grupo", options=grupos, default=[], key="grupo_pre_emp",
                                placeholder="Selecione uma ou mais opções")
            
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
                    ano_emp = st.multiselect("Ano", options=anos_emp, default=[], key="ano_rp",
                                placeholder="Selecione uma ou mais opções")
            with col2_f:
                if 'Favorecido' in df_rp.columns:
                    favorecidos = sorted([f for f in df_rp['Favorecido'].unique() if f != 'Não informado'][:100])
                    favorecido_emp = st.selectbox("Favorecido", options=['Todos'] + favorecidos, key="fav_rp",
                                placeholder="Selecione uma ou mais opções")
            with col3_f:
                if 'Grupo' in df_rp.columns:
                    grupos = sorted(df_rp['Grupo'].dropna().unique().tolist())
                    grupo_emp = st.multiselect("Grupo", options=grupos, default=[], key="grupo_rp",
                                placeholder="Selecione uma ou mais opções")
            
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

# ==================== ABA 6: INCONSISTÊNCIAS DOS DADOS ====================
with tab6:
    st.subheader("Inconsistências nos dados dos sistemas")
    st.info("""Esta aba compara os dados do **ComprasNet** com os dados do **Portal TRF5** (Empenhos, Pré-Empenhos e Restos a Pagar).""")
    
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
    
    df_comprasnet_copy = df_comprasnet.copy()
    df_comprasnet_copy['numeroContrato_original'] = df_comprasnet_copy['numeroContrato']
    df_comprasnet_copy['numeroContrato'] = df_comprasnet_copy['numeroContrato'].apply(normalizar_contrato)
    df_portal_consolidado = pd.DataFrame()
    dfs_portal = [('Empenhos', df_empenhos), ('Pré-Empenhos', df_pre_empenhos), ('Restos a Pagar', df_rp)]
    for nome_df, df_temp in dfs_portal:
        if df_temp is not None and not df_temp.empty and 'Contrato' in df_temp.columns:
            df_temp_copy = df_temp.copy()
            df_temp_copy['Origem portal'] = nome_df
            df_temp_copy['Contrato_original'] = df_temp_copy['Contrato']
            df_temp_copy['Contrato'] = df_temp_copy['Contrato'].apply(normalizar_contrato)
            df_portal_consolidado = pd.concat([df_portal_consolidado, df_temp_copy], ignore_index=True)
    if df_portal_consolidado.empty:
        st.warning("⚠️ Não foram encontrados dados do Portal TRF5 com a coluna 'Contrato'.")
    else:
        contratos_comprasnet = set(df_comprasnet_copy['numeroContrato'].unique())
        contratos_portal = set(df_portal_consolidado['Contrato'].dropna().unique())
        contratos_comprasnet.discard('')
        contratos_portal.discard('')
        contratos_ambos = contratos_comprasnet & contratos_portal
        contratos_so_comprasnet = contratos_comprasnet - contratos_portal
        contratos_so_portal = contratos_portal - contratos_comprasnet
        
        # Métricas principais
        col1, col2, col3, col4 = st.columns(4)
        with col1:
            st.metric("Contratos no ComprasNet", f"{len(contratos_comprasnet):,}")
        with col2:
            st.metric("Contratos no Portal TRF5", f"{len(contratos_portal):,}")
        with col3:
            st.metric("Em Ambos", f"{len(contratos_ambos):,}")
        with col4:
            perc_match = (len(contratos_ambos) / len(contratos_comprasnet) * 100) if len(contratos_comprasnet) > 0 else 0
            st.metric("% Correspondência", f"{perc_match:.1f}%")
        
        st.markdown("---")
        st.subheader("Distribuição de Contratos")        
        col1, col2 = st.columns(2)
        with col1:
            fig_dist = go.Figure(data=[go.Pie(labels=['Em Ambos', 'Só ComprasNet', 'Só Portal'],
                values=[len(contratos_ambos), len(contratos_so_comprasnet), len(contratos_so_portal)],
                marker=dict(colors=['#28a745', '#ffc107', '#dc3545']), hole=0.4)])
            fig_dist.update_layout(height=400)
            st.plotly_chart(fig_dist, use_container_width=True)
        with col2:
            dados_comp = pd.DataFrame({'Categoria': ['ComprasNet Total', 'Portal TRF5 Total', 'Correspondência'], 
                                       'Quantidade': [len(contratos_comprasnet), len(contratos_portal), len(contratos_ambos)]}) 
            fig_comp = go.Figure() 
            fig_comp.add_trace(go.Bar(x=dados_comp['Categoria'], y=dados_comp['Quantidade'], 
                                      marker_color=['#28a745', '#ffc107', '#dc3545'], 
                                      text=dados_comp['Quantidade'], textposition='auto')) 
            fig_comp.update_layout(yaxis_title="Quantidade de Contratos", height=400) 
            st.plotly_chart(fig_comp, use_container_width=True)
        st.markdown("---")

        rec_tab1, rec_tab2, rec_tab3 = st.tabs(["Em Ambos", "Somente ComprasNet", "Somente Portal"])
        with rec_tab1:
            st.subheader("Contratos presentes em ambas as bases")
            if len(contratos_ambos) > 0:
                df_ambos = df_comprasnet_copy[df_comprasnet_copy['numeroContrato'].isin(contratos_ambos)][
                    ['numeroContrato', 'nomeRazaoSocialFornecedor', 'objeto', 'valorGlobal', 
                     'dataVigenciaInicial', 'dataVigenciaFinal', 'status']].sort_values('valorGlobal', ascending=False)
                df_portal_info = df_portal_consolidado[df_portal_consolidado['Contrato'].isin(contratos_ambos)]
                col1, col2, col3 = st.columns(3)
                with col1:
                    st.metric("Quantidade de contratos compatibilizados", f"{len(df_ambos):,}")
                df_ambos = df_ambos.reset_index(drop=True)
                #df_ambos.columns = colunas_renomeadas
                st.dataframe(df_ambos, use_container_width=True)     
                buffer = io.BytesIO()
                with pd.ExcelWriter(buffer, engine="openpyxl") as writer:
                    df_ambos.to_excel(writer, index=False, sheet_name="Contratos em Ambos")
                buffer.seek(0)
                timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                st.download_button(label="⬇️ Baixar dados", data=buffer, file_name=f"Contratos ambos portais {timestamp}.xlsx",
                    mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")
            else:
                st.info("Nenhum contrato encontrado em ambas as bases.")
        
        with rec_tab2:
            st.subheader("Contratos presentes apenas no ComprasNet")
            st.markdown("""**Atenção:** Estes contratos estão cadastrados no ComprasNet mas não foram encontrados em nenhuma base do Portal TRF5 (Empenhos, Pré-Empenhos ou Restos a Pagar).""")
            
            if len(contratos_so_comprasnet) > 0:
                df_so_comprasnet = df_comprasnet_copy[df_comprasnet_copy['numeroContrato'].isin(contratos_so_comprasnet)][
                    ['numeroContrato', 'nomeRazaoSocialFornecedor', 'objeto', 'valorGlobal', 
                     'dataVigenciaInicial', 'dataVigenciaFinal', 'status']].sort_values('valorGlobal', ascending=False)
                
                st.metric("Total de Contratos", f"{len(df_so_comprasnet):,}")
                df_so_comprasnet = df_so_comprasnet.reset_index(drop=True)
                st.dataframe(df_so_comprasnet, use_container_width=True)
                
                buffer = io.BytesIO()
                with pd.ExcelWriter(buffer, engine="openpyxl") as writer:
                    df_so_comprasnet.to_excel(writer, index=False, sheet_name="Só ComprasNet")
                buffer.seek(0)
                timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                st.download_button(label="⬇️ Baixar dados", data=buffer, 
                    file_name=f"Contratos presentes apenas no ComprasNet {timestamp}.xlsx",
                    mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")
            else:
                st.success("✅ Todos os contratos do ComprasNet foram encontrados no Portal!")
        
        with rec_tab3:
            st.subheader("Contratos presentes apenas no Portal TRF5")
            st.markdown("""**Atenção:** Estes contratos estão no Portal TRF5 (Empenhos, Pré-Empenhos ou Restos a Pagar) mas não foram encontrados no ComprasNet.""")
            st.markdown("""No Portal TRF5 há contratos que já foram encerrados e ainda estão presentes.""")
            
            if len(contratos_so_portal) > 0:
                # Preparar dados resumidos para visualização
                colunas_exibir = ['Contrato', 'Origem portal']
                for col in ['Favorecido Nome', 'Valor Empenhos Total', 'Data Emissão', 'Ano', 'Valor']:
                    if col in df_portal_consolidado.columns:
                        colunas_exibir.append(col)
                df_so_portal_resumo = df_portal_consolidado[df_portal_consolidado['Contrato'].isin(contratos_so_portal)][colunas_exibir].drop_duplicates(subset=['Contrato'])
                valor_col = 'Valor Empenhos Total' if 'Valor Empenhos Total' in df_so_portal_resumo.columns else (
                    'Valor' if 'Valor' in df_so_portal_resumo.columns else 'Contrato')
                
                col1, col2 = st.columns(2)
                with col1:
                    st.metric("Total de Contratos", f"{len(df_so_portal_resumo):,}")
                with col2:
                    if 'Valor Empenhos Total' in df_so_portal_resumo.columns:
                        total_val = pd.to_numeric(df_so_portal_resumo['Valor Empenhos Total'], errors='coerce').sum()
                        st.metric("Valor Total Empenhado", formatar_real(total_val))
                    elif 'Valor' in df_so_portal_resumo.columns:
                        total_val = pd.to_numeric(df_so_portal_resumo['Valor'], errors='coerce').sum()
                        st.metric("Valor Total", formatar_real(total_val))
                df_so_portal_resumo = df_so_portal_resumo.reset_index(drop=True)
                st.dataframe(df_so_portal_resumo, use_container_width=True)
                with pd.ExcelWriter(buffer, engine="openpyxl") as writer:
                    df_so_portal_resumo.to_excel(writer, index=False, sheet_name="Só ComprasNet")
                buffer.seek(0)
                timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                st.download_button(label="⬇️ Baixar dados", data=buffer, 
                    file_name=f"Contratos presentes apenas no Portal TRF5 {timestamp}.xlsx",
                    mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")
            else:
                st.success("✅ Todos os contratos do Portal foram encontrados no ComprasNet!")

# ==================== ABA 7: ANÁLISE DETALHADA DE CONTRATOS ====================
with tab7:
    st.subheader("Resumo geral")
    st.markdown("""Esta aba apresenta uma análise dos contratos compatibilizados entre Comprasnet e Portal TRF5.""")
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
    df_comprasnet2 = df_comprasnet.copy()
    df_comprasnet2["contrato_norm"] = df_comprasnet2["numeroContrato"].apply(normalizar_contrato)
    df_resumo["contrato_norm"] = df_resumo["Contrato"].apply(normalizar_contrato)
    contratos_em_ambos = set(df_comprasnet2["contrato_norm"]).intersection(set(df_resumo["contrato_norm"]))
    df_resumo_filtrado = df_resumo[df_resumo["contrato_norm"].isin(contratos_em_ambos)]
    df_resumo_comprasnet = df_resumo_filtrado.merge(df_comprasnet2, on="contrato_norm", how="left")
    
    # Criar base única de contratos (para alertas de vigência)
    df_contratos = df_resumo_comprasnet.groupby('contrato_norm').agg({
        'numeroContrato': 'first',
        'nomeRazaoSocialFornecedor': 'first',
        'dataVigenciaInicial': 'first',
        'dataVigenciaFinal': 'first',
        'valorGlobal': 'first',
        'status': 'first',
        'Valor Empenhos Total': lambda x: pd.to_numeric(x, errors='coerce').sum(),
        'Valor Empenhos Pagos': lambda x: pd.to_numeric(x, errors='coerce').sum()}).reset_index()
    
    # Calcular valores
    df_contratos['Valor a Pagar'] = df_contratos['Valor Empenhos Total'] - df_contratos['Valor Empenhos Pagos']
    
    # Converter datas
    df_contratos['dataVigenciaFinal'] = pd.to_datetime(df_contratos['dataVigenciaFinal'], errors='coerce')
    df_contratos['dataVigenciaInicial'] = pd.to_datetime(df_contratos['dataVigenciaInicial'], errors='coerce')
    
    # Calcular dias até vencimento
    hoje = pd.Timestamp.now()
    df_contratos['Dias até Vencimento'] = (df_contratos['dataVigenciaFinal'] - hoje).dt.days
    
    # Classificar alertas
    def classificar_alerta(dias):
        if pd.isna(dias):
            return 'Sem Data'
        elif dias < 0:
            return 'Vencido'
        elif dias <= 30:
            return 'Crítico (≤30 dias)'
        elif dias <= 90:
            return 'Atenção (≤90 dias)'
        else:
            return 'Normal'
    df_contratos['Alerta Vigência'] = df_contratos['Dias até Vencimento'].apply(classificar_alerta)
    
    col1, col2, col3, col4 = st.columns(4)
    with col1:
        st.metric("Total Contratos", f"{len(df_contratos):,}")
    with col2:
        vencidos = len(df_contratos[df_contratos['Alerta Vigência'] == 'Vencido'])
        st.metric("Vencidos", f"{vencidos:,}", delta_color="inverse")
    with col3:
        criticos = len(df_contratos[df_contratos['Alerta Vigência'] == 'Crítico (≤30 dias)'])
        st.metric("Críticos (≤30d)", f"{criticos:,}", delta_color="inverse")
    with col4:
        atencao = len(df_contratos[df_contratos['Alerta Vigência'] == 'Atenção (≤90 dias)'])
        st.metric("Atenção (≤90d)", f"{atencao:,}", delta_color="inverse")
    st.markdown("---")
    st.subheader("🚨 Alertas de vigência")
    tab_vig, tab_gestor, tab_nucleo_div, tab_cc = st.tabs(["Geral", "Gestor", "Núcleo/Divisão/Seção", "Centro de Custo"])
    with tab_vig:
        alertas_selecionados = st.multiselect("Filtrar por status:",
            options=['Vencido', 'Crítico (≤30 dias)', 'Atenção (≤90 dias)', 'Normal', 'Sem Data'],
            default=['Crítico (≤30 dias)', 'Atenção (≤90 dias)'])
        if alertas_selecionados:
            df_filtrado = df_contratos[df_contratos['Alerta Vigência'].isin(alertas_selecionados)].copy()
            df_filtrado = df_filtrado.sort_values('Dias até Vencimento', na_position='last')
            gestores_por_contrato = df_resumo.groupby('contrato_norm')['Gestor(a)'].apply(
                lambda x: ', '.join(sorted(set(str(v) for v in x.dropna().unique())))).to_dict()
            cc_por_contrato = df_resumo.groupby('contrato_norm')['Centro de Custo'].apply(
                lambda x: ', '.join(sorted(set(str(v) for v in x.dropna().unique())))).to_dict()
            df_filtrado['Gestores'] = df_filtrado['contrato_norm'].map(gestores_por_contrato)
            df_filtrado['Centros de Custo'] = df_filtrado['contrato_norm'].map(cc_por_contrato)
            
            df_exibir = df_filtrado[['numeroContrato', 'nomeRazaoSocialFornecedor', 'Gestores', 'Centros de Custo',
                'dataVigenciaFinal', 'Dias até Vencimento', 'Alerta Vigência',
                'valorGlobal', 'Valor Empenhos Total', 'Valor Empenhos Pagos', 'Valor a Pagar']].copy()
            df_exibir['dataVigenciaFinal'] = df_exibir['dataVigenciaFinal'].dt.strftime('%d/%m/%Y')
            df_exibir.columns = ['Contrato', 'Fornecedor', 'Gestores', 'Centros de Custo',
                'Vencimento', 'Dias', 'Alerta', 'Valor Global', 'Empenhado', 'Pago', 'A Pagar']
            st.metric("Quantidade de contratos", f"{len(df_exibir):,}")
            df_exibir = df_exibir.reset_index(drop=True)
            st.dataframe(df_exibir, use_container_width=True)
            buffer = io.BytesIO()
            with pd.ExcelWriter(buffer, engine="openpyxl") as writer:
                df_exibir.to_excel(writer, index=False, sheet_name="Alertas")
            buffer.seek(0)
            st.download_button("⬇️ Baixar Excel", buffer,
                               f"Alertas vigência {datetime.now().strftime('%Y%m%d')}.xlsx",
                               mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")
    with tab_gestor:
        df_gestor_contrato = df_resumo_comprasnet.groupby(['Gestor(a)', 'contrato_norm']).agg({
            'valorGlobal': 'first',
            'Valor Empenhos Total': lambda x: pd.to_numeric(x, errors='coerce').sum(),
            'Valor Empenhos Pagos': lambda x: pd.to_numeric(x, errors='coerce').sum()}).reset_index()
        
        df_gestor_contrato['Valor a Pagar'] = (df_gestor_contrato['Valor Empenhos Total'] - df_gestor_contrato['Valor Empenhos Pagos'])
        df_gestor_contrato = df_gestor_contrato.merge(df_contratos[['contrato_norm', 'Alerta Vigência']], 
            on='contrato_norm', how='left')
        df_por_gestor = df_gestor_contrato.groupby('Gestor(a)').agg({'contrato_norm': 'count',
            'valorGlobal': 'sum', 'Valor Empenhos Total': 'sum', 'Valor Empenhos Pagos': 'sum', 'Valor a Pagar': 'sum', 
            'Alerta Vigência': lambda x: (x.isin(['Vencido', 'Crítico (≤30 dias)', 'Atenção (≤90 dias)'])).sum()}).reset_index()
        df_por_gestor.columns = ['Gestor', 'Qtd Contratos', 'Valor Global', 'Empenhado', 'Pago', 'A Pagar', 'Com Alertas']
        df_por_gestor = df_por_gestor.sort_values('Valor Global', ascending=False)
        df_por_gestor = df_por_gestor.reset_index(drop=True)
        st.dataframe(df_por_gestor, use_container_width=True)
        buffer = io.BytesIO()
        with pd.ExcelWriter(buffer, engine="openpyxl") as writer:
            df_por_gestor.to_excel(writer, index=False, sheet_name="Por Gestor")
        buffer.seek(0)
        st.download_button("⬇️ Baixar Excel", buffer, f"Resumo por gestor{datetime.now().strftime('%Y%m%d')}.xlsx",
                           mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")
    with tab_nucleo_div:
        df_nd_contrato = df_resumo_comprasnet.groupby(['Núcleo_Divisão_Seção', 'contrato_norm']).agg({
            'valorGlobal': 'first',
            'Valor Empenhos Total': lambda x: pd.to_numeric(x, errors='coerce').sum(),
            'Valor Empenhos Pagos': lambda x: pd.to_numeric(x, errors='coerce').sum()}).reset_index()  
        df_nd_contrato['Valor a Pagar'] = (df_nd_contrato['Valor Empenhos Total'] - df_nd_contrato['Valor Empenhos Pagos'])
        df_nd_contrato = df_nd_contrato.merge(df_contratos[['contrato_norm', 'Alerta Vigência']], 
            on='contrato_norm', how='left')
        df_por_nd = df_nd_contrato.groupby('Núcleo_Divisão_Seção').agg({'contrato_norm': 'count',
            'valorGlobal': 'sum', 'Valor Empenhos Total': 'sum', 'Valor Empenhos Pagos': 'sum',
            'Valor a Pagar': 'sum',
            'Alerta Vigência': lambda x: (x.isin(['Vencido', 'Crítico (≤30 dias)', 'Atenção (≤90 dias)'])).sum()}).reset_index()
        df_por_nd.columns = ['Núcleo_Divisão_Seção', 'Qtd Contratos', 'Valor Global', 'Empenhado', 'Pago', 'A Pagar', 'Com Alertas']
        df_por_nd = df_por_nd.sort_values('Valor Global', ascending=False)
        df_por_nd = df_por_nd.reset_index(drop=True)
        st.dataframe(df_por_nd, use_container_width=True)
        buffer = io.BytesIO()
        with pd.ExcelWriter(buffer, engine="openpyxl") as writer:
            df_por_nd.to_excel(writer, index=False, sheet_name="Por Núcleo Divisão Seção")
        buffer.seek(0)
        st.download_button("⬇️ Baixar Excel", buffer, f"Resumo por Núcleo Divisão Seção {datetime.now().strftime('%Y%m%d')}.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")       
    with tab_cc:
        df_cc_contrato = df_resumo_comprasnet.groupby(['Centro de Custo', 'contrato_norm']).agg({
            'valorGlobal': 'first',
            'Valor Empenhos Total': lambda x: pd.to_numeric(x, errors='coerce').sum(),
            'Valor Empenhos Pagos': lambda x: pd.to_numeric(x, errors='coerce').sum()}).reset_index()  
        df_cc_contrato['Valor a Pagar'] = (df_cc_contrato['Valor Empenhos Total'] - df_cc_contrato['Valor Empenhos Pagos'])
        df_cc_contrato = df_cc_contrato.merge(df_contratos[['contrato_norm', 'Alerta Vigência']], 
            on='contrato_norm', how='left')
        df_por_cc = df_cc_contrato.groupby('Centro de Custo').agg({'contrato_norm': 'count',
            'valorGlobal': 'sum', 'Valor Empenhos Total': 'sum', 'Valor Empenhos Pagos': 'sum',
            'Valor a Pagar': 'sum',
            'Alerta Vigência': lambda x: (x.isin(['Vencido', 'Crítico (≤30 dias)', 'Atenção (≤90 dias)'])).sum()}).reset_index()
        df_por_cc.columns = ['Centro de Custo', 'Qtd Contratos', 'Valor Global', 'Empenhado', 'Pago', 'A Pagar', 'Com Alertas']
        df_por_cc = df_por_cc.sort_values('Valor Global', ascending=False)
        df_por_cc = df_por_cc.reset_index(drop=True)
        st.dataframe(df_por_cc, use_container_width=True)
        buffer = io.BytesIO()
        with pd.ExcelWriter(buffer, engine="openpyxl") as writer:
            df_por_cc.to_excel(writer, index=False, sheet_name="Por Centro de Custo")
        buffer.seek(0)
        st.download_button("⬇️ Baixar Excel", buffer, f"Resumo por centro de custo {datetime.now().strftime('%Y%m%d')}.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")

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