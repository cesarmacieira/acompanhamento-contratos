import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import numpy as np
from datetime import datetime

# Configuração da página
st.set_page_config(page_title="Portal Financeiro TRF5", page_icon="💰", layout="wide", initial_sidebar_state="collapsed")

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

# Função para carregar dados
@st.cache_data
def load_data():
    try:
        # Tentar carregar parquet primeiro
        df = pd.read_parquet('Dados portal TRF5.parquet')

        # Renomear para o padrão com espaços
        df.columns = df.columns.str.replace('.', ' ')
    except:
        # Se falhar, carregar do xlsx (já vem com espaços nos nomes)
        df = pd.read_excel('Dados portal TRF5.xlsx')

    df['Ano'] = df['Ano'].astype(str)
    
    # Converter colunas financeiras object para numérico
    financial_cols = [
        'Valor Limite Disponível', 'Valor Destaque Concedido', 
        'Valor Pré-Empenhos a Empenhar', 'Valor Empenhos Total',
        'Valor Empenhos Pagos', 'Valor RP Não Processados Inscritos',
        'Valor RP Não Processados Reinscritos', 'Valor RP Processados Inscritos',
        'Valor RP Processados Reinscritos', 'Valor RP Não Processados Cancelados',
        'Valor RP Processados Cancelados', 'Valor RP Não Processados Bloqueados',
        'Valor RP Processados Pagos', 'Valor Empenhos Liquidação Total',
        'Valor Empenhos a Liquidar', 'Inscrito', 'LIMITE DE PAGAMENTO AJUSTADO',
        'Limite Disponível', 'LIMITE ORÇAMENTÁRIO AJUSTADO', 'R$ a pagar',
        'Restos a pagar', 'RESTOS A PAGAR ANULADOS', 'RESTOS A PAGAR INSCRITOS',
        'RESTOS A PAGAR PAGOS', 'RP a pagar', 'RP Anulados', 'RP Bloqueados',
        'RP Cancelados', 'RP Inscrito Líquido', 'RP Inscritos', 'RP Pagos',
        'Saldo', 'SALDO EM RESTOS A PAGAR', 'SALDO ORÇAMENTÁRIO DISPONÍVEL',
        'Valor Empenhado', 'Valor Pago', 'Valor Pré-Empenhado']
    
    for col in financial_cols:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors='coerce').fillna(0)
    
    # Calcular métricas derivadas conforme especificação
    # Valor a Pagar = Valor Empenhos Total - Valor Empenhos Pagos
    df['Valor a Pagar Calculado'] = df['Valor Empenhos Total'] - df['Valor Empenhos Pagos']
    
    # RP Inscritos = soma de todas as inscrições e reinscrições
    df['RP Inscritos Calculado'] = (df['Valor RP Não Processados Inscritos'] + df['Valor RP Não Processados Reinscritos'] +
        df['Valor RP Processados Inscritos'] + df['Valor RP Processados Reinscritos'])
    
    # RP Cancelados = soma de cancelamentos
    df['RP Cancelados Calculado'] = (df['Valor RP Não Processados Cancelados'] + df['Valor RP Processados Cancelados'])
    
    # RP Bloqueados
    df['RP Bloqueados Calculado'] = df['Valor RP Não Processados Bloqueados']
    
    # RP Pagos
    df['RP Pagos Calculado'] = df['Valor RP Processados Pagos']
    
    # RP a Pagar = RP Inscritos - RP Cancelados - RP Bloqueados - RP Pagos
    df['RP a Pagar Calculado'] = (df['RP Inscritos Calculado'] - df['RP Cancelados Calculado'] - 
        df['RP Bloqueados Calculado'] - df['RP Pagos Calculado'])
    return df

# Carregar dados
df = load_data()

# Título principal
st.title("💰 Portal Financeiro TRF5")
st.markdown("### Sistema de Acompanhamento e Análise de Gestão Orçamentária")

# Criar abas
tab1, tab2, tab3, tab4, tab5, tab6 = st.tabs(["📊 Visão Geral & Filtros", "👥 Análise por Gestores",
    "🏢 Análise por Centro de Custos", "💳 Empenhos Detalhados", "📋 Pré-Empenhos", "📈 Restos a Pagar"])

