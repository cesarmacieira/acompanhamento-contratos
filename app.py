"""
Painel de Gestão Financeira - TRF5
Dashboard profissional para análise orçamentária completa
Versão 2.0 - Completa e Otimizada
"""

import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from plotly.subplots import make_subplots
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
    initial_sidebar_state="collapsed"
)

# =============================================================================
# CSS CUSTOMIZADO
# =============================================================================
st.markdown("""
<style>
    /* Esconde o menu do Streamlit */
    #MainMenu {visibility: hidden;}
    footer {visibility: hidden;}
    
    /* Header principal */
    .main-header {
        font-size: 2.5rem;
        font-weight: bold;
        color: #1e3a8a;
        text-align: center;
        padding: 1.5rem 0;
        margin-bottom: 2rem;
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        background-clip: text;
    }
    
    /* Container de métricas */
    .metric-card {
        background: white;
        padding: 1.5rem;
        border-radius: 12px;
        box-shadow: 0 2px 8px rgba(0,0,0,0.1);
        border-left: 4px solid #3b82f6;
        margin-bottom: 1rem;
    }
    
    .metric-value {
        font-size: 1.8rem;
        font-weight: bold;
        color: #1e3a8a;
        margin: 0.5rem 0;
    }
    
    .metric-label {
        font-size: 0.95rem;
        color: #64748b;
        text-transform: uppercase;
        letter-spacing: 0.5px;
    }
    
    .metric-positive {
        color: #10b981;
    }
    
    .metric-negative {
        color: #ef4444;
    }
    
    /* Seção headers */
    .section-header {
        font-size: 1.6rem;
        font-weight: 600;
        color: #1e3a8a;
        margin: 2rem 0 1rem 0;
        border-bottom: 3px solid #3b82f6;
        padding-bottom: 0.5rem;
    }
    
    /* Filtros */
    .filter-container {
        background: #f8fafc;
        padding: 1.5rem;
        border-radius: 12px;
        margin-bottom: 2rem;
        border: 1px solid #e2e8f0;
    }
    
    /* Tabs customizadas */
    .stTabs [data-baseweb="tab-list"] {
        gap: 8px;
        background-color: #f8fafc;
        padding: 0.5rem;
        border-radius: 10px;
    }
    
    .stTabs [data-baseweb="tab"] {
        height: 50px;
        padding: 0 24px;
        background-color: white;
        border-radius: 8px;
        border: 1px solid #e2e8f0;
        font-weight: 500;
    }
    
    .stTabs [aria-selected="true"] {
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        color: white;
        border: none;
    }
    
    /* Tabela customizada */
    .dataframe {
        font-size: 0.9rem;
    }
    
    /* Info boxes */
    .info-box {
        background: #eff6ff;
        border-left: 4px solid #3b82f6;
        padding: 1rem;
        border-radius: 8px;
        margin: 1rem 0;
    }
    
    .warning-box {
        background: #fef3c7;
        border-left: 4px solid #f59e0b;
        padding: 1rem;
        border-radius: 8px;
        margin: 1rem 0;
    }
    
    .success-box {
        background: #d1fae5;
        border-left: 4px solid #10b981;
        padding: 1rem;
        border-radius: 8px;
        margin: 1rem 0;
    }
</style>
""", unsafe_allow_html=True)

# =============================================================================
# FUNÇÕES AUXILIARES
# =============================================================================
def formatar_moeda(valor):
    """Formata valor em Real brasileiro"""
    return f"R$ {valor:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")

def formatar_numero(valor):
    """Formata número com separadores"""
    return f"{valor:,.0f}".replace(",", ".")

def calcular_percentual(parte, total):
    """Calcula percentual com tratamento de divisão por zero"""
    if total == 0:
        return 0
    return (parte / total) * 100

# =============================================================================
# CACHE DE DADOS
# =============================================================================
@st.cache_data
def carregar_dados():
    """Carrega e processa os dados de forma otimizada"""
    try:
        def normaliza_colunas(df):
            df.columns = (
                df.columns
                .str.strip()
                .str.replace(" ", ".", regex=False)
            )
            return df
        # Carrega dados do Excel (você pode adaptar para Parquet quando tiver pyarrow)
        df_2025 = pd.read_parquet("Dados 2025.parquet")
        df_2026 = pd.read_parquet("Dados 2026.parquet")
        df_2025 = normaliza_colunas(df_2025)
        df_2026 = normaliza_colunas(df_2026)

        df = pd.concat([df_2025, df_2026], ignore_index=True)
        colunas_valor = [
            'Valor Limite Disponível',
            'Valor Destaque Concedido',
            'Valor Pré-Empenhos a Empenhar',
            'Valor Empenhos Total',
            'Valor Empenhos Pagos',
            'Valor RP Não Processados Inscritos',
            'Valor RP Não Processados Reinscritos',
            'Valor RP Processados Inscritos',
            'Valor RP Processados Reinscritos',
            'Valor RP Não Processados Cancelados',
            'Valor RP Processados Cancelados',
            'Valor RP Não Processados Bloqueados',
            'Valor RP Processados Pagos'
        ]

        for col in colunas_valor:
            if col in df.columns:
                df[col] = (
                    df[col]
                    .astype(str)
                    .str.replace('R$', '', regex=False)
                    .str.replace('.', '', regex=False)
                    .str.replace(',', '.', regex=False)
                    .str.strip()
                )
                df[col] = pd.to_numeric(df[col], errors='coerce').fillna(0)
        
        # Adiciona ano se não existir
        if 'Ano' not in df.columns:
            df['Ano'] = 2026
        
        # Garante que colunas texto existam
        colunas_texto = ['Centro de Custo', 'Gestores', 'Órgão', 'Plano Orçamentário Nome', 
                        'Favorecido Nome', 'Natureza Despesa Nome', 'Grupo Despesa Nome']
        for col in colunas_texto:
            if col in df.columns:
                df[col] = df[col].fillna('Não informado')
        
        # Converte data de emissão se existir
        if 'Data Emissão' in df.columns:
            df['Data Emissão'] = pd.to_datetime(df['Data Emissão'], errors='coerce')
            df['Mês Emissão'] = df['Data Emissão'].dt.month
            df['Trimestre'] = df['Data Emissão'].dt.quarter
        
        return df
    
    except Exception as e:
        st.error(f"Erro ao carregar dados: {e}")
        st.stop()

