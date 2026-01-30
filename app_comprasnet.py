import streamlit as st
import pandas as pd
from datetime import datetime, timedelta
from buscador_contratos import BuscadorContratos
import plotly.express as px
from PIL import Image,ImageDraw,ImageFont
st.set_page_config(page_title="Gestão de Contratos Públicos",layout="wide")
#st.image("logo_policromia.png",width=180)
def header_banner():
    W,H=2200,140
    bg=(0,104,157,255)
    banner=Image.new("RGBA",(W,H),bg)
    draw=ImageDraw.Draw(banner)
    try: font=ImageFont.truetype("calibri.ttf", 70)
    except: font=ImageFont.load_default()

    # LOGO PRINCIPAL À ESQUERDA
    logo_esquerda="logo_horizontal_branca.png"
    im_left=Image.open(logo_esquerda).convert("RGBA")
    h_left=80
    w_left=int(im_left.size[0]*h_left/im_left.size[1])
    im_left=im_left.resize((w_left,h_left))
    left_x=32
    banner.alpha_composite(im_left,(left_x,(H-h_left)//2))

    # LOGOS À DIREITA (calcular largura total)
    logos_direita=[
        "logo_Justica_Federal_5Regiao_branca.png",
        "logo_Justica_Federal_Ceara_branca.png",
        "Logo_PNUD_branca.png"
    ]

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
    texto="Sistema de Gestão de Contratos Públicos"
    bbox=draw.textbbox((0,0),texto,font=font)
    text_w=bbox[2]-bbox[0]

    area_inicio=left_x+w_left+32
    area_fim=right_start-32
    centro_area=(area_inicio+area_fim)//2
    texto_x=centro_area-(text_w//2)

    draw.text((texto_x,(H-48)//2),texto,fill=(255,255,255,255),font=font)

    return banner

st.image(header_banner(),use_column_width=True)
#st.title("📑 Sistema de Gestão de Contratos Públicos")

# ======================================================
# CARREGAMENTO
# ======================================================
@st.cache_data(show_spinner=True)
def carregar_dados():
    buscador = BuscadorContratos()
    contratos = buscador.buscar_multiplos_anos("12000","090006",2015,datetime.now().year)
    return pd.DataFrame(contratos)

df = carregar_dados()
df = df.dropna(how="all")
df = df.dropna(subset=["numeroContrato","dataVigenciaFinal"])
if df.empty:
    st.warning("Nenhum contrato encontrado.")
    st.stop()

# ======================================================
# PRÉ-PROCESSAMENTO
# ======================================================
df["dataVigenciaInicial"] = pd.to_datetime(df["dataVigenciaInicial"], errors="coerce")
df["dataVigenciaFinal"] = pd.to_datetime(df["dataVigenciaFinal"], errors="coerce")
df["valorGlobal"] = pd.to_numeric(df["valorGlobal"], errors="coerce").fillna(0)

hoje = pd.Timestamp.today()

df["status"] = df["dataVigenciaFinal"].apply(lambda x: "Vencido" if x < hoje else "Vigente")
df["ano"] = df["dataVigenciaInicial"].dt.year

# ======================================================
# ABAS
# ======================================================
tab_lista, tab_alertas, tab_analises = st.tabs(["📋 Lista de Contratos", "🚨 Alertas", "📊 Análises"])

# ======================================================
# ABA 1 — LISTA
# ======================================================
with tab_lista:
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
    st.dataframe(df_f.sort_values("dataVigenciaFinal"),use_container_width=True,height=600)
    st.caption(f"Contratos exibidos: {len(df_f)}")
    import io
    buffer = io.BytesIO()

    with pd.ExcelWriter(buffer, engine="openpyxl") as writer:
        df_f.sort_values("dataVigenciaFinal").to_excel(
            writer,
            index=False,
            sheet_name="Contratos"
        )

    buffer.seek(0)

    st.download_button(
        label="⬇️ Baixar dados em Excel",
        data=buffer,
        file_name="contratos.xlsx",
        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    )

# ======================================================
# ABA 2 — ALERTAS
# ======================================================
with tab_alertas:
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

# ======================================================
# ABA 3 — ANÁLISES
# ======================================================
with tab_analises:
    st.subheader("Análises Gerenciais Completas")

    # ============ VISÃO GERAL ============
    st.markdown("## 📊 Visão Geral Consolidada")
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