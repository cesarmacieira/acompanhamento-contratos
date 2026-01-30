import streamlit as st
import pandas as pd
import numpy as np
import plotly.express as px
from datetime import datetime
import warnings
warnings.filterwarnings("ignore")

# =============================================================================
# CONFIG
# =============================================================================
st.set_page_config(page_title="Painel Contratos & Finanças", page_icon="💰", layout="wide")

PARQUETS = [
    "Dados 2025.parquet",
    #"Dados 2026.parquet",
]

# =============================================================================
# CSS (sem sidebar, filtros no topo)
# =============================================================================
st.markdown("""
<style>
    .main-header {
        font-size: 2.2rem;
        font-weight: 800;
        color: #0f172a;
        margin: 0.25rem 0 0.75rem 0;
    }
    .sub-header {
        font-size: 1rem;
        color: #475569;
        margin-top: -0.35rem;
        margin-bottom: 1rem;
    }
    .card {
        border: 1px solid rgba(15, 23, 42, 0.10);
        border-radius: 14px;
        padding: 14px 14px 10px 14px;
        background: #fff;
        box-shadow: 0 2px 8px rgba(15,23,42,0.06);
    }
    .kpi-grid {
        display: grid;
        grid-template-columns: repeat(4, 1fr);
        gap: 10px;
        margin-top: 6px;
        margin-bottom: 12px;
    }
    @media (max-width: 1200px) {
        .kpi-grid { grid-template-columns: repeat(2, 1fr); }
    }
    @media (max-width: 700px) {
        .kpi-grid { grid-template-columns: repeat(1, 1fr); }
    }
    .kpi {
        border: 1px solid rgba(15, 23, 42, 0.10);
        border-radius: 14px;
        padding: 12px 12px 10px 12px;
        background: #ffffff;
    }
    .kpi-label { font-size: 0.82rem; color: #64748b; margin-bottom: 6px; }
    .kpi-value { font-size: 1.35rem; font-weight: 800; color: #0f172a; line-height: 1.2; }
    .kpi-help  { font-size: 0.78rem; color: #94a3b8; margin-top: 6px; }
    .filters-wrap {
        border: 1px solid rgba(15, 23, 42, 0.10);
        border-radius: 14px;
        padding: 12px;
        background: #ffffff;
        box-shadow: 0 2px 8px rgba(15,23,42,0.04);
        margin-bottom: 12px;
    }
    .section-title {
        font-size: 1.15rem;
        font-weight: 800;
        color: #0f172a;
        margin: 10px 0 6px 0;
    }
    .muted { color: #64748b; font-size: 0.9rem; }
</style>
""", unsafe_allow_html=True)

st.markdown('<div class="main-header">💰 Painel de Contratos & Finanças</div>', unsafe_allow_html=True)
st.markdown('<div class="sub-header">Leitura em Parquet (rápido) • Filtros no topo • Abas por visão</div>', unsafe_allow_html=True)

# =============================================================================
# HELPERS
# =============================================================================
def brl(x: float) -> str:
    if x is None or (isinstance(x, float) and np.isnan(x)):
        x = 0.0
    s = f"{float(x):,.2f}"
    return "R$ " + s.replace(",", "X").replace(".", ",").replace("X", ".")