# =============================================================================
# CARREGAMENTO DOS DADOS
# =============================================================================
df = carregar_dados()

# =============================================================================
# HEADER
# =============================================================================
st.markdown('<p class="main-header">📊 Painel de Gestão Financeira - TRF5</p>', unsafe_allow_html=True)

# =============================================================================
# FILTROS PRINCIPAIS (TOPO)
# =============================================================================
st.markdown('<div class="filter-container">', unsafe_allow_html=True)
st.markdown("### 🔍 Filtros de Análise")

col_f1, col_f2, col_f3, col_f4 = st.columns(4)

with col_f1:
    anos = sorted(df['Ano'].unique()) if 'Ano' in df.columns else []
    ano_sel = st.multiselect("📅 Ano", anos, default=anos, key="filtro_ano")

with col_f2:
    gestores = sorted(df['Gestores'].unique()) if 'Gestores' in df.columns else []
    gestor_sel = st.multiselect("👤 Gestor", gestores, key="filtro_gestor")

with col_f3:
    centros = sorted(df['Centro de Custo'].unique()) if 'Centro de Custo' in df.columns else []
    centro_sel = st.multiselect("🏢 Centro de Custos", centros, key="filtro_centro")

with col_f4:
    orgaos = sorted(df['Órgão'].unique()) if 'Órgão' in df.columns else []
    orgao_sel = st.multiselect("🏛️ Órgão", orgaos, key="filtro_orgao")

# Aplicar filtros
df_filtrado = df.copy()

if ano_sel:
    df_filtrado = df_filtrado[df_filtrado['Ano'].isin(ano_sel)]
if gestor_sel:
    df_filtrado = df_filtrado[df_filtrado['Gestores'].isin(gestor_sel)]
if centro_sel:
    df_filtrado = df_filtrado[df_filtrado['Centro de Custo'].isin(centro_sel)]
if orgao_sel:
    df_filtrado = df_filtrado[df_filtrado['Órgão'].isin(orgao_sel)]

# Info de registros filtrados
st.markdown(f'<div class="success-box">✅ <strong>{len(df_filtrado):,}</strong> registros selecionados de <strong>{len(df):,}</strong> totais</div>'.replace(",", "."), unsafe_allow_html=True)
st.markdown('</div>', unsafe_allow_html=True)

# =============================================================================
# CÁLCULO DOS KPIs
# =============================================================================
# KPIs Financeiros Principais
limite_gastos = df_filtrado['Valor.Limite.Disponível'].sum()
destaques_concedidos = df_filtrado['Valor Destaque Concedido'].sum()
valor_pre_empenhado = df_filtrado['Valor Pré-Empenhos a Empenhar'].sum()
valor_empenhado = df_filtrado['Valor Empenhos Total'].sum()
valor_pago = df_filtrado['Valor Empenhos Pagos'].sum()
limite_disponivel = limite_gastos - valor_pre_empenhado - valor_empenhado
valor_a_pagar = valor_empenhado - valor_pago

# Restos a Pagar
rp_np_inscritos = df_filtrado['Valor RP Não Processados Inscritos'].sum()
rp_np_reinscritos = df_filtrado['Valor RP Não Processados Reinscritos'].sum()
rp_p_inscritos = df_filtrado['Valor RP Processados Inscritos'].sum()
rp_p_reinscritos = df_filtrado['Valor RP Processados Reinscritos'].sum()
rp_inscritos = rp_np_inscritos + rp_np_reinscritos + rp_p_inscritos + rp_p_reinscritos

rp_np_cancelados = df_filtrado['Valor RP Não Processados Cancelados'].sum()
rp_p_cancelados = df_filtrado['Valor RP Processados Cancelados'].sum()
rp_cancelados = rp_np_cancelados + rp_p_cancelados

rp_bloqueados = df_filtrado['Valor RP Não Processados Bloqueados'].sum()
rp_pagos = df_filtrado['Valor RP Processados Pagos'].sum()
rp_a_pagar = rp_inscritos - rp_cancelados - rp_bloqueados - rp_pagos

# =============================================================================
# ABAS
# =============================================================================
tab1, tab2, tab3, tab4, tab5, tab6, tab7 = st.tabs([
    "📊 Visão Geral",
    "💼 Por Gestor",
    "🏢 Por Centro de Custos",
    "📝 Empenhos e Pré-Empenhos",
    "💸 Restos a Pagar",
    "📈 Análises Avançadas",
    "🔍 Detalhamento/Busca"
])