# ==================== ABA 1: VISÃO GERAL & FILTROS ====================
with tab1:
    st.header("Filtros e Visão Geral")
    # Filtros em colunas
    col1, col2, col3 = st.columns(3)
    with col1:
        anos_disponiveis = sorted(df['Ano'].unique())
        ano_selecionado = st.multiselect("Ano", options=anos_disponiveis)
    with col2:
        gestores_disponiveis = sorted([g for g in df['Gestores'].unique() if g != 'Não informado'])
        gestor_selecionado = st.multiselect("Gestor", options=['Todos'] + gestores_disponiveis,)
    with col3:
        centros_disponiveis = sorted([c for c in df['Centro de Custo'].unique() if c != 'Não informado'])
        centro_selecionado = st.multiselect("Centro de Custo", options=['Todos'] + centros_disponiveis)
    
    # Aplicar filtros
    df_filtered = df.copy()
    if ano_selecionado:
        df_filtered = df_filtered[df_filtered['Ano'].isin(ano_selecionado)]
    
    if 'Todos' not in gestor_selecionado and gestor_selecionado:
        df_filtered = df_filtered[df_filtered['Gestores'].isin(gestor_selecionado)]
    
    if 'Todos' not in centro_selecionado and centro_selecionado:
        df_filtered = df_filtered[df_filtered['Centro de Custo'].isin(centro_selecionado)]
        
    st.markdown("---")
    
    # Calcular indicadores principais usando as fórmulas corretas
    # Limite de Gastos = Valor Limite Disponível (conforme especificação)
    limite_gastos = df_filtered['Valor Limite Disponível'].sum()
    
    # Destaques concedidos = Sum(Valor Destaque Concedido)
    destaques_concedidos = df_filtered['Valor Destaque Concedido'].sum()
    
    # Valor Pré-Empenhado = Sum(Valor Pré-Empenhos a Empenhar)
    valor_pre_empenhado = df_filtered['Valor Pré-Empenhos a Empenhar'].sum()
    
    # Valor Empenhado = sum(Valor Empenhos Total)
    valor_empenhado = df_filtered['Valor Empenhos Total'].sum()
    
    # Valor Pago = sum(Valor Empenhos Pagos)
    valor_pago = df_filtered['Valor Empenhos Pagos'].sum()
    
    # Limite disponível = Valor Limite Disponível - Pré-Empenhos - Empenhos
    limite_disponivel = limite_gastos - valor_pre_empenhado - valor_empenhado
    
    # Valor a pagar = Empenhos - Pagos
    valor_a_pagar = df_filtered['Valor a Pagar Calculado'].sum()
    
    # RP usando campos calculados
    rp_inscritos = df_filtered['RP Inscritos Calculado'].sum()
    rp_cancelados = df_filtered['RP Cancelados Calculado'].sum()
    rp_bloqueados = df_filtered['RP Bloqueados Calculado'].sum()
    rp_pagos = df_filtered['RP Pagos Calculado'].sum()
    rp_a_pagar = df_filtered['RP a Pagar Calculado'].sum()
    
    # Mostrar indicadores principais em cards
    st.subheader("📊 Indicadores Financeiros Principais")
    
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        st.metric("Limite de Gastos", f"R$ {limite_gastos:,.2f}", help="Valor Limite Disponível")
        st.metric("Valor Empenhado", f"R$ {valor_empenhado:,.2f}", 
                  delta=f"{(valor_empenhado/limite_gastos*100) if limite_gastos > 0 else 0:.1f}% do limite", help="Soma dos empenhos totais")
    
    with col2:
        st.metric("Valor Pago", f"R$ {valor_pago:,.2f}",
            delta=f"{(valor_pago/valor_empenhado*100) if valor_empenhado > 0 else 0:.1f}% empenhado", help="Soma dos empenhos pagos")
        st.metric("Valor a Pagar", f"R$ {valor_a_pagar:,.2f}", help="Diferença entre empenhado e pago")
    
    with col3:
        st.metric("Valor Pré-Empenhado", f"R$ {valor_pre_empenhado:,.2f}", help="Soma dos pré-empenhos a empenhar")
        st.metric("Limite Disponível", f"R$ {limite_disponivel:,.2f}", help="Limite menos pré-empenhos e empenhos")
    
    with col4:
        st.metric("RP Inscritos", f"R$ {rp_inscritos:,.2f}", help="Total de restos a pagar inscritos")
        st.metric("RP a Pagar", f"R$ {rp_a_pagar:,.2f}", help="RP Inscritos - Cancelados - Bloqueados - Pagos")

    st.markdown("---")

    # Gráficos de visão geral
    col1, col2 = st.columns(2)
    with col1:
        st.subheader("Execução Orçamentária")
        fig_exec = go.Figure()
        fig_exec.add_trace(go.Bar(name='Empenhado', x=['Execução'], y=[valor_empenhado], marker_color='#0068c9',
            text=[f'R$ {valor_empenhado:,.0f}'], textposition='auto'))
        fig_exec.add_trace(go.Bar(name='Pago', x=['Execução'], y=[valor_pago], marker_color='#28a745',
            text=[f'R$ {valor_pago:,.0f}'], textposition='auto'))
        fig_exec.add_trace(go.Bar(name='A Pagar', x=['Execução'], y=[valor_a_pagar], marker_color='#ffc107',
            text=[f'R$ {valor_a_pagar:,.0f}'], textposition='auto'))
        fig_exec.update_layout(barmode='group', height=400, showlegend=True, xaxis_title="", yaxis_title="Valor (R$)",
            hovermode='x unified')
        st.plotly_chart(fig_exec, use_container_width=True)
    
    with col2:
        st.subheader("Distribuição do Limite")
        valores = [valor_empenhado, valor_pre_empenhado, max(0, limite_disponivel)]
        labels = ['Empenhado', 'Pré-Empenhado', 'Disponível']
        colors = ['#0068c9', '#ffc107', '#28a745'] 
        fig_dist = go.Figure(data=[go.Pie(labels=labels, values=valores, hole=0.4, marker=dict(colors=colors),
            textinfo='label+percent', textposition='outside')])  
        fig_dist.update_layout(height=400, showlegend=True)
        st.plotly_chart(fig_dist, use_container_width=True)
    
    # Tabela de resumo
    st.subheader("📋 Resumo dos Dados Filtrados")
    st.write(f"**Total de registros:** {len(df_filtered):,}")
    st.write(f"**Anos selecionados:** {', '.join(sorted(df_filtered['Ano'].unique()))}")
    st.write(f"**Gestores únicos:** {df_filtered['Gestores'].nunique()}")
    st.write(f"**Centros de Custo únicos:** {df_filtered['Centro de Custo'].nunique()}")
    st.write(df_filtered)

