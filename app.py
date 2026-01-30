"""
Painel de Gestão Financeira - TRF5
Dashboard profissional para análise orçamentária completa
Versão melhorada com base nos requisitos e prints fornecidos
"""

import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import numpy as np
from datetime import datetime
import warnings
warnings.filterwarnings('ignore')

# =============================================================================
# CONFIGURAÇÃO DA PÁGINA
# =============================================================================
st.set_page_config(
    page_title="Painel Financeiro TRF5",
    page_icon="💰",
    layout="wide",
    initial_sidebar_state="expanded"
)

# =============================================================================
# CSS
# =============================================================================
st.markdown("""
<style>
    .main-header {
        font-size: 2.2rem;
        font-weight: bold;
        color: #1e3a8a;
        text-align: center;
        padding: 1rem 0;
        margin-bottom: 1rem;
    }
    .metric-container {
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        padding: 1.5rem;
        border-radius: 10px;
        color: white;
        text-align: center;
        box-shadow: 0 4px 6px rgba(0,0,0,0.1);
    }
    .metric-value {
        font-size: 1.8rem;
        font-weight: bold;
        margin: 0.5rem 0;
    }
    .metric-label {
        font-size: 0.9rem;
        opacity: 0.9;
    }
    .section-header {
        font-size: 1.5rem;
        font-weight: 600;
        color: #1e3a8a;
        margin: 1.5rem 0 1rem 0;
        border-bottom: 3px solid #3b82f6;
        padding-bottom: 0.5rem;
    }
</style>
""", unsafe_allow_html=True)

# =============================================================================
# HEADER
# =============================================================================
st.markdown('<p class="main-header">🔷 Painel de Gestão Financeira</p>', unsafe_allow_html=True)

# =============================================================================
# LOAD DATA (INLINE)
# =============================================================================
try:
    df_2025 = pd.read_parquet('Dados 2025.parquet')
    df_2026 = pd.read_parquet('Dados 2026.parquet')

    df = pd.concat([df_2025, df_2026], ignore_index=True)

    colunas_numericas = [
        'Limite.de.Gastos', 'Valor.Destaque.Concedido', 'Valor.Pré-Empenhos.a.Empenhar',
        'Valor.Empenhos.Total', 'Valor.Empenhos.Pagos', 'Valor.Limite.Disponível',
        'Valor.RP.Não.Processados.Inscritos', 'Valor.RP.Não.Processados.Reinscritos',
        'Valor.RP.Processados.Inscritos', 'Valor.RP.Processados.Reinscritos',
        'Valor.RP.Não.Processados.Cancelados', 'Valor.RP.Processados.Cancelados',
        'Valor.RP.Não.Processados.Bloqueados', 'Valor.RP.Processados.Pagos'
    ]

    for col in colunas_numericas:
        if col in df.columns:
            # Normaliza valores problemáticos como '-' e strings vazias
            df[col] = df[col].astype(str).str.strip()

            # Trata hífen e outros "não valores"
            df[col] = df[col].replace(
                {
                    "-": "",
                    "nan": "",
                    "None": "",
                    "NaN": "",
                    "": ""
                }
            )

            # Troca separador decimal pt-BR para padrão float
            df[col] = df[col].str.replace(".", "", regex=False)   # remove separador de milhar (se existir)
            df[col] = df[col].str.replace(",", ".", regex=False)  # vírgula vira ponto

            # Converte com tolerância: tudo que não converter vira NaN -> 0
            df[col] = pd.to_numeric(df[col], errors="coerce").fillna(0.0)


    colunas_texto = ['Centro.de.Custo', 'Gestores', 'Órgão', 'Plano.Orçamentário.Nome']
    for col in colunas_texto:
        if col in df.columns:
            df[col] = df[col].fillna('Não informado')

    if 'Ano' in df.columns:
        df['Ano'] = df['Ano'].astype(str)

except Exception as e:
    st.error(f"Erro ao carregar dados: {e}")
    st.stop()

# =============================================================================
# SIDEBAR FILTROS
# =============================================================================
st.sidebar.title("🔍 Filtros")

anos = sorted(df['Ano'].unique()) if 'Ano' in df.columns else []
ano_sel = st.sidebar.multiselect("📅 Ano", anos, default=anos)

gestores = sorted(df['Gestores'].unique()) if 'Gestores' in df.columns else []
gestor_sel = st.sidebar.multiselect("👤 Gestor", gestores)

centros = sorted(df['Centro.de.Custo'].unique()) if 'Centro.de.Custo' in df.columns else []
centro_sel = st.sidebar.multiselect("🏢 Centro de Custos", centros)

orgaos = sorted(df['Órgão'].unique()) if 'Órgão' in df.columns else []
orgao_sel = st.sidebar.multiselect("🏛️ Órgão", orgaos)