# =============================================================================
# ABA 1 — VISÃO GERAL
# =============================================================================
with tab1:
    st.markdown("## 📊 Visão Geral — KPIs Financeiros")
    
    # Primeira linha de KPIs
    col1, col2, col3 = st.columns(3)
    
    with col1:
        st.metric(
            "💰 Limite de Gastos",
            formatar_moeda(limite_gastos),
            help="Valor total do limite disponível"
        )
    
    with col2:
        st.metric(
            "🎯 Destaques Concedidos",
            formatar_moeda(destaques_concedidos),
            help="Soma dos valores de destaque concedidos"
        )
    
    with col3:
        perc_pe = calcular_percentual(valor_pre_empenhado, limite_gastos)
        st.metric(
            "📋 Valor Pré-Empenhado",
            formatar_moeda(valor_pre_empenhado),
            f"{perc_pe:.1f}% do limite",
            help="Soma dos pré-empenhos a empenhar"
        )
    
    # Segunda linha de KPIs
    col4, col5, col6 = st.columns(3)
    
    with col4:
        perc_emp = calcular_percentual(valor_empenhado, limite_gastos)
        st.metric(
            "📝 Valor Empenhado",
            formatar_moeda(valor_empenhado),
            f"{perc_emp:.1f}% do limite",
            help="Soma total dos empenhos"
        )
    
    with col5:
        perc_pago = calcular_percentual(valor_pago, valor_empenhado)
        st.metric(
            "💵 Valor Pago",
            formatar_moeda(valor_pago),
            f"{perc_pago:.1f}% do empenhado",
            help="Soma dos valores pagos"
        )
    
    with col6:
        st.metric(
            "⏳ Valor a Pagar",
            formatar_moeda(valor_a_pagar),
            help="Diferença entre empenhado e pago"
        )
    
    # Terceira linha de KPIs
    col7, col8 = st.columns(2)
    
    with col7:
        perc_disp = calcular_percentual(limite_disponivel, limite_gastos)
        delta_color = "normal" if limite_disponivel > 0 else "inverse"
        st.metric(
            "🟢 Limite Disponível",
            formatar_moeda(limite_disponivel),
            f"{perc_disp:.1f}% do total",
            help="Limite - Pré-Empenhos - Empenhos"
        )
    
    with col8:
        st.metric(
            "📦 RP Inscritos",
            formatar_moeda(rp_inscritos),
            help="Total de Restos a Pagar inscritos"
        )
    
    # Quarta linha - RP
    col9, col10, col11, col12 = st.columns(4)
    
    with col9:
        st.metric(
            "❌ RP Cancelados",
            formatar_moeda(rp_cancelados),
            help="Restos a Pagar cancelados"
        )
    
    with col10:
        st.metric(
            "🚫 RP Bloqueados",
            formatar_moeda(rp_bloqueados),
            help="Restos a Pagar bloqueados"
        )
    
    with col11:
        st.metric(
            "✅ RP Pagos",
            formatar_moeda(rp_pagos),
            help="Restos a Pagar já pagos"
        )
    
    with col12:
        st.metric(
            "⏰ RP a Pagar",
            formatar_moeda(rp_a_pagar),
            help="Saldo de RP a pagar"
        )
    
    # Gráfico de execução orçamentária
    st.markdown("---")
    st.markdown("### 📊 Execução Orçamentária")
    
    col_g1, col_g2 = st.columns(2)
    
    with col_g1:
        # Gráfico de pizza - Composição do Limite
        fig_composicao = go.Figure(data=[go.Pie(
            labels=['Pré-Empenhado', 'Empenhado', 'Disponível'],
            values=[valor_pre_empenhado, valor_empenhado, max(0, limite_disponivel)],
            hole=0.4,
            marker=dict(colors=['#fbbf24', '#3b82f6', '#10b981']),
            textinfo='label+percent',
            textposition='outside'
        )])
        fig_composicao.update_layout(
            title="Composição do Limite de Gastos",
            height=400,
            showlegend=True
        )
        st.plotly_chart(fig_composicao, use_container_width=True)
    
    with col_g2:
        # Gráfico de barras - Execução
        fig_exec = go.Figure()
        fig_exec.add_trace(go.Bar(
            name='Empenhado',
            x=['Execução'],
            y=[valor_empenhado],
            marker_color='#3b82f6',
            text=[formatar_moeda(valor_empenhado)],
            textposition='auto'
        ))
        fig_exec.add_trace(go.Bar(
            name='Pago',
            x=['Execução'],
            y=[valor_pago],
            marker_color='#10b981',
            text=[formatar_moeda(valor_pago)],
            textposition='auto'
        ))
        fig_exec.add_trace(go.Bar(
            name='A Pagar',
            x=['Execução'],
            y=[valor_a_pagar],
            marker_color='#f59e0b',
            text=[formatar_moeda(valor_a_pagar)],
            textposition='auto'
        ))
        fig_exec.update_layout(
            title="Situação de Pagamento",
            barmode='stack',
            height=400,
            showlegend=True,
            yaxis_title="Valor (R$)"
        )
        st.plotly_chart(fig_exec, use_container_width=True)
    
    # Tabela resumo
    st.markdown("---")
    st.markdown("### 📋 Dados Detalhados (Primeiros 100 registros)")
    
    # Seleciona colunas mais relevantes para exibição
    colunas_exibir = [
        'Data Emissão', 'Favorecido Nome', 'Natureza Despesa Nome',
        'Valor Empenhos Total', 'Valor Empenhos Pagos', 'Valor Pré-Empenhos a Empenhar',
        'Centro de Custo', 'Gestores'
    ]
    
    # Filtra apenas colunas que existem
    colunas_exibir = [col for col in colunas_exibir if col in df_filtrado.columns]
    
    df_display = df_filtrado[colunas_exibir].head(100).copy()
    
    # Formata valores monetários
    for col in df_display.columns:
        if 'Valor' in col:
            df_display[col] = df_display[col].apply(lambda x: formatar_moeda(x) if pd.notna(x) else 'R$ 0,00')
    
    st.dataframe(df_display, use_container_width=True, height=400)