# ==================== ABA 2: ANÁLISE POR GESTORES ====================
with tab2:
    st.header("👥 Análise por Gestores")
    # Remover "Não informado" da análise
    df_gestores = df_filtered[df_filtered['Gestores'] != 'Não informado'].copy()
    if len(df_gestores) == 0:
        st.warning("Não há dados de gestores para os filtros selecionados.")
    else:
        # Agrupar por gestor
        gestores_agg = df_gestores.groupby('Gestores').agg({
            'Valor Limite Disponível': 'sum',
            'Valor Empenhos Total': 'sum',
            'Valor Empenhos Pagos': 'sum',
            'Valor Pré-Empenhos a Empenhar': 'sum',
            'RP Inscritos Calculado': 'sum',
            'RP a Pagar Calculado': 'sum',
            'Valor a Pagar Calculado': 'sum'}).reset_index()
        
        gestores_agg['% Execução'] = (gestores_agg['Valor Empenhos Total'] / gestores_agg['Valor Limite Disponível'] * 100).fillna(0)
        gestores_agg['% Pagamento'] = (gestores_agg['Valor Empenhos Pagos'] / gestores_agg['Valor Empenhos Total'] * 100).fillna(0)
        
        # Ordenar por valor empenhado
        gestores_agg = gestores_agg.sort_values('Valor Empenhos Total', ascending=False)
        
        # Métricas gerais
        col1, col2, col3, col4 = st.columns(4)
        with col1:
            st.metric("Total de Gestores", len(gestores_agg))
        with col2:
            st.metric("Maior Empenhador", gestores_agg.iloc[0]['Gestores'].split()[0] if len(gestores_agg) > 0 else "N/A")
        with col3:
            st.metric("Média de Empenho", f"R$ {gestores_agg['Valor Empenhos Total'].mean():,.2f}")
        with col4:
            st.metric("Média de Execução", f"{gestores_agg['% Execução'].mean():.1f}%")
        st.markdown("---")
        
        # Top 10 gestores por empenho
        col1, col2 = st.columns(2)
        with col1:
            st.subheader("🏆 Top 10 Gestores por Empenho")
            top10_gestores = gestores_agg.head(10)
            fig_top_gestores = go.Figure()
            fig_top_gestores.add_trace(go.Bar(x=top10_gestores['Valor Empenhos Total'], y=top10_gestores['Gestores'],
                orientation='h', marker_color='#0068c9', text=top10_gestores['Valor Empenhos Total'].apply(lambda x: f'R$ {x:,.0f}'),
                textposition='auto'))
            fig_top_gestores.update_layout(height=500, xaxis_title="Valor Empenhado (R$)",
                yaxis_title="", yaxis={'categoryorder':'total ascending'})
            st.plotly_chart(fig_top_gestores, use_container_width=True)
        
        with col2:
            st.subheader("📊 Comparativo Empenho vs Pagamento")
            top10_gestores_sorted = top10_gestores.sort_values('Valor Empenhos Total')
            fig_comp = go.Figure()
            fig_comp.add_trace(go.Bar(name='Empenhado', x=top10_gestores_sorted['Valor Empenhos Total'], y=top10_gestores_sorted['Gestores'],
                orientation='h', marker_color='#0068c9'))
            fig_comp.add_trace(go.Bar(name='Pago', x=top10_gestores_sorted['Valor Empenhos Pagos'], y=top10_gestores_sorted['Gestores'],
                orientation='h', marker_color='#28a745'))
            fig_comp.update_layout(height=500, barmode='group', xaxis_title="Valor (R$)", yaxis_title="", showlegend=True)
            st.plotly_chart(fig_comp, use_container_width=True)
        
        # Análise de execução orçamentária
        st.subheader("💼 Taxa de Execução Orçamentária por Gestor")
        
        fig_exec_gestores = go.Figure()
        
        gestores_top15 = gestores_agg.head(15).sort_values('% Execução')
        
        fig_exec_gestores.add_trace(go.Bar(x=gestores_top15['% Execução'], y=gestores_top15['Gestores'], orientation='h',
            marker=dict(color=gestores_top15['% Execução'], colorscale='RdYlGn', showscale=True, colorbar=dict(title="% Execução")),
            text=gestores_top15['% Execução'].apply(lambda x: f'{x:.1f}%'),
            textposition='auto'))
        
        fig_exec_gestores.update_layout(height=600, xaxis_title="Taxa de Execução (%)", yaxis_title="", showlegend=False)
        
        st.plotly_chart(fig_exec_gestores, use_container_width=True)
        
        # Tabela detalhada
        st.subheader("📋 Tabela Detalhada por Gestor")
        
        # Formatar tabela para exibição
        gestores_display = gestores_agg.copy()
        gestores_display['Valor Limite Disponível'] = gestores_display['Valor Limite Disponível'].apply(lambda x: f'R$ {x:,.2f}')
        gestores_display['Valor Empenhos Total'] = gestores_display['Valor Empenhos Total'].apply(lambda x: f'R$ {x:,.2f}')
        gestores_display['Valor Empenhos Pagos'] = gestores_display['Valor Empenhos Pagos'].apply(lambda x: f'R$ {x:,.2f}')
        gestores_display['Valor a Pagar Calculado'] = gestores_display['Valor a Pagar Calculado'].apply(lambda x: f'R$ {x:,.2f}')
        gestores_display['% Execução'] = gestores_display['% Execução'].apply(lambda x: f'{x:.2f}%')
        gestores_display['% Pagamento'] = gestores_display['% Pagamento'].apply(lambda x: f'{x:.2f}%')
        
        st.dataframe(gestores_display[['Gestores', 'Valor Limite Disponível', 'Valor Empenhos Total', 
                                       'Valor Empenhos Pagos', 'Valor a Pagar Calculado', '% Execução', '% Pagamento']],
            use_container_width=True, height=400)