@st.cache_data(show_spinner=False)
def load_data(parquets):
    dfs = []
    for p in parquets:
        dfp = pd.read_parquet(p)
        dfp["Arquivo"] = p
        dfs.append(dfp)
    df = pd.concat(dfs, ignore_index=True)

    # Normalizações
    if "Ano" in df.columns:
        df["Ano"] = df["Ano"].astype(str)

    # colunas-chave (podem variar conforme seu dataset)
    texto_cols = [
        "Centro.de.Custo", "Gestores", "Órgão",
        "Plano.Orçamentário.Nome", "Contrato",
        "Nota.Empenho", "Nota.Empenho.Completo",
        "Processo.SEI", "Natureza.Despesa.Nome",
        "Grupo.Despesa.Nome", "Favorecido.Nome",
        "Sigla", "Sigla.UG.Executora",
        "Documento.Origem", "Doc.-.Observação",
        "Descrição",
    ]
    for c in texto_cols:
        if c in df.columns:
            df[c] = df[c].fillna("Não informado").astype(str)

    # normaliza datas (se existirem)
    for c in ["Data.Emissão", "Data.Hora.Emissão", "Data"]:
        if c in df.columns:
            df[c] = pd.to_datetime(df[c], errors="coerce")

    # Colunas numéricas (baseadas no seu app anterior e no que você pediu)
    num_cols = [
        "Valor Limite Disponível",
        "Valor Destaque Concedido",
        "Valor Pré-Empenhos a Empenhar",
        "Valor Empenhos Total",
        "Valor Empenhos Pagos",
        "Valor RP Não Processados Inscritos",
        "Valor RP Não Processados Reinscritos",
        "Valor RP Processados Inscritos",
        "Valor RP Processados Reinscritos",
        "Valor RP Não Processados Cancelados",
        "Valor RP Processados Cancelados",
        "Valor RP Não Processados Bloqueados",
        "Valor RP Processados Pagos",
    ]

    # também aceita a nomenclatura "pontuada" que apareceu no seu app anterior
    alt_map = {
        "Valor Limite Disponível": ["Valor.Limite.Disponível"],
        "Valor Destaque Concedido": ["Valor.Destaque.Concedido"],
        "Valor Pré-Empenhos a Empenhar": ["Valor.Pré-Empenhos.a.Empenhar"],
        "Valor Empenhos Total": ["Valor.Empenhos.Total"],
        "Valor Empenhos Pagos": ["Valor.Empenhos.Pagos"],
        "Valor RP Não Processados Inscritos": ["Valor.RP.Não.Processados.Inscritos"],
        "Valor RP Não Processados Reinscritos": ["Valor.RP.Não.Processados.Reinscritos"],
        "Valor RP Processados Inscritos": ["Valor.RP.Processados.Inscritos"],
        "Valor RP Processados Reinscritos": ["Valor.RP.Processados.Reinscritos"],
        "Valor RP Não Processados Cancelados": ["Valor.RP.Não.Processados.Cancelados"],
        "Valor RP Processados Cancelados": ["Valor.RP.Processados.Cancelados"],
        "Valor RP Não Processados Bloqueados": ["Valor.RP.Não.Processados.Bloqueados"],
        "Valor RP Processados Pagos": ["Valor.RP.Processados.Pagos"],
    }
    # Se vier com colunas alternativas, cria as "padrão"
    for canonical, alts in alt_map.items():
        if canonical not in df.columns:
            for a in alts:
                if a in df.columns:
                    df[canonical] = df[a]
                    break
            if canonical not in df.columns:
                df[canonical] = 0.0

    # Converte numéricos (tolerante a pt-BR e strings)
    for c in num_cols:
        if c in df.columns:
            s = df[c].astype(str).str.strip()
            s = s.replace({"-": "", "nan": "", "None": "", "NaN": "", "": ""})
            # remove milhar e troca decimal
            s = s.str.replace(".", "", regex=False).str.replace(",", ".", regex=False)
            df[c] = pd.to_numeric(s, errors="coerce").fillna(0.0)

    return df

def compute_kpis(d: pd.DataFrame) -> dict:
    # Seus KPIs (como você definiu)
    limite_gastos = d["Valor Limite Disponível"].sum()
    destaques_concedidos = d["Valor Destaque Concedido"].sum()
    valor_pre_empenhado = d["Valor Pré-Empenhos a Empenhar"].sum()
    valor_empenhado = d["Valor Empenhos Total"].sum()
    valor_pago = d["Valor Empenhos Pagos"].sum()

    limite_disponivel = (d["Valor Limite Disponível"].sum()
                         - d["Valor Pré-Empenhos a Empenhar"].sum()
                         - d["Valor Empenhos Total"].sum())

    valor_a_pagar = d["Valor Empenhos Total"].sum() - d["Valor Empenhos Pagos"].sum()

    rp_inscritos = (
        d["Valor RP Não Processados Inscritos"].sum()
        + d["Valor RP Não Processados Reinscritos"].sum()
        + d["Valor RP Processados Inscritos"].sum()
        + d["Valor RP Processados Reinscritos"].sum()
    )

    rp_cancelados = (
        d["Valor RP Não Processados Cancelados"].sum()
        + d["Valor RP Processados Cancelados"].sum()
    )

    rp_bloqueados = d["Valor RP Não Processados Bloqueados"].sum()
    rp_pagos = d["Valor RP Processados Pagos"].sum()
    rp_a_pagar = rp_inscritos - rp_cancelados - rp_bloqueados - rp_pagos

    return {
        "Limite de Gastos": limite_gastos,
        "Destaques concedidos": destaques_concedidos,
        "Valor Pré-Empenhado": valor_pre_empenhado,
        "Valor Empenhado": valor_empenhado,
        "Valor Pago": valor_pago,
        "Limite disponível": limite_disponivel,
        "Valor a pagar": valor_a_pagar,
        "RP inscritos": rp_inscritos,
        "RP cancelados": rp_cancelados,
        "RP bloqueados": rp_bloqueados,
        "RP pagos": rp_pagos,
        "RP a pagar": rp_a_pagar,
    }