# =============================================================================
# ABA 2 — POR GESTOR
# =============================================================================
with tab2:
    st.markdown("## 💼 Análise por Gestor")
    
    if 'Gestores' in df_filtrado.columns:
        # Agrupa por gestor
        df_gestor = df_filtrado.groupby('Gestores').agg({
            'Nota Empenho': 'count',
            'Valor Empenhos Total': 'sum',
            'Valor Empenhos Pagos': 'sum',
            'Valor Pré-Empenhos a Empenhar': 'sum',
            'Valor Limite Disponível': 'sum'
        }).reset_index()
        
        df_gestor.columns = ['Gestor', 'Qtd Empenhos', 'Valor Empenhado', 
                            'Valor Pago', 'Valor Pré-Empenhado', 'Limite Disponível']
        
        df_gestor['Valor a Pagar'] = df_gestor['Valor Empenhado'] - df_gestor['Valor Pago']
        df_gestor['% Execução'] = (df_gestor['Valor Empenhado'] / df_gestor['Limite Disponível'] * 100).round(2)
        
        # Ordena por valor empenhado
        df_gestor = df_gestor.sort_values('Valor Empenhado', ascending=False)
        
        # KPIs por gestor
        col1, col2, col3 = st.columns(3)
        
        with col1:
            st.metric("👥 Total de Gestores", len(df_gestor))
        
        with col2:
            st.metric("📝 Total de Empenhos", formatar_numero(df_gestor['Qtd Empenhos'].sum()))
        
        with col3:
            media_gestor = df_gestor['Valor Empenhado'].mean()
            st.metric("💰 Média por Gestor", formatar_moeda(media_gestor))
        
        # Gráficos
        col_g1, col_g2 = st.columns(2)
        
        with col_g1:
            # Top 10 gestores por valor empenhado
            top10 = df_gestor.head(10)
            fig_gestor = px.bar(
                top10,
                x='Valor Empenhado',
                y='Gestor',
                orientation='h',
                title='Top 10 Gestores por Valor Empenhado',
                labels={'Valor Empenhado': 'Valor (R$)'},
                color='Valor Empenhado',
                color_continuous_scale='Blues'
            )
            fig_gestor.update_layout(height=500, showlegend=False)
            st.plotly_chart(fig_gestor, use_container_width=True)
        
        with col_g2:
            # Quantidade de empenhos por gestor
            fig_qtd = px.bar(
                top10,
                x='Qtd Empenhos',
                y='Gestor',
                orientation='h',
                title='Top 10 Gestores por Quantidade de Empenhos',
                labels={'Qtd Empenhos': 'Quantidade'},
                color='Qtd Empenhos',
                color_continuous_scale='Greens'
            )
            fig_qtd.update_layout(height=500, showlegend=False)
            st.plotly_chart(fig_qtd, use_container_width=True)
        
        # Tabela detalhada
        st.markdown("### 📊 Tabela Completa por Gestor")
        
        # Formata a tabela para exibição
        df_gestor_display = df_gestor.copy()
        for col in ['Valor Empenhado', 'Valor Pago', 'Valor Pré-Empenhado', 'Limite Disponível', 'Valor a Pagar']:
            df_gestor_display[col] = df_gestor_display[col].apply(formatar_moeda)
        
        df_gestor_display['Qtd Empenhos'] = df_gestor_display['Qtd Empenhos'].apply(lambda x: f"{x:,.0f}".replace(",", "."))
        
        st.dataframe(df_gestor_display, use_container_width=True, height=400)
        
        # Download
        csv = df_gestor.to_csv(index=False).encode('utf-8-sig')
        st.download_button(
            label="📥 Download CSV - Análise por Gestor",
            data=csv,
            file_name=f'analise_gestores_{datetime.now().strftime("%Y%m%d")}.csv',
            mime='text/csv'
        )
    else:
        st.warning("Coluna 'Gestores' não encontrada nos dados.")