df_filtrado = df.copy()

if ano_sel:
    df_filtrado = df_filtrado[df_filtrado['Ano'].isin(ano_sel)]
if gestor_sel:
    df_filtrado = df_filtrado[df_filtrado['Gestores'].isin(gestor_sel)]
if centro_sel:
    df_filtrado = df_filtrado[df_filtrado['Centro.de.Custo'].isin(centro_sel)]
if orgao_sel:
    df_filtrado = df_filtrado[df_filtrado['Órgão'].isin(orgao_sel)]

st.sidebar.success(f"✅ {len(df_filtrado):,} registros filtrados")

# =============================================================================
# ABAS
# =============================================================================
tab1, tab2, tab3, tab4, tab5, tab6 = st.tabs([
    "📊 Visão Geral",
    "💼 Por Gestor",
    "🏢 Por Centro de Custos",
    "📝 Empenhos e Pré-Empenhos",
    "💸 Restos a Pagar",
    "🔍 Detalhamento/Busca"
])

# =============================================================================
# ABA 1 – VISÃO GERAL (EXATAMENTE IGUAL)
# =============================================================================
with tab1:
    limite_gastos=df_filtrado['Limite.de.Gastos'].sum()
    destaques_concedidos=df_filtrado['Valor.Destaque.Concedido'].sum()
    valor_pre_empenhado=df_filtrado['Valor.Pré-Empenhos.a.Empenhar'].sum()
    valor_empenhado=df_filtrado['Valor.Empenhos.Total'].sum()
    valor_pago=df_filtrado['Valor.Empenhos.Pagos'].sum()
    limite_disponivel=df_filtrado['Valor.Limite.Disponível'].sum()-valor_pre_empenhado-valor_empenhado
    valor_a_pagar=valor_empenhado-valor_pago
    rp_inscritos=df_filtrado['Valor.RP.Não.Processados.Inscritos'].sum()+df_filtrado['Valor.RP.Não.Processados.Reinscritos'].sum()+df_filtrado['Valor.RP.Processados.Inscritos'].sum()+df_filtrado['Valor.RP.Processados.Reinscritos'].sum()
    rp_cancelados=df_filtrado['Valor.RP.Não.Processados.Cancelados'].sum()+df_filtrado['Valor.RP.Processados.Cancelados'].sum()
    rp_bloqueados=df_filtrado['Valor.RP.Não.Processados.Bloqueados'].sum()
    rp_pagos=df_filtrado['Valor.RP.Processados.Pagos'].sum()
    rp_a_pagar=rp_inscritos-rp_cancelados-rp_bloqueados-rp_pagos
    st.markdown("## 📊 Visão Geral – KPIs Financeiros")
    col1,col2,col3=st.columns(3)
    col1.metric("💰 Limite de Gastos",f"R$ {limite_gastos:,.2f}".replace(",", "X").replace(".", ",").replace("X", "."))
    col2.metric("🎯 Destaques Concedidos",f"R$ {destaques_concedidos:,.2f}".replace(",", "X").replace(".", ",").replace("X", "."))
    col3.metric("📋 Valor Pré-Empenhado",f"R$ {valor_pre_empenhado:,.2f}".replace(",", "X").replace(".", ",").replace("X", "."))
    col4,col5,col6=st.columns(3)
    col4.metric("📝 Valor Empenhado",f"R$ {valor_empenhado:,.2f}".replace(",", "X").replace(".", ",").replace("X", "."))
    col5.metric("💵 Valor Pago",f"R$ {valor_pago:,.2f}".replace(",", "X").replace(".", ",").replace("X", "."))
    col6.metric("⏳ Valor a Pagar",f"R$ {valor_a_pagar:,.2f}".replace(",", "X").replace(".", ",").replace("X", "."))
    col7,col8=st.columns(2)
    col7.metric("🟢 Limite Disponível",f"R$ {limite_disponivel:,.2f}".replace(",", "X").replace(".", ",").replace("X", "."))
    col8.metric("📦 RP Inscritos",f"R$ {rp_inscritos:,.2f}".replace(",", "X").replace(".", ",").replace("X", "."))
    col9,col10,col11=st.columns(3)
    col9.metric("❌ RP Cancelados",f"R$ {rp_cancelados:,.2f}".replace(",", "X").replace(".", ",").replace("X", "."))
    col10.metric("🚫 RP Bloqueados",f"R$ {rp_bloqueados:,.2f}".replace(",", "X").replace(".", ",").replace("X", "."))
    col11.metric("✅ RP Pagos",f"R$ {rp_pagos:,.2f}".replace(",", "X").replace(".", ",").replace("X", "."))
    st.metric("⏰ RP a Pagar",f"R$ {rp_a_pagar:,.2f}".replace(",", "X").replace(".", ",").replace("X", "."))
    st.dataframe(df_filtrado)