# ==================== ABA 3: ANÁLISE POR CENTRO DE CUSTOS ====================
with tab3:
    st.header("🏢 Análise por Centro de Custos")
    
    # Remover "Não informado"
    df_centros = df_filtered[df_filtered['Centro de Custo'] != 'Não informado'].copy()
    
    if len(df_centros) == 0:
        st.warning("Não há dados de centros de custo para os filtros selecionados.")
    else:
        # Agrupar por centro de custo
        centros_agg = df_centros.groupby('Centro de Custo').agg({
            'Valor Limite Disponível': 'sum',
            'Valor Empenhos Total': 'sum',
            'Valor Empenhos Pagos': 'sum',
            'Valor Pré-Empenhos a Empenhar': 'sum',
            'Valor a Pagar Calculado': 'sum',
            'RP Inscritos Calculado': 'sum',
            'RP a Pagar Calculado': 'sum'}).reset_index()
        
        centros_agg['% Execução'] = (centros_agg['Valor Empenhos Total'] / centros_agg['Valor Limite Disponível'] * 100).fillna(0)
        centros_agg['% Pagamento'] = (centros_agg['Valor Empenhos Pagos'] / centros_agg['Valor Empenhos Total'] * 100).fillna(0)
        
        # Ordenar por valor empenhado
        centros_agg = centros_agg.sort_values('Valor Empenhos Total', ascending=False)
        
        # Métricas gerais
        col1, col2, col3, col4 = st.columns(4)
        
        with col1:
            st.metric("Total de Centros", len(centros_agg))
        
        with col2:
            st.metric("Centro com Maior Empenho", centros_agg.iloc[0]['Centro de Custo'][:20] + "..." if len(centros_agg) > 0 else "N/A")
        
        with col3:
            st.metric("Média de Empenho", f"R$ {centros_agg['Valor Empenhos Total'].mean():,.2f}")
        
        with col4:
            total_centros = centros_agg['Valor Empenhos Total'].sum()
            concentracao_top5 = centros_agg.head(5)['Valor Empenhos Total'].sum() / total_centros * 100 if total_centros > 0 else 0
            st.metric("Concentração Top 5", f"{concentracao_top5:.1f}%")
        
        st.markdown("---")
        
        # Gráficos
        col1, col2 = st.columns(2)
        with col1:
            st.subheader("🏆 Top 15 Centros de Custo por Empenho")
            top15_centros = centros_agg.head(15).sort_values('Valor Empenhos Total')
            fig_top_centros = go.Figure()
            fig_top_centros.add_trace(go.Bar(x=top15_centros['Valor Empenhos Total'], y=top15_centros['Centro de Custo'],
                orientation='h', marker_color='#0068c9', text=top15_centros['Valor Empenhos Total'].apply(lambda x: f'R$ {x/1000:.0f}K'),
                textposition='auto'))
            fig_top_centros.update_layout(height=600, xaxis_title="Valor Empenhado (R$)", yaxis_title="")
            st.plotly_chart(fig_top_centros, use_container_width=True)
        
        with col2:
            st.subheader("📊 Distribuição de Empenhos")
            # Criar categorias
            top10_valor = centros_agg.head(10)['Valor Empenhos Total'].sum()
            outros_valor = centros_agg['Valor Empenhos Total'].sum() - top10_valor
            fig_dist_centros = go.Figure(data=[go.Pie(labels=list(centros_agg.head(10)['Centro de Custo']) + ['Outros'],
                values=list(centros_agg.head(10)['Valor Empenhos Total']) + [outros_valor], hole=0.4, textinfo='label+percent',
                textposition='outside', marker=dict(colors=px.colors.qualitative.Set3))])
            fig_dist_centros.update_layout(height=600, showlegend=False)
            st.plotly_chart(fig_dist_centros, use_container_width=True)
        
        # Análise de pagamento
        st.subheader("💰 Análise de Pagamento por Centro de Custo")
        col1, col2 = st.columns(2)
        with col1:
            st.write("**Top 10 Centros com Maior Valor a Pagar**")
            top10_apagar = centros_agg.sort_values('Valor a Pagar Calculado', ascending=False).head(10)
            fig_apagar = go.Figure()
            fig_apagar.add_trace(go.Bar(x=top10_apagar['Valor a Pagar Calculado'], y=top10_apagar['Centro de Custo'],
                orientation='h', marker_color='#ffc107', text=top10_apagar['Valor a Pagar Calculado'].apply(lambda x: f'R$ {x/1000:.0f}K'),
                textposition='auto'))
            fig_apagar.update_layout(height=450, xaxis_title="Valor a Pagar (R$)", yaxis_title="", yaxis={'categoryorder':'total ascending'})
            st.plotly_chart(fig_apagar, use_container_width=True)
        
        with col2:
            st.write("**Taxa de Pagamento (% Pago / Empenhado)**")
            top10_centros_taxa = centros_agg.head(10).sort_values('% Pagamento')
            fig_taxa = go.Figure()
            fig_taxa.add_trace(go.Bar(x=top10_centros_taxa['% Pagamento'], y=top10_centros_taxa['Centro de Custo'],
                orientation='h', marker=dict(color=top10_centros_taxa['% Pagamento'], colorscale='RdYlGn', showscale=True,
                    colorbar=dict(title="% Pago")),
                text=top10_centros_taxa['% Pagamento'].apply(lambda x: f'{x:.1f}%'), textposition='auto'))
            fig_taxa.update_layout(height=450, xaxis_title="Taxa de Pagamento (%)", yaxis_title="")            
            st.plotly_chart(fig_taxa, use_container_width=True)
        
        # Tabela detalhada
        st.subheader("📋 Tabela Detalhada por Centro de Custo")
        
        centros_display = centros_agg.copy()
        centros_display['Valor Empenhos Total'] = centros_display['Valor Empenhos Total'].apply(lambda x: f'R$ {x:,.2f}')
        centros_display['Valor Empenhos Pagos'] = centros_display['Valor Empenhos Pagos'].apply(lambda x: f'R$ {x:,.2f}')
        centros_display['Valor a Pagar Calculado'] = centros_display['Valor a Pagar Calculado'].apply(lambda x: f'R$ {x:,.2f}')
        centros_display['% Execução'] = centros_display['% Execução'].apply(lambda x: f'{x:.2f}%')
        centros_display['% Pagamento'] = centros_display['% Pagamento'].apply(lambda x: f'{x:.2f}%')
        
        st.dataframe(centros_display[['Centro de Custo', 'Valor Empenhos Total', 'Valor Empenhos Pagos', 
                                      'Valor a Pagar Calculado', '% Execução', '% Pagamento']],
            use_container_width=True, height=400)