def safe_unique(df, col):
    if col in df.columns:
        vals = df[col].dropna().astype(str).unique().tolist()
        vals = [v for v in vals if v.strip() != ""]
        return sorted(vals)
    return []

# =============================================================================
# LOAD
# =============================================================================
with st.spinner("Carregando dados (Parquet)..."):
    df = load_data(PARQUETS)

# =============================================================================
# FILTROS (NO TOPO)
# =============================================================================
st.markdown('<div class="filters-wrap">', unsafe_allow_html=True)

c1, c2, c3, c4, c5 = st.columns([1.0, 1.4, 1.4, 1.4, 1.2])

anos = safe_unique(df, "Ano")
orgaos = safe_unique(df, "Órgão")
gestores = safe_unique(df, "Gestores")
centros = safe_unique(df, "Centro.de.Custo")
contratos = safe_unique(df, "Contrato")

ano_sel = c1.multiselect("Ano", anos, default=anos)
orgao_sel = c2.multiselect("Órgão", orgaos, default=orgaos[:1] if len(orgaos) else [])
gestor_sel = c3.multiselect("Gestor(a)", gestores, default=[])
centro_sel = c4.multiselect("Centro de Custo", centros, default=[])
contrato_sel = c5.multiselect("Contrato", contratos, default=[])

st.markdown("</div>", unsafe_allow_html=True)

# aplica filtros
df_f = df.copy()
if ano_sel and "Ano" in df_f.columns:
    df_f = df_f[df_f["Ano"].isin(ano_sel)]
if orgao_sel and "Órgão" in df_f.columns:
    df_f = df_f[df_f["Órgão"].isin(orgao_sel)]
if gestor_sel and "Gestores" in df_f.columns:
    df_f = df_f[df_f["Gestores"].isin(gestor_sel)]
if centro_sel and "Centro.de.Custo" in df_f.columns:
    df_f = df_f[df_f["Centro.de.Custo"].isin(centro_sel)]
if contrato_sel and "Contrato" in df_f.columns:
    df_f = df_f[df_f["Contrato"].isin(contrato_sel)]

st.caption(f"🔎 Registros filtrados: **{len(df_f):,}**")

# =============================================================================
# ABAS
# =============================================================================
tab1, tab2, tab3, tab4, tab5, tab6 = st.tabs([
    "📊 Visão Geral",
    "👤 Gestores",
    "🏢 Centro de Custos",
    "🧾 Empenhos & Pré-Empenhos",
    "📦 Restos a Pagar (RP)",
    "🔎 Busca / Detalhe"
])

# =============================================================================
# TAB 1 — VISÃO GERAL
# =============================================================================
with tab1:
    st.markdown('<div class="section-title">KPIs Financeiros</div>', unsafe_allow_html=True)
    k = compute_kpis(df_f)

    kpi_order = [
        "Limite de Gastos",
        "Destaques concedidos",
        "Valor Pré-Empenhado",
        "Valor Empenhado",
        "Valor Pago",
        "Valor a pagar",
        "Limite disponível",
        "RP inscritos",
        "RP cancelados",
        "RP bloqueados",
        "RP pagos",
        "RP a pagar",
    ]

    st.markdown('<div class="kpi-grid">', unsafe_allow_html=True)
    for key in kpi_order:
        st.markdown(f"""
            <div class="kpi">
                <div class="kpi-label">{key}</div>
                <div class="kpi-value">{brl(k.get(key, 0.0))}</div>
            </div>
        """, unsafe_allow_html=True)
    st.markdown("</div>", unsafe_allow_html=True)

    st.markdown('<div class="section-title">Dados (amostra filtrada)</div>', unsafe_allow_html=True)
    st.dataframe(df_f, use_container_width=True, height=520)