# =============================================================================
# ABA 3 — POR CENTRO DE CUSTOS
# =============================================================================
with tab3:
    st.markdown("## 🏢 Análise por Centro de Custos")
    
    if 'Centro de Custo' in df_filtrado.columns:
        # Agrupa por centro de custo
        df_centro = df_filtrado.groupby('Centro de Custo').agg({
            'Nota Empenho': 'count',
            'Valor Empenhos Total': 'sum',
            'Valor Empenhos Pagos': 'sum',
            'Valor Pré-Empenhos a Empenhar': 'sum',
            'Valor Limite Disponível': 'sum',
            'Valor RP Não Processados Inscritos': 'sum',
            'Valor RP Processados Inscritos': 'sum'
        }).reset_index()
        
        df_centro.columns = ['Centro de Custo', 'Qtd Empenhos', 'Valor Empenhado', 
                            'Valor Pago', 'Valor Pré-Empenhado', 'Limite Disponível',
                            'RP Não Processados', 'RP Processados']
        
        df_centro['Valor a Pagar'] = df_centro['Valor Empenhado'] - df_centro['Valor Pago']
        df_centro['Total RP'] = df_centro['RP Não Processados'] + df_centro['RP Processados']
        df_centro['% Execução'] = (df_centro['Valor Empenhado'] / df_centro['Limite Disponível'] * 100).round(2)
        
        # Ordena por valor empenhado
        df_centro = df_centro.sort_values('Valor Empenhado', ascending=False)
        
        # KPIs
        col1, col2, col3, col4 = st.columns(4)
        
        with col1:
            st.metric("🏢 Centros de Custo", len(df_centro))
        
        with col2:
            st.metric("📝 Total Empenhos", formatar_numero(df_centro['Qtd Empenhos'].sum()))
        
        with col3:
            st.metric("💰 Total Empenhado", formatar_moeda(df_centro['Valor Empenhado'].sum()))
        
        with col4:
            st.metric("📦 Total RP", formatar_moeda(df_centro['Total RP'].sum()))
        
        # Gráficos
        col_g1, col_g2 = st.columns(2)
        
        with col_g1:
            # Top centros por valor
            top_centros = df_centro.head(15)
            fig_centro = px.treemap(
                top_centros,
                path=['Centro de Custo'],
                values='Valor Empenhado',
                title='Distribuição de Valores por Centro de Custo (Top 15)',
                color='Valor Empenhado',
                color_continuous_scale='RdYlGn_r'
            )
            fig_centro.update_layout(height=500)
            st.plotly_chart(fig_centro, use_container_width=True)
        
        with col_g2:
            # Execução vs Pagamento
            fig_exec_centro = go.Figure()
            top_exec = df_centro.head(10)
            
            fig_exec_centro.add_trace(go.Bar(
                name='Empenhado',
                x=top_exec['Centro de Custo'],
                y=top_exec['Valor Empenhado'],
                marker_color='#3b82f6'
            ))
            fig_exec_centro.add_trace(go.Bar(
                name='Pago',
                x=top_exec['Centro de Custo'],
                y=top_exec['Valor Pago'],
                marker_color='#10b981'
            ))
            
            fig_exec_centro.update_layout(
                title='Top 10 - Empenhado vs Pago',
                barmode='group',
                height=500,
                xaxis_tickangle=-45
            )
            st.plotly_chart(fig_exec_centro, use_container_width=True)
        
        # Tabela detalhada
        st.markdown("### 📊 Tabela Completa por Centro de Custo")
        
        df_centro_display = df_centro.copy()
        colunas_monetarias = ['Valor Empenhado', 'Valor Pago', 'Valor Pré-Empenhado', 
                             'Limite Disponível', 'Valor a Pagar', 'RP Não Processados', 
                             'RP Processados', 'Total RP']
        
        for col in colunas_monetarias:
            df_centro_display[col] = df_centro_display[col].apply(formatar_moeda)
        
        df_centro_display['Qtd Empenhos'] = df_centro_display['Qtd Empenhos'].apply(lambda x: f"{x:,.0f}".replace(",", "."))
        
        st.dataframe(df_centro_display, use_container_width=True, height=400)
        
        # Download
        csv = df_centro.to_csv(index=False).encode('utf-8-sig')
        st.download_button(
            label="📥 Download CSV - Análise por Centro de Custo",
            data=csv,
            file_name=f'analise_centros_{datetime.now().strftime("%Y%m%d")}.csv',
            mime='text/csv'
        )
    else:
        st.warning("Coluna 'Centro de Custo' não encontrada nos dados.")