# ==================== ABA 4: EMPENHOS DETALHADOS ====================
with tab4:
    st.header("💳 Análise Detalhada de Empenhos")
    
    # Filtrar apenas registros com empenhos
    df_empenhos = df_filtered[df_filtered['Valor Empenhos Total'] > 0].copy()
    
    if len(df_empenhos) == 0:
        st.warning("Não há dados de empenhos para os filtros selecionados.")
    else:
        # Métricas principais
        col1, col2, col3, col4 = st.columns(4)
        
        with col1:
            st.metric("Total de Empenhos", f"{len(df_empenhos):,}")
        
        with col2:
            st.metric("Valor Total Empenhado", f"R$ {df_empenhos['Valor Empenhos Total'].sum():,.2f}")
        
        with col3:
            st.metric("Valor Médio por Empenho", f"R$ {df_empenhos['Valor Empenhos Total'].mean():,.2f}")
        
        with col4:
            st.metric("Maior Empenho", f"R$ {df_empenhos['Valor Empenhos Total'].max():,.2f}")
        
        st.markdown("---")
        
        # Análise temporal
        if 'Data Emissão' in df_empenhos.columns:
            st.subheader("📅 Evolução Temporal dos Empenhos")
            
            # Converter data
            df_empenhos['Data Emissão'] = pd.to_datetime(df_empenhos['Data Emissão'], errors='coerce')
            df_empenhos['Ano-Mês'] = df_empenhos['Data Emissão'].dt.to_period('M').astype(str)
            
            empenhos_mes = df_empenhos.groupby('Ano-Mês').agg({
                'Valor Empenhos Total': 'sum',
                'Nota Empenho': 'count'
            }).reset_index()
            
            empenhos_mes.columns = ['Mês', 'Valor Total', 'Quantidade']
            
            fig_temporal = make_subplots(
                rows=2, cols=1,
                subplot_titles=('Valor Total Empenhado por Mês', 'Quantidade de Empenhos por Mês'),
                vertical_spacing=0.15
            )
            
            fig_temporal.add_trace(
                go.Bar(x=empenhos_mes['Mês'], y=empenhos_mes['Valor Total'], 
                       name='Valor Total', marker_color='#0068c9'),
                row=1, col=1
            )
            
            fig_temporal.add_trace(
                go.Scatter(x=empenhos_mes['Mês'], y=empenhos_mes['Quantidade'], 
                          name='Quantidade', mode='lines+markers', marker_color='#28a745'),
                row=2, col=1
            )
            
            fig_temporal.update_xaxes(title_text="Mês", row=2, col=1)
            fig_temporal.update_yaxes(title_text="Valor (R$)", row=1, col=1)
            fig_temporal.update_yaxes(title_text="Quantidade", row=2, col=1)
            
            fig_temporal.update_layout(height=600, showlegend=False)
            
            st.plotly_chart(fig_temporal, use_container_width=True)
        
        # Análise por natureza de despesa
        if 'Natureza Despesa Nome' in df_empenhos.columns:
            st.subheader("📊 Empenhos por Natureza de Despesa")
            
            col1, col2 = st.columns(2)
            
            with col1:
                natureza_agg = df_empenhos.groupby('Natureza Despesa Nome').agg({
                    'Valor Empenhos Total': 'sum',
                    'Nota Empenho': 'count'
                }).reset_index()
                natureza_agg.columns = ['Natureza', 'Valor', 'Quantidade']
                natureza_agg = natureza_agg.sort_values('Valor', ascending=False).head(10)
                
                fig_natureza = go.Figure()
                fig_natureza.add_trace(go.Bar(
                    x=natureza_agg['Valor'],
                    y=natureza_agg['Natureza'],
                    orientation='h',
                    marker_color='#0068c9',
                    text=natureza_agg['Valor'].apply(lambda x: f'R$ {x/1000:.0f}K'),
                    textposition='auto'
                ))
                
                fig_natureza.update_layout(
                    title="Top 10 Naturezas por Valor",
                    height=450,
                    xaxis_title="Valor (R$)",
                    yaxis_title="",
                    yaxis={'categoryorder':'total ascending'}
                )
                
                st.plotly_chart(fig_natureza, use_container_width=True)
            
            with col2:
                fig_natureza_qty = go.Figure()
                fig_natureza_qty.add_trace(go.Bar(
                    x=natureza_agg['Quantidade'],
                    y=natureza_agg['Natureza'],
                    orientation='h',
                    marker_color='#28a745',
                    text=natureza_agg['Quantidade'],
                    textposition='auto'
                ))
                
                fig_natureza_qty.update_layout(
                    title="Top 10 Naturezas por Quantidade",
                    height=450,
                    xaxis_title="Quantidade de Empenhos",
                    yaxis_title="",
                    yaxis={'categoryorder':'total ascending'}
                )
                
                st.plotly_chart(fig_natureza_qty, use_container_width=True)
        
        # Análise por favorecido
        if 'Favorecido Nome' in df_empenhos.columns:
            st.subheader("🏢 Top Favorecidos")
            
            favorecidos_agg = df_empenhos.groupby('Favorecido Nome').agg({
                'Valor Empenhos Total': 'sum',
                'Nota Empenho': 'count'
            }).reset_index()
            favorecidos_agg.columns = ['Favorecido', 'Valor Total', 'Quantidade']
            favorecidos_agg = favorecidos_agg.sort_values('Valor Total', ascending=False).head(15)
            
            fig_favorecidos = go.Figure()
            fig_favorecidos.add_trace(go.Bar(
                x=favorecidos_agg['Valor Total'],
                y=favorecidos_agg['Favorecido'],
                orientation='h',
                marker_color='#0068c9',
                text=favorecidos_agg['Valor Total'].apply(lambda x: f'R$ {x/1e6:.1f}M'),
                textposition='auto',
                hovertemplate='<b>%{y}</b><br>Valor: R$ %{x:,.2f}<br>Quantidade: %{customdata}<extra></extra>',
                customdata=favorecidos_agg['Quantidade']
            ))
            
            fig_favorecidos.update_layout(
                height=600,
                xaxis_title="Valor Total (R$)",
                yaxis_title="",
                yaxis={'categoryorder':'total ascending'}
            )
            
            st.plotly_chart(fig_favorecidos, use_container_width=True)
        
        # Tabela de maiores empenhos
        st.subheader("📋 Maiores Empenhos Individuais")
        
        maiores_empenhos = df_empenhos.nlargest(20, 'Valor Empenhos Total')[
            ['Nota Empenho', 'Favorecido Nome', 'Gestores', 'Centro de Custo', 
             'Valor Empenhos Total', 'Valor Empenhos Pagos', 'Data Emissão']
        ].copy()
        
        if 'Gestores' not in maiores_empenhos.columns and 'Gestores' in maiores_empenhos.columns:
            maiores_empenhos['Gestores'] = df_empenhos.loc[maiores_empenhos.index, 'Gestores']
        
        maiores_empenhos['Valor Empenhos Total'] = maiores_empenhos['Valor Empenhos Total'].apply(lambda x: f'R$ {x:,.2f}')
        maiores_empenhos['Valor Empenhos Pagos'] = maiores_empenhos['Valor Empenhos Pagos'].apply(lambda x: f'R$ {x:,.2f}')
        
        st.dataframe(maiores_empenhos, use_container_width=True, height=400)