# =============================================================================
# TAB 2 — GESTORES
# =============================================================================
with tab2:
    st.markdown('<div class="section-title">Perfil dos Gestores</div>', unsafe_allow_html=True)
    if "Gestores" not in df_f.columns:
        st.info("Coluna 'Gestores' não encontrada.")
    else:
        # contratos: se não existir 'Contrato', conta Nota.Empenho.Completo ou Nota.Empenho
        if "Contrato" in df_f.columns:
            contrato_col = "Contrato"
        elif "Nota.Empenho.Completo" in df_f.columns:
            contrato_col = "Nota.Empenho.Completo"
        elif "Nota.Empenho" in df_f.columns:
            contrato_col = "Nota.Empenho"
        else:
            contrato_col = None

        grp = df_f.groupby("Gestores", dropna=False)

        resumo = pd.DataFrame({
            "Qtd Registros": grp.size(),
            "Qtd Contratos": grp[contrato_col].nunique() if contrato_col else grp.size(),
            "Limite Disponível (base)": grp["Valor Limite Disponível"].sum(),
            "Pré-Empenhado": grp["Valor Pré-Empenhos a Empenhar"].sum(),
            "Empenhado": grp["Valor Empenhos Total"].sum(),
            "Pago": grp["Valor Empenhos Pagos"].sum(),
        }).reset_index()

        resumo["Saldo Disponível"] = (
            resumo["Limite Disponível (base)"] - resumo["Pré-Empenhado"] - resumo["Empenhado"]
        )
        resumo["A Pagar (Empenhos)"] = resumo["Empenhado"] - resumo["Pago"]

        # RP
        resumo["RP Inscritos"] = grp["Valor RP Não Processados Inscritos"].sum() + grp["Valor RP Não Processados Reinscritos"].sum() + grp["Valor RP Processados Inscritos"].sum() + grp["Valor RP Processados Reinscritos"].sum()
        resumo["RP Cancelados"] = grp["Valor RP Não Processados Cancelados"].sum() + grp["Valor RP Processados Cancelados"].sum()
        resumo["RP Bloqueados"] = grp["Valor RP Não Processados Bloqueados"].sum()
        resumo["RP Pagos"] = grp["Valor RP Processados Pagos"].sum()
        resumo["RP a Pagar"] = resumo["RP Inscritos"] - resumo["RP Cancelados"] - resumo["RP Bloqueados"] - resumo["RP Pagos"]

        # ranking (maior impacto: a pagar + RP a pagar)
        resumo["Impacto Financeiro"] = resumo["A Pagar (Empenhos)"] + resumo["RP a Pagar"]
        resumo = resumo.sort_values("Impacto Financeiro", ascending=False)

        left, right = st.columns([1.3, 1.0])
        with left:
            st.dataframe(resumo, use_container_width=True, height=520)
        with right:
            fig = px.bar(resumo.head(15), x="Impacto Financeiro", y="Gestores", orientation="h")
            st.plotly_chart(fig, use_container_width=True)

# =============================================================================
# TAB 3 — CENTRO DE CUSTOS
# =============================================================================
with tab3:
    st.markdown('<div class="section-title">Centro de Custos</div>', unsafe_allow_html=True)
    if "Centro.de.Custo" not in df_f.columns:
        st.info("Coluna 'Centro.de.Custo' não encontrada.")
    else:
        grp = df_f.groupby("Centro.de.Custo", dropna=False)

        cc = pd.DataFrame({
            "Qtd Registros": grp.size(),
            "Limite Disponível (base)": grp["Valor Limite Disponível"].sum(),
            "Pré-Empenhado": grp["Valor Pré-Empenhos a Empenhar"].sum(),
            "Empenhado": grp["Valor Empenhos Total"].sum(),
            "Pago": grp["Valor Empenhos Pagos"].sum(),
        }).reset_index()

        cc["Saldo Disponível"] = cc["Limite Disponível (base)"] - cc["Pré-Empenhado"] - cc["Empenhado"]
        cc["A Pagar (Empenhos)"] = cc["Empenhado"] - cc["Pago"]
        cc["% Execução (Empenhos/Limite)"] = np.where(
            cc["Limite Disponível (base)"] > 0,
            cc["Empenhado"] / cc["Limite Disponível (base)"],
            0.0
        )

        cc = cc.sort_values("Empenhado", ascending=False)

        st.dataframe(cc, use_container_width=True, height=520)
        fig = px.bar(cc.head(20), x="Empenhado", y="Centro.de.Custo", orientation="h")
        st.plotly_chart(fig, use_container_width=True)