# =============================================================================
# ABA 4 — EMPENHOS E PRÉ-EMPENHOS
# =============================================================================
with tab4:
    st.markdown("## 📝 Análise de Empenhos e Pré-Empenhos")
    
    # KPIs de empenhos
    col1, col2, col3, col4 = st.columns(4)
    
    total_empenhos = len(df_filtrado[df_filtrado['Valor Empenhos Total'] > 0])
    total_pre_empenhos = len(df_filtrado[df_filtrado['Valor Pré-Empenhos a Empenhar'] > 0])
    ticket_medio_emp = df_filtrado[df_filtrado['Valor Empenhos Total'] > 0]['Valor Empenhos Total'].mean()
    ticket_medio_pe = df_filtrado[df_filtrado['Valor Pré-Empenhos a Empenhar'] > 0]['Valor Pré-Empenhos a Empenhar'].mean()
    
    with col1:
        st.metric("📝 Total de Empenhos", formatar_numero(total_empenhos))
    
    with col2:
        st.metric("📋 Total de Pré-Empenhos", formatar_numero(total_pre_empenhos))
    
    with col3:
        st.metric("💰 Ticket Médio Empenho", formatar_moeda(ticket_medio_emp))
    
    with col4:
        st.metric("💵 Ticket Médio Pré-Empenho", formatar_moeda(ticket_medio_pe))
    
    # Análise por Natureza de Despesa
    st.markdown("### 📊 Análise por Natureza de Despesa")
    
    if 'Natureza Despesa Nome' in df_filtrado.columns:
        df_natureza = df_filtrado.groupby('Natureza Despesa Nome').agg({
            'Valor Empenhos Total': 'sum',
            'Valor Pré-Empenhos a Empenhar': 'sum',
            'Nota Empenho': 'count'
        }).reset_index()
        
        df_natureza.columns = ['Natureza', 'Valor Empenhado', 'Valor Pré-Empenhado', 'Qtd']
        df_natureza = df_natureza.sort_values('Valor Empenhado', ascending=False).head(20)
        
        col_g1, col_g2 = st.columns(2)
        
        with col_g1:
            fig_nat_emp = px.bar(
                df_natureza.head(10),
                x='Valor Empenhado',
                y='Natureza',
                orientation='h',
                title='Top 10 Naturezas - Valor Empenhado',
                color='Valor Empenhado',
                color_continuous_scale='Blues'
            )
            fig_nat_emp.update_layout(height=500, showlegend=False)
            st.plotly_chart(fig_nat_emp, use_container_width=True)
        
        with col_g2:
            fig_nat_pe = px.bar(
                df_natureza.head(10),
                x='Valor Pré-Empenhado',
                y='Natureza',
                orientation='h',
                title='Top 10 Naturezas - Valor Pré-Empenhado',
                color='Valor Pré-Empenhado',
                color_continuous_scale='Greens'
            )
            fig_nat_pe.update_layout(height=500, showlegend=False)
            st.plotly_chart(fig_nat_pe, use_container_width=True)
    
    # Análise temporal (se houver data)
    if 'Data Emissão' in df_filtrado.columns:
        st.markdown("### 📅 Evolução Temporal de Empenhos")
        
        df_temp = df_filtrado[df_filtrado['Data Emissão'].notna()].copy()
        df_temp['Mês'] = df_temp['Data Emissão'].dt.to_period('M').astype(str)
        
        df_mensal = df_temp.groupby('Mês').agg({
            'Valor Empenhos Total': 'sum',
            'Nota Empenho': 'count'
        }).reset_index()
        
        df_mensal.columns = ['Mês', 'Valor', 'Quantidade']
        
        fig_temp = make_subplots(
            rows=2, cols=1,
            subplot_titles=('Valor Empenhado por Mês', 'Quantidade de Empenhos por Mês'),
            vertical_spacing=0.15
        )
        
        fig_temp.add_trace(
            go.Bar(x=df_mensal['Mês'], y=df_mensal['Valor'], name='Valor', marker_color='#3b82f6'),
            row=1, col=1
        )
        
        fig_temp.add_trace(
            go.Bar(x=df_mensal['Mês'], y=df_mensal['Quantidade'], name='Quantidade', marker_color='#10b981'),
            row=2, col=1
        )
        
        fig_temp.update_layout(height=600, showlegend=False)
        fig_temp.update_xaxes(title_text="Mês", row=2, col=1)
        fig_temp.update_yaxes(title_text="Valor (R$)", row=1, col=1)
        fig_temp.update_yaxes(title_text="Quantidade", row=2, col=1)
        
        st.plotly_chart(fig_temp, use_container_width=True)
    
    # Top fornecedores
    if 'Favorecido Nome' in df_filtrado.columns:
        st.markdown("### 🏪 Top Fornecedores")
        
        df_fornec = df_filtrado.groupby('Favorecido Nome').agg({
            'Valor Empenhos Total': 'sum',
            'Nota Empenho': 'count'
        }).reset_index()
        
        df_fornec.columns = ['Fornecedor', 'Valor Total', 'Qtd Empenhos']
        df_fornec = df_fornec.sort_values('Valor Total', ascending=False).head(15)
        
        fig_fornec = px.bar(
            df_fornec,
            x='Valor Total',
            y='Fornecedor',
            orientation='h',
            title='Top 15 Fornecedores por Valor',
            color='Qtd Empenhos',
            color_continuous_scale='Viridis',
            labels={'Valor Total': 'Valor (R$)', 'Qtd Empenhos': 'Quantidade'}
        )
        fig_fornec.update_layout(height=600)
        st.plotly_chart(fig_fornec, use_container_width=True)