# ==================== ABA 5: PRÉ-EMPENHOS ====================
with tab5:
    st.header("📋 Análise de Pré-Empenhos")
    
    df_pre = df_filtered[df_filtered['Valor Pré-Empenhos a Empenhar'] > 0].copy()
    
    if len(df_pre) == 0:
        st.warning("Não há dados de pré-empenhos para os filtros selecionados.")
    else:
        # Métricas
        col1, col2, col3, col4 = st.columns(4)
        
        with col1:
            st.metric("Total de Pré-Empenhos", f"{len(df_pre):,}")
        
        with col2:
            st.metric("Valor Total", f"R$ {df_pre['Valor Pré-Empenhos a Empenhar'].sum():,.2f}")
        
        with col3:
            st.metric("Valor Médio", f"R$ {df_pre['Valor Pré-Empenhos a Empenhar'].mean():,.2f}")
        
        with col4:
            st.metric("Maior Pré-Empenho", f"R$ {df_pre['Valor Pré-Empenhos a Empenhar'].max():,.2f}")
        
        st.markdown("---")
        
        # Análises
        col1, col2 = st.columns(2)
        
        with col1:
            st.subheader("👥 Pré-Empenhos por Gestor")
            
            pre_gestores = df_pre[df_pre['Gestores'] != 'Não informado'].groupby('Gestores').agg({
                'Valor Pré-Empenhos a Empenhar': 'sum'
            }).reset_index()
            pre_gestores = pre_gestores.sort_values('Valor Pré-Empenhos a Empenhar', ascending=False).head(10)
            
            fig_pre_gestores = go.Figure()
            fig_pre_gestores.add_trace(go.Bar(
                x=pre_gestores['Valor Pré-Empenhos a Empenhar'],
                y=pre_gestores['Gestores'],
                orientation='h',
                marker_color='#ffc107',
                text=pre_gestores['Valor Pré-Empenhos a Empenhar'].apply(lambda x: f'R$ {x:,.0f}'),
                textposition='auto'
            ))
            
            fig_pre_gestores.update_layout(
                height=400,
                xaxis_title="Valor (R$)",
                yaxis_title="",
                yaxis={'categoryorder':'total ascending'}
            )
            
            st.plotly_chart(fig_pre_gestores, use_container_width=True)
        
        with col2:
            st.subheader("🏢 Pré-Empenhos por Centro de Custo")
            
            pre_centros = df_pre[df_pre['Centro de Custo'] != 'Não informado'].groupby('Centro de Custo').agg({
                'Valor Pré-Empenhos a Empenhar': 'sum'
            }).reset_index()
            pre_centros = pre_centros.sort_values('Valor Pré-Empenhos a Empenhar', ascending=False).head(10)
            
            fig_pre_centros = go.Figure()
            fig_pre_centros.add_trace(go.Bar(
                x=pre_centros['Valor Pré-Empenhos a Empenhar'],
                y=pre_centros['Centro de Custo'],
                orientation='h',
                marker_color='#0068c9',
                text=pre_centros['Valor Pré-Empenhos a Empenhar'].apply(lambda x: f'R$ {x:,.0f}'),
                textposition='auto'
            ))
            
            fig_pre_centros.update_layout(
                height=400,
                xaxis_title="Valor (R$)",
                yaxis_title="",
                yaxis={'categoryorder':'total ascending'}
            )
            
            st.plotly_chart(fig_pre_centros, use_container_width=True)
        
        # Tabela detalhada
        st.subheader("📋 Detalhamento dos Pré-Empenhos")
        
        pre_display = df_pre[['Gestores', 'Centro de Custo', 'Natureza Despesa Nome', 
                              'Valor Pré-Empenhos a Empenhar']].copy()
        pre_display['Valor Pré-Empenhos a Empenhar'] = pre_display['Valor Pré-Empenhos a Empenhar'].apply(lambda x: f'R$ {x:,.2f}')
        
        st.dataframe(pre_display, use_container_width=True, height=400)