# =============================================================================
# TAB 4 — EMPENHOS & PRÉ-EMPENHOS
# =============================================================================
with tab4:
    st.markdown('<div class="section-title">Empenhos & Pré-Empenhos</div>', unsafe_allow_html=True)

    cA, cB, cC = st.columns(3)
    cA.metric("Pré-Empenhado (total)", brl(df_f["Valor Pré-Empenhos a Empenhar"].sum()))
    cB.metric("Empenhado (total)", brl(df_f["Valor Empenhos Total"].sum()))
    cC.metric("Pago (total)", brl(df_f["Valor Empenhos Pagos"].sum()))

    cols_show = []
    preferred = [
        "Ano","Órgão","Gestores","Centro.de.Custo","Contrato",
        "Processo.SEI","Natureza.Despesa.Nome","Descrição",
        "Valor Pré-Empenhos a Empenhar","Valor Empenhos Total","Valor Empenhos Pagos",
        "Nota.Empenho.Completo","Nota.Empenho","Data.Emissão","Tempo.Emissao.em.Dias"
    ]
    for c in preferred:
        if c in df_f.columns:
            cols_show.append(c)

    st.dataframe(df_f[cols_show] if cols_show else df_f, use_container_width=True, height=560)

# =============================================================================
# TAB 5 — RESTOS A PAGAR
# =============================================================================
with tab5:
    st.markdown('<div class="section-title">Restos a Pagar (RP)</div>', unsafe_allow_html=True)
    k = compute_kpis(df_f)

    c1, c2, c3, c4, c5 = st.columns(5)
    c1.metric("RP inscritos", brl(k["RP inscritos"]))
    c2.metric("RP cancelados", brl(k["RP cancelados"]))
    c3.metric("RP bloqueados", brl(k["RP bloqueados"]))
    c4.metric("RP pagos", brl(k["RP pagos"]))
    c5.metric("RP a pagar", brl(k["RP a pagar"]))

    # Visão por ano ou por centro, dependendo do que existir
    if "Ano" in df_f.columns:
        grp = df_f.groupby("Ano", dropna=False)
        rp_ano = pd.DataFrame({
            "RP inscritos": grp["Valor RP Não Processados Inscritos"].sum()
                + grp["Valor RP Não Processados Reinscritos"].sum()
                + grp["Valor RP Processados Inscritos"].sum()
                + grp["Valor RP Processados Reinscritos"].sum(),
            "RP cancelados": grp["Valor RP Não Processados Cancelados"].sum()
                + grp["Valor RP Processados Cancelados"].sum(),
            "RP bloqueados": grp["Valor RP Não Processados Bloqueados"].sum(),
            "RP pagos": grp["Valor RP Processados Pagos"].sum(),
        }).reset_index()
        rp_ano["RP a pagar"] = rp_ano["RP inscritos"] - rp_ano["RP cancelados"] - rp_ano["RP bloqueados"] - rp_ano["RP pagos"]
        st.dataframe(rp_ano, use_container_width=True)
        st.plotly_chart(px.bar(rp_ano, x="Ano", y="RP a pagar"), use_container_width=True)
    else:
        st.info("Coluna 'Ano' não encontrada para visão temporal.")

# =============================================================================
# TAB 6 — BUSCA / DETALHE
# =============================================================================
with tab6:
    st.markdown('<div class="section-title">Busca / Detalhamento</div>', unsafe_allow_html=True)

    q = st.text_input("Buscar (Processo SEI, Favorecido, Descrição, Nota de Empenho, etc.)", value="")
    d = df_f.copy()

    search_cols = [c for c in [
        "Processo.SEI","Favorecido.Nome","Descrição","Doc.-.Observação",
        "Nota.Empenho.Completo","Nota.Empenho","Contrato"
    ] if c in d.columns]

    if q.strip() and search_cols:
        mask = np.zeros(len(d), dtype=bool)
        qlow = q.lower().strip()
        for c in search_cols:
            mask |= d[c].astype(str).str.lower().str.contains(qlow, na=False)
        d = d[mask]

    st.caption(f"Resultados: **{len(d):,}**")
    st.dataframe(d, use_container_width=True, height=620)