# =============================================================================
# ABA 5 — RESTOS A PAGAR
# =============================================================================
with tab5:
    st.markdown("## 💸 Análise de Restos a Pagar")
    
    # KPIs de RP
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        st.metric("📦 RP Inscritos", formatar_moeda(rp_inscritos))
    
    with col2:
        st.metric("✅ RP Pagos", formatar_moeda(rp_pagos))
    
    with col3:
        st.metric("❌ RP Cancelados", formatar_moeda(rp_cancelados))
    
    with col4:
        st.metric("🚫 RP Bloqueados", formatar_moeda(rp_bloqueados))
    
    st.markdown("---")
    
    col5, col6 = st.columns(2)
    
    with col5:
        st.metric("⏰ RP a Pagar", formatar_moeda(rp_a_pagar))
    
    with col6:
        perc_pago_rp = calcular_percentual(rp_pagos, rp_inscritos)
        st.metric("📊 % Executado de RP", f"{perc_pago_rp:.1f}%")
    
    # Gráficos
    col_g1, col_g2 = st.columns(2)
    
    with col_g1:
        # Composição de RP
        labels_rp = ['Pagos', 'A Pagar', 'Cancelados', 'Bloqueados']
        values_rp = [rp_pagos, max(0, rp_a_pagar), rp_cancelados, rp_bloqueados]
        
        fig_rp_comp = go.Figure(data=[go.Pie(
            labels=labels_rp,
            values=values_rp,
            hole=0.4,
            marker=dict(colors=['#10b981', '#f59e0b', '#ef4444', '#6b7280']),
            textinfo='label+percent',
            textposition='outside'
        )])
        fig_rp_comp.update_layout(
            title="Composição dos Restos a Pagar",
            height=400
        )
        st.plotly_chart(fig_rp_comp, use_container_width=True)
    
    with col_g2:
        # RP Processados vs Não Processados
        fig_rp_tipo = go.Figure()
        
        categorias = ['Inscritos', 'Reinscritos']
        np_vals = [rp_np_inscritos, rp_np_reinscritos]
        p_vals = [rp_p_inscritos, rp_p_reinscritos]
        
        fig_rp_tipo.add_trace(go.Bar(
            name='Não Processados',
            x=categorias,
            y=np_vals,
            marker_color='#f59e0b'
        ))
        fig_rp_tipo.add_trace(go.Bar(
            name='Processados',
            x=categorias,
            y=p_vals,
            marker_color='#3b82f6'
        ))
        
        fig_rp_tipo.update_layout(
            title="RP Processados vs Não Processados",
            barmode='group',
            height=400,
            yaxis_title="Valor (R$)"
        )
        st.plotly_chart(fig_rp_tipo, use_container_width=True)
    
    # Análise por Gestor
    if 'Gestores' in df_filtrado.columns:
        st.markdown("### 📊 RP por Gestor")
        
        df_rp_gestor = df_filtrado.groupby('Gestores').agg({
            'Valor RP Não Processados Inscritos': 'sum',
            'Valor RP Processados Inscritos': 'sum',
            'Valor RP Processados Pagos': 'sum',
            'Valor RP Não Processados Cancelados': 'sum',
            'Valor RP Processados Cancelados': 'sum'
        }).reset_index()
        
        df_rp_gestor['Total Inscritos'] = (df_rp_gestor['Valor RP Não Processados Inscritos'] + 
                                           df_rp_gestor['Valor RP Processados Inscritos'])
        df_rp_gestor['Total Cancelados'] = (df_rp_gestor['Valor RP Não Processados Cancelados'] + 
                                            df_rp_gestor['Valor RP Processados Cancelados'])
        
        df_rp_gestor = df_rp_gestor.sort_values('Total Inscritos', ascending=False).head(10)
        
        fig_rp_gestor = go.Figure()
        fig_rp_gestor.add_trace(go.Bar(
            name='Inscritos',
            x=df_rp_gestor['Gestores'],
            y=df_rp_gestor['Total Inscritos'],
            marker_color='#3b82f6'
        ))
        fig_rp_gestor.add_trace(go.Bar(
            name='Pagos',
            x=df_rp_gestor['Gestores'],
            y=df_rp_gestor['Valor RP Processados Pagos'],
            marker_color='#10b981'
        ))
        fig_rp_gestor.add_trace(go.Bar(
            name='Cancelados',
            x=df_rp_gestor['Gestores'],
            y=df_rp_gestor['Total Cancelados'],
            marker_color='#ef4444'
        ))
        
        fig_rp_gestor.update_layout(
            title="Top 10 Gestores - RP Inscritos, Pagos e Cancelados",
            barmode='group',
            height=500,
            xaxis_tickangle=-45,
            yaxis_title="Valor (R$)"
        )
        st.plotly_chart(fig_rp_gestor, use_container_width=True)

# =============================================================================
# ABA 6 — ANÁLISES AVANÇADAS
# =============================================================================
with tab6:
    st.markdown("## 📈 Análises Avançadas")
    
    # Análise de concentração
    st.markdown("### 🎯 Análise de Concentração")
    
    col1, col2 = st.columns(2)
    
    with col1:
        # Curva ABC de Fornecedores
        if 'Favorecido Nome' in df_filtrado.columns:
            df_abc = df_filtrado.groupby('Favorecido Nome')['Valor Empenhos Total'].sum().reset_index()
            df_abc = df_abc.sort_values('Valor Empenhos Total', ascending=False)
            df_abc['% Acumulado'] = (df_abc['Valor Empenhos Total'].cumsum() / df_abc['Valor Empenhos Total'].sum() * 100)
            df_abc['Ranking'] = range(1, len(df_abc) + 1)
            
            fig_abc = px.line(
                df_abc.head(50),
                x='Ranking',
                y='% Acumulado',
                title='Curva ABC - Fornecedores (Top 50)',
                labels={'Ranking': 'Ranking do Fornecedor', '% Acumulado': '% Acumulado do Valor'}
            )
            fig_abc.add_hline(y=80, line_dash="dash", line_color="red", 
                             annotation_text="80% (Classe A)")
            fig_abc.add_hline(y=95, line_dash="dash", line_color="orange", 
                             annotation_text="95% (Classe B)")
            fig_abc.update_layout(height=400)
            st.plotly_chart(fig_abc, use_container_width=True)
    
    with col2:
        # Distribuição de valores
        if 'Valor Empenhos Total' in df_filtrado.columns:
            df_valores = df_filtrado[df_filtrado['Valor Empenhos Total'] > 0]['Valor Empenhos Total']
            
            fig_dist = go.Figure()
            fig_dist.add_trace(go.Histogram(
                x=df_valores,
                nbinsx=50,
                marker_color='#3b82f6',
                name='Distribuição'
            ))
            fig_dist.update_layout(
                title='Distribuição de Valores de Empenhos',
                xaxis_title='Valor (R$)',
                yaxis_title='Frequência',
                height=400,
                showlegend=False
            )
            st.plotly_chart(fig_dist, use_container_width=True)
    
    # Análise de eficiência de pagamento
    st.markdown("### ⚡ Eficiência de Pagamento")
    
    if 'Gestores' in df_filtrado.columns:
        df_efic = df_filtrado.groupby('Gestores').agg({
            'Valor Empenhos Total': 'sum',
            'Valor Empenhos Pagos': 'sum'
        }).reset_index()
        
        df_efic['% Pago'] = (df_efic['Valor Empenhos Pagos'] / df_efic['Valor Empenhos Total'] * 100).round(2)
        df_efic = df_efic.sort_values('% Pago', ascending=False).head(15)
        
        fig_efic = px.bar(
            df_efic,
            x='% Pago',
            y='Gestores',
            orientation='h',
            title='Eficiência de Pagamento por Gestor (% Empenhado que foi Pago)',
            color='% Pago',
            color_continuous_scale='RdYlGn',
            labels={'% Pago': '% Pago do Empenhado'}
        )
        fig_efic.update_layout(height=500)
        st.plotly_chart(fig_efic, use_container_width=True)
    
    # Matriz de correlação (se houver dados suficientes)
    st.markdown("### 🔗 Indicadores Consolidados")
    
    indicadores = {
        'Indicador': [
            'Taxa de Execução Orçamentária',
            'Taxa de Pagamento',
            'Taxa de Pré-Empenho',
            'Taxa de RP Pagos',
            'Comprometimento do Limite'
        ],
        'Valor': [
            f"{calcular_percentual(valor_empenhado, limite_gastos):.2f}%",
            f"{calcular_percentual(valor_pago, valor_empenhado):.2f}%",
            f"{calcular_percentual(valor_pre_empenhado, limite_gastos):.2f}%",
            f"{calcular_percentual(rp_pagos, rp_inscritos):.2f}%",
            f"{calcular_percentual(valor_empenhado + valor_pre_empenhado, limite_gastos):.2f}%"
        ],
        'Status': ['✅', '✅', '⚠️', '✅', '⚠️']
    }
    
    df_indicadores = pd.DataFrame(indicadores)
    st.table(df_indicadores)