# ==================== ABA 6: RESTOS A PAGAR ====================
with tab6:
    st.header("📈 Análise de Restos a Pagar")
    
    df_rp = df_filtered[df_filtered['RP Inscritos Calculado'] > 0].copy()
    
    if len(df_rp) == 0:
        st.warning("Não há dados de restos a pagar para os filtros selecionados.")
    else:
        # Métricas principais usando campos calculados
        total_rp_inscritos = df_rp['RP Inscritos Calculado'].sum()
        total_rp_pagos = df_rp['RP Pagos Calculado'].sum()
        total_rp_cancelados = df_rp['RP Cancelados Calculado'].sum()
        total_rp_bloqueados = df_rp['RP Bloqueados Calculado'].sum()
        total_rp_a_pagar = df_rp['RP a Pagar Calculado'].sum()
        
        col1, col2, col3, col4, col5 = st.columns(5)
        
        with col1:
            st.metric("RP Inscritos", f"R$ {total_rp_inscritos:,.2f}")
        
        with col2:
            st.metric("RP Pagos", f"R$ {total_rp_pagos:,.2f}", 
                     delta=f"{(total_rp_pagos/total_rp_inscritos*100) if total_rp_inscritos > 0 else 0:.1f}%")
        
        with col3:
            st.metric("RP Cancelados", f"R$ {total_rp_cancelados:,.2f}")
        
        with col4:
            st.metric("RP Bloqueados", f"R$ {total_rp_bloqueados:,.2f}")
        
        with col5:
            st.metric("RP a Pagar", f"R$ {total_rp_a_pagar:,.2f}",
                     delta=f"{(total_rp_a_pagar/total_rp_inscritos*100) if total_rp_inscritos > 0 else 0:.1f}%")
        
        st.markdown("---")
        
        # Gráfico de fluxo
        st.subheader("💰 Fluxo dos Restos a Pagar")
        
        col1, col2 = st.columns(2)
        
        with col1:
            fig_rp_flow = go.Figure()
            
            categorias = ['Inscritos', 'Pagos', 'Cancelados', 'Bloqueados', 'A Pagar']
            valores = [total_rp_inscritos, total_rp_pagos, total_rp_cancelados, 
                      total_rp_bloqueados, total_rp_a_pagar]
            cores = ['#0068c9', '#28a745', '#dc3545', '#6c757d', '#ffc107']
            
            fig_rp_flow.add_trace(go.Bar(
                x=categorias,
                y=valores,
                marker_color=cores,
                text=[f'R$ {v/1e6:.1f}M' for v in valores],
                textposition='auto'
            ))
            
            fig_rp_flow.update_layout(
                height=400,
                xaxis_title="Categoria",
                yaxis_title="Valor (R$)",
                showlegend=False
            )
            
            st.plotly_chart(fig_rp_flow, use_container_width=True)
        
        with col2:
            fig_rp_pie = go.Figure(data=[go.Pie(
                labels=['Pagos', 'A Pagar', 'Cancelados', 'Bloqueados'],
                values=[total_rp_pagos, total_rp_a_pagar, total_rp_cancelados, total_rp_bloqueados],
                hole=0.4,
                marker=dict(colors=['#28a745', '#ffc107', '#dc3545', '#6c757d']),
                textinfo='label+percent',
                textposition='outside'
            )])
            
            fig_rp_pie.update_layout(
                title="Distribuição dos RP Inscritos",
                height=400
            )
            
            st.plotly_chart(fig_rp_pie, use_container_width=True)
        
        # Análise por gestor
        st.subheader("👥 RP por Gestor")
        
        rp_gestores = df_rp[df_rp['Gestores'] != 'Não informado'].groupby('Gestores').agg({
            'RP Inscritos Calculado': 'sum',
            'RP Pagos Calculado': 'sum',
            'RP a Pagar Calculado': 'sum'
        }).reset_index()
        rp_gestores = rp_gestores.sort_values('RP Inscritos Calculado', ascending=False).head(10)
        
        fig_rp_gestores = go.Figure()
        
        fig_rp_gestores.add_trace(go.Bar(
            name='Inscritos',
            x=rp_gestores['Gestores'],
            y=rp_gestores['RP Inscritos Calculado'],
            marker_color='#0068c9'
        ))
        
        fig_rp_gestores.add_trace(go.Bar(
            name='Pagos',
            x=rp_gestores['Gestores'],
            y=rp_gestores['RP Pagos Calculado'],
            marker_color='#28a745'
        ))
        
        fig_rp_gestores.add_trace(go.Bar(
            name='A Pagar',
            x=rp_gestores['Gestores'],
            y=rp_gestores['RP a Pagar Calculado'],
            marker_color='#ffc107'
        ))
        
        fig_rp_gestores.update_layout(
            barmode='group',
            height=400,
            xaxis_title="Gestor",
            yaxis_title="Valor (R$)",
            xaxis={'tickangle': -45}
        )
        
        st.plotly_chart(fig_rp_gestores, use_container_width=True)
        
        # Análise por centro de custo
        st.subheader("🏢 RP por Centro de Custo")
        
        rp_centros = df_rp[df_rp['Centro de Custo'] != 'Não informado'].groupby('Centro de Custo').agg({
            'RP Inscritos Calculado': 'sum',
            'RP Pagos Calculado': 'sum',
            'RP a Pagar Calculado': 'sum'
        }).reset_index()
        rp_centros = rp_centros.sort_values('RP a Pagar Calculado', ascending=False).head(15)
        
        fig_rp_centros = go.Figure()
        fig_rp_centros.add_trace(go.Bar(
            x=rp_centros['RP a Pagar Calculado'],
            y=rp_centros['Centro de Custo'],
            orientation='h',
            marker_color='#ffc107',
            text=rp_centros['RP a Pagar Calculado'].apply(lambda x: f'R$ {x/1000:.0f}K'),
            textposition='auto'
        ))
        
        fig_rp_centros.update_layout(
            title="Top 15 Centros com Maior RP a Pagar",
            height=600,
            xaxis_title="Valor (R$)",
            yaxis_title="",
            yaxis={'categoryorder':'total ascending'}
        )
        
        st.plotly_chart(fig_rp_centros, use_container_width=True)
        
        # Tabela detalhada
        st.subheader("📋 Tabela Detalhada de Restos a Pagar")
        
        rp_display = df_rp.groupby(['Gestores', 'Centro de Custo']).agg({
            'RP Inscritos Calculado': 'sum',
            'RP Pagos Calculado': 'sum',
            'RP Cancelados Calculado': 'sum',
            'RP Bloqueados Calculado': 'sum',
            'RP a Pagar Calculado': 'sum'
        }).reset_index()
        
        rp_display['RP Inscritos Calculado'] = rp_display['RP Inscritos Calculado'].apply(lambda x: f'R$ {x:,.2f}')
        rp_display['RP Pagos Calculado'] = rp_display['RP Pagos Calculado'].apply(lambda x: f'R$ {x:,.2f}')
        rp_display['RP Cancelados Calculado'] = rp_display['RP Cancelados Calculado'].apply(lambda x: f'R$ {x:,.2f}')
        rp_display['RP Bloqueados Calculado'] = rp_display['RP Bloqueados Calculado'].apply(lambda x: f'R$ {x:,.2f}')
        rp_display['RP a Pagar Calculado'] = rp_display['RP a Pagar Calculado'].apply(lambda x: f'R$ {x:,.2f}')
        
        rp_display.columns = ['Gestores', 'Centro de Custo', 'RP Inscritos', 'RP Pagos', 'RP Cancelados', 'RP Bloqueados', 'RP a Pagar']
        
        st.dataframe(rp_display, use_container_width=True, height=400)

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