# =============================================================================
# ABA 7 — DETALHAMENTO/BUSCA
# =============================================================================
with tab7:
    st.markdown("## 🔍 Detalhamento e Busca")
    
    # Busca avançada
    st.markdown("### 🔎 Busca Avançada")
    
    col_b1, col_b2, col_b3 = st.columns(3)
    
    with col_b1:
        if 'Favorecido Nome' in df_filtrado.columns:
            fornecedor_busca = st.text_input("🏪 Buscar Fornecedor", "")
    
    with col_b2:
        if 'Nota Empenho' in df_filtrado.columns:
            nota_busca = st.text_input("📝 Buscar Nota de Empenho", "")
    
    with col_b3:
        valor_min = st.number_input("💰 Valor Mínimo (R$)", min_value=0.0, value=0.0, step=1000.0)
    
    # Aplica filtros de busca
    df_busca = df_filtrado.copy()
    
    if 'Favorecido Nome' in df_busca.columns and fornecedor_busca:
        df_busca = df_busca[df_busca['Favorecido Nome'].str.contains(fornecedor_busca, case=False, na=False)]
    
    if 'Nota Empenho' in df_busca.columns and nota_busca:
        df_busca = df_busca[df_busca['Nota Empenho'].astype(str).str.contains(nota_busca, na=False)]
    
    if 'Valor Empenhos Total' in df_busca.columns and valor_min > 0:
        df_busca = df_busca[df_busca['Valor Empenhos Total'] >= valor_min]
    
    st.markdown(f"**{len(df_busca)}** registros encontrados")
    
    # Seleciona colunas para exibição
    if len(df_busca) > 0:
        colunas_detalhe = [
            'Data Emissão', 'Nota Empenho', 'Favorecido Nome', 'Natureza Despesa Nome',
            'Valor Empenhos Total', 'Valor Empenhos Pagos', 'Valor Pré-Empenhos a Empenhar',
            'Centro de Custo', 'Gestores', 'Órgão'
        ]
        
        colunas_detalhe = [col for col in colunas_detalhe if col in df_busca.columns]
        
        df_display_busca = df_busca[colunas_detalhe].copy()
        
        # Formata valores
        for col in df_display_busca.columns:
            if 'Valor' in col:
                df_display_busca[col] = df_display_busca[col].apply(
                    lambda x: formatar_moeda(x) if pd.notna(x) else 'R$ 0,00'
                )
        
        st.dataframe(df_display_busca, use_container_width=True, height=500)
        
        # Download dos resultados
        csv_busca = df_busca.to_csv(index=False).encode('utf-8-sig')
        st.download_button(
            label="📥 Download CSV - Resultados da Busca",
            data=csv_busca,
            file_name=f'busca_detalhada_{datetime.now().strftime("%Y%m%d_%H%M%S")}.csv',
            mime='text/csv'
        )
    
    # Estatísticas do dataset completo
    st.markdown("---")
    st.markdown("### 📊 Estatísticas do Dataset")
    
    col_e1, col_e2, col_e3, col_e4 = st.columns(4)
    
    with col_e1:
        st.metric("📁 Total de Registros", formatar_numero(len(df_filtrado)))
    
    with col_e2:
        st.metric("📋 Colunas", len(df_filtrado.columns))
    
    with col_e3:
        if 'Favorecido Nome' in df_filtrado.columns:
            st.metric("🏪 Fornecedores Únicos", formatar_numero(df_filtrado['Favorecido Nome'].nunique()))
    
    with col_e4:
        periodo = ""
        if 'Data Emissão' in df_filtrado.columns:
            min_data = df_filtrado['Data Emissão'].min()
            max_data = df_filtrado['Data Emissão'].max()
            if pd.notna(min_data) and pd.notna(max_data):
                periodo = f"{min_data.strftime('%d/%m/%Y')} a {max_data.strftime('%d/%m/%Y')}"
        st.metric("📅 Período", periodo if periodo else "N/A")

# =============================================================================
# FOOTER
# =============================================================================
st.markdown("---")
st.markdown("""
<div style='text-align: center; color: #64748b; padding: 2rem 0;'>
    <p><strong>Painel de Gestão Financeira - TRF5</strong></p>
    <p>Desenvolvido com Streamlit | Dados atualizados em tempo real</p>
</div>
""", unsafe_allow_html=True)