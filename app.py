import streamlit as st
import pandas as pd
import json  # mantido (não usado) para não alterar além do necessário
from datetime import datetime, timedelta
import hashlib
import plotly.express as px
import plotly.graph_objects as go

# Configuração da página
st.set_page_config(page_title="Gestão de Contratos", layout="wide", initial_sidebar_state="expanded")

# =========================
# ALTERADO: Persistência em Excel (.xlsx) ao invés de JSON
# =========================
CONTRATOS_FILE = "contratos.xlsx"
HISTORICO_FILE = "historico.xlsx"
USUARIOS_FILE = "usuarios.xlsx"

def _excel_read(filename):
    try:
        return pd.read_excel(filename)
    except FileNotFoundError:
        return pd.DataFrame()

def _excel_write(filename, df):
    df.to_excel(filename, index=False)

def load_data(filename, default_data):
    """
    ALTERADO: lê Excel e devolve o MESMO formato do código original:
    - contratos: list[dict]
    - historico: list[dict]
    - usuarios: dict[str] -> {senha, nivel}
    """
    df = _excel_read(filename)

    # Se não existir ou estiver vazio, retorna default
    if df.empty:
        return default_data

    # USUÁRIOS: dataframe -> dict
    if filename == USUARIOS_FILE:
        usuarios = {}
        for _, row in df.iterrows():
            u = str(row.get("usuario", "")).strip()
            if not u:
                continue
            usuarios[u] = {
                "senha": str(row.get("senha", "")).strip(),
                "nivel": str(row.get("nivel", "")).strip()
            }
        return usuarios

    # CONTRATOS / HISTÓRICO: dataframe -> list[dict]
    records = df.to_dict(orient="records")

    # Normalizar datas do contrato para string YYYY-MM-DD (como no original)
    if filename == CONTRATOS_FILE:
        date_cols = ["data_inicio", "data_fim_prevista", "data_fim_real", "data_assinatura"]
        for rec in records:
            for c in date_cols:
                v = rec.get(c, None)
                if pd.isna(v):
                    rec[c] = None
                else:
                    # Se veio como Timestamp/Datetime, converte para YYYY-MM-DD
                    try:
                        rec[c] = pd.to_datetime(v).strftime("%Y-%m-%d")
                    except Exception:
                        rec[c] = str(v)
            # datas de cadastro/atualização ficam string, como já estavam
            for c in ["data_cadastro", "ultima_atualizacao"]:
                v = rec.get(c, None)
                if pd.isna(v):
                    rec[c] = None
                else:
                    try:
                        rec[c] = pd.to_datetime(v).strftime("%Y-%m-%d %H:%M:%S")
                    except Exception:
                        rec[c] = str(v)

        # Garantir tipos simples
        for rec in records:
            if "id" in rec and not pd.isna(rec["id"]):
                try:
                    rec["id"] = int(rec["id"])
                except Exception:
                    pass
            if "valor" in rec and not pd.isna(rec["valor"]):
                try:
                    rec["valor"] = float(rec["valor"])
                except Exception:
                    pass

    if filename == HISTORICO_FILE:
        # manter timestamp como string do jeito original
        for rec in records:
            v = rec.get("timestamp", None)
            if pd.isna(v):
                rec["timestamp"] = None
            else:
                try:
                    rec["timestamp"] = pd.to_datetime(v).strftime("%Y-%m-%d %H:%M:%S")
                except Exception:
                    rec["timestamp"] = str(v)

    return records

def save_data(filename, data):
    """
    ALTERADO: grava Excel a partir do MESMO formato do código original
    """
    # USUÁRIOS: dict -> dataframe
    if filename == USUARIOS_FILE:
        rows = []
        for usuario, info in data.items():
            rows.append({
                "usuario": usuario,
                "senha": info.get("senha", ""),
                "nivel": info.get("nivel", "")
            })
        df = pd.DataFrame(rows)
        _excel_write(filename, df)
        return

    # CONTRATOS/HISTÓRICO: list[dict] -> dataframe
    df = pd.DataFrame(data)

    # Para contratos, converter strings de data para datetime no Excel (fica melhor no arquivo)
    if filename == CONTRATOS_FILE and not df.empty:
        for c in ["data_inicio", "data_fim_prevista", "data_fim_real", "data_assinatura"]:
            if c in df.columns:
                df[c] = pd.to_datetime(df[c], errors="coerce")
        for c in ["data_cadastro", "ultima_atualizacao"]:
            if c in df.columns:
                df[c] = pd.to_datetime(df[c], errors="coerce")

    # Para histórico, converter timestamp para datetime no Excel
    if filename == HISTORICO_FILE and not df.empty:
        if "timestamp" in df.columns:
            df["timestamp"] = pd.to_datetime(df["timestamp"], errors="coerce")

    _excel_write(filename, df)

# Função para hash de senha
def hash_password(password):
    return hashlib.sha256(password.encode()).hexdigest()

# Função para formatar valor em Real brasileiro
def formatar_real(valor):
    return f"R$ {valor:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")

# Função para formatar data em formato brasileiro
def formatar_data(data_str):
    if not data_str:
        return ""
    try:
        dt = datetime.strptime(data_str, "%Y-%m-%d")
        return dt.strftime("%d/%m/%Y")
    except:
        return data_str

# Função para formatar data e hora em formato brasileiro
def formatar_data_hora(data_hora_str):
    if not data_hora_str:
        return ""
    try:
        dt = datetime.strptime(data_hora_str, "%Y-%m-%d %H:%M:%S")
        return dt.strftime("%d/%m/%Y %H:%M:%S")
    except:
        return data_hora_str

# =========================
# ALTERADO: Simulação de contratos iniciais (apenas se não houver base)
# =========================
def seed_contratos_exemplo():
    hoje = datetime.now().date()
    exemplos = [
        {
            "id": 1,
            "numero_contrato": "CT-2024-001",
            "fornecedor": "Empresa Alpha LTDA",
            "objeto": "Serviços de TI (suporte + manutenção)",
            "valor": 250000.00,
            "setor": "TI",
            "gestor": "Carlos Silva",
            "data_inicio": (hoje - timedelta(days=180)).strftime("%Y-%m-%d"),
            "data_fim_prevista": (hoje + timedelta(days=20)).strftime("%Y-%m-%d"),
            "data_fim_real": None,
            "data_assinatura": (hoje - timedelta(days=200)).strftime("%Y-%m-%d"),
            "status": "Ativo",
            "observacoes": "Contrato de referência (simulado).",
            "data_cadastro": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "ultima_atualizacao": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        },
        {
            "id": 2,
            "numero_contrato": "CT-2023-014",
            "fornecedor": "Beta Consultoria",
            "objeto": "Consultoria financeira e compliance",
            "valor": 480000.00,
            "setor": "Financeiro",
            "gestor": "Ana Souza",
            "data_inicio": (hoje - timedelta(days=420)).strftime("%Y-%m-%d"),
            "data_fim_prevista": (hoje - timedelta(days=10)).strftime("%Y-%m-%d"),
            "data_fim_real": None,
            "data_assinatura": (hoje - timedelta(days=450)).strftime("%Y-%m-%d"),
            "status": "Ativo",
            "observacoes": "Prazo já vencido (simulado).",
            "data_cadastro": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "ultima_atualizacao": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        },
        {
            "id": 3,
            "numero_contrato": "CT-2025-007",
            "fornecedor": "Gamma Serviços",
            "objeto": "Serviços de limpeza e conservação predial",
            "valor": 120000.00,
            "setor": "Operações",
            "gestor": "Rafael Lima",
            "data_inicio": (hoje - timedelta(days=60)).strftime("%Y-%m-%d"),
            "data_fim_prevista": (hoje + timedelta(days=120)).strftime("%Y-%m-%d"),
            "data_fim_real": None,
            "data_assinatura": (hoje - timedelta(days=75)).strftime("%Y-%m-%d"),
            "status": "Em Análise",
            "observacoes": "Em análise de aditivo (simulado).",
            "data_cadastro": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "ultima_atualizacao": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        },
        {
            "id": 4,
            "numero_contrato": "CT-2022-033",
            "fornecedor": "Delta Marketing",
            "objeto": "Campanhas digitais e mídia paga",
            "valor": 90000.00,
            "setor": "Marketing",
            "gestor": "Fernanda Rocha",
            "data_inicio": (hoje - timedelta(days=900)).strftime("%Y-%m-%d"),
            "data_fim_prevista": (hoje - timedelta(days=500)).strftime("%Y-%m-%d"),
            "data_fim_real": (hoje - timedelta(days=490)).strftime("%Y-%m-%d"),
            "data_assinatura": (hoje - timedelta(days=920)).strftime("%Y-%m-%d"),
            "status": "Finalizado",
            "observacoes": "Finalizado (simulado).",
            "data_cadastro": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "ultima_atualizacao": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        },
    ]
    return exemplos

# Inicialização de dados
if 'contratos' not in st.session_state:
    st.session_state.contratos = load_data(CONTRATOS_FILE, [])  # ALTERADO
    # ALTERADO: se base vazia, simula e salva
    if not st.session_state.contratos:
        st.session_state.contratos = seed_contratos_exemplo()
        save_data(CONTRATOS_FILE, st.session_state.contratos)

if 'historico' not in st.session_state:
    st.session_state.historico = load_data(HISTORICO_FILE, [])  # ALTERADO

if 'usuarios' not in st.session_state:
    usuarios_default = {
        'César': {
            'senha': hash_password('Atletico@13'),
            'nivel': 'Administrador'
        }
    }
    st.session_state.usuarios = load_data(USUARIOS_FILE, usuarios_default)  # ALTERADO
    # ALTERADO: garantir persistência inicial em Excel
    save_data(USUARIOS_FILE, st.session_state.usuarios)

if 'logged_in' not in st.session_state:
    st.session_state.logged_in = False
    st.session_state.user_nivel = None

# Função para registrar ações
def registrar_acao(tipo, descricao, usuario='Sistema'):
    registro = {
        'timestamp': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
        'tipo': tipo,
        'descricao': descricao,
        'usuario': usuario
    }
    st.session_state.historico.append(registro)
    save_data(HISTORICO_FILE, st.session_state.historico)  # ALTERADO

# Função de login
def login_page():
    st.title("🔐 Login - Sistema de Gestão de Contratos")

    col1, col2, col3 = st.columns([1, 2, 1])

    with col2:
        st.markdown("### Acesso Restrito - Alta Gestão")
        
        with st.form("form_login", clear_on_submit=False):
            usuario = st.text_input("Usuário", placeholder="Digite seu usuário")
            senha = st.text_input("Senha", type="password", placeholder="Digite sua senha")
            
            col_a, col_b, col_c = st.columns([1, 2, 1])
            with col_b:
                submitted = st.form_submit_button("🔓 Entrar", use_container_width=True, type="primary")

            if submitted:
                if not usuario or not senha:
                    st.error("⚠️ Preencha usuário e senha!")
                elif usuario in st.session_state.usuarios:
                    if st.session_state.usuarios[usuario]['senha'] == hash_password(senha):
                        st.session_state.logged_in = True
                        st.session_state.user_nivel = st.session_state.usuarios[usuario]['nivel']
                        st.session_state.current_user = usuario
                        registrar_acao('LOGIN', f'Usuário {usuario} fez login', usuario)
                        st.success("✅ Login realizado com sucesso!")
                        st.rerun()
                    else:
                        st.error("❌ Senha incorreta!")
                        registrar_acao('LOGIN_FALHO', f'Tentativa de login falhou para usuário {usuario}', 'Sistema')
                else:
                    st.error("❌ Usuário não encontrado!")
                    registrar_acao('LOGIN_FALHO', f'Tentativa de login com usuário inexistente: {usuario}', 'Sistema')

        st.divider()
        with st.expander("ℹ️ Informações de Acesso", expanded=False):
            st.info("**Credenciais padrão:**\n\n👤 Usuário: César\n🔑 Senha: Atletico@13")
            st.caption("⚠️ Recomenda-se alterar as credenciais após o primeiro acesso")

# Parte 1: Cadastro de Contratos
def cadastro_contrato():
    st.header("📝 Cadastro de Novo Contrato")
    
    st.info("💡 Preencha todos os campos obrigatórios marcados com * antes de cadastrar")

    with st.form("form_cadastro", clear_on_submit=False):
        st.subheader("Informações do Contrato")
        col1, col2 = st.columns(2)

        with col1:
            numero_contrato = st.text_input("Número do Contrato*", placeholder="Ex: CT-2024-001", help="Número único de identificação do contrato")
            fornecedor = st.text_input("Fornecedor/Contratado*", placeholder="Nome completo da empresa", help="Razão social do fornecedor")
            objeto = st.text_area("Objeto do Contrato*", placeholder="Descrição detalhada dos serviços ou produtos", height=100, help="Descreva o que será contratado")
            valor = st.number_input("Valor do Contrato (R$)*", min_value=0.0, format="%.2f", help="Valor total do contrato")
            setor = st.selectbox("Setor Responsável*",
                               ["TI", "Financeiro", "RH", "Operações", "Compras", "Jurídico", "Marketing"],
                               help="Setor que irá gerenciar este contrato")

        with col2:
            gestor = st.text_input("Gestor Responsável*", placeholder="Nome do gestor", help="Nome completo do gestor responsável")
            data_assinatura = st.date_input("Data de Assinatura*", help="Data em que o contrato foi assinado")
            data_inicio = st.date_input("Data de Início*", help="Data de início da vigência do contrato")
            data_fim_prevista = st.date_input("Data de Término Prevista*", help="Data prevista para término do contrato")
            status = st.selectbox("Status", ["Ativo", "Em Análise", "Suspenso", "Finalizado"], help="Status atual do contrato")

        st.subheader("Informações Complementares")
        observacoes = st.text_area("Observações", placeholder="Adicione observações relevantes sobre o contrato (opcional)", height=80)

        col1, col2, col3 = st.columns([2, 1, 2])
        with col2:
            submitted = st.form_submit_button("💾 Cadastrar Contrato", use_container_width=True, type="primary")

        if submitted:
            # Validações
            erros = []
            if not numero_contrato or not numero_contrato.strip():
                erros.append("Número do Contrato")
            if not fornecedor or not fornecedor.strip():
                erros.append("Fornecedor")
            if not objeto or not objeto.strip():
                erros.append("Objeto do Contrato")
            if not gestor or not gestor.strip():
                erros.append("Gestor Responsável")
            if valor <= 0:
                erros.append("Valor do Contrato (deve ser maior que zero)")
            
            if erros:
                st.error(f"⚠️ Preencha corretamente os seguintes campos: {', '.join(erros)}")
            elif any(c['numero_contrato'].strip().upper() == numero_contrato.strip().upper() for c in st.session_state.contratos):
                st.error(f"⚠️ Já existe um contrato com o número {numero_contrato}. Use um número diferente.")
            elif data_fim_prevista < data_inicio:
                st.error("⚠️ A data de término prevista não pode ser anterior à data de início!")
            elif data_assinatura > data_inicio:
                st.warning("⚠️ Atenção: A data de assinatura é posterior à data de início do contrato. Deseja continuar?")
                # Ainda permite cadastrar, mas alerta
                contrato = {
                    'id': max([c['id'] for c in st.session_state.contratos], default=0) + 1,
                    'numero_contrato': numero_contrato.strip(),
                    'fornecedor': fornecedor.strip(),
                    'objeto': objeto.strip(),
                    'valor': valor,
                    'setor': setor,
                    'gestor': gestor.strip(),
                    'data_inicio': data_inicio.strftime('%Y-%m-%d'),
                    'data_fim_prevista': data_fim_prevista.strftime('%Y-%m-%d'),
                    'data_fim_real': None,
                    'data_assinatura': data_assinatura.strftime('%Y-%m-%d'),
                    'status': status,
                    'observacoes': observacoes.strip() if observacoes else "",
                    'data_cadastro': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                    'ultima_atualizacao': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
                }

                st.session_state.contratos.append(contrato)
                save_data(CONTRATOS_FILE, st.session_state.contratos)
                registrar_acao('CADASTRO', f'Contrato {numero_contrato} cadastrado - Fornecedor: {fornecedor} - Valor: {formatar_real(valor)}', 'Sistema')
                st.success(f"✅ Contrato {numero_contrato} cadastrado com sucesso!")
            else:
                contrato = {
                    'id': max([c['id'] for c in st.session_state.contratos], default=0) + 1,
                    'numero_contrato': numero_contrato.strip(),
                    'fornecedor': fornecedor.strip(),
                    'objeto': objeto.strip(),
                    'valor': valor,
                    'setor': setor,
                    'gestor': gestor.strip(),
                    'data_inicio': data_inicio.strftime('%Y-%m-%d'),
                    'data_fim_prevista': data_fim_prevista.strftime('%Y-%m-%d'),
                    'data_fim_real': None,
                    'data_assinatura': data_assinatura.strftime('%Y-%m-%d'),
                    'status': status,
                    'observacoes': observacoes.strip() if observacoes else "",
                    'data_cadastro': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                    'ultima_atualizacao': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
                }

                st.session_state.contratos.append(contrato)
                save_data(CONTRATOS_FILE, st.session_state.contratos)
                registrar_acao('CADASTRO', f'Contrato {numero_contrato} cadastrado - Fornecedor: {fornecedor} - Valor: {formatar_real(valor)}', 'Sistema')
                st.success(f"✅ Contrato {numero_contrato} cadastrado com sucesso!")
                
    # Mostrar resumo dos últimos contratos cadastrados
    if st.session_state.contratos:
        with st.expander("📋 Últimos contratos cadastrados", expanded=False):
            ultimos = sorted(st.session_state.contratos, key=lambda x: x['data_cadastro'], reverse=True)[:5]
            for c in ultimos:
                col1, col2, col3 = st.columns([2, 2, 1])
                with col1:
                    st.write(f"**{c['numero_contrato']}** - {c['fornecedor']}")
                with col2:
                    st.write(f"{formatar_real(c['valor'])} | {c['setor']}")
                with col3:
                    st.write(f"Status: {c['status']}")

# Parte 2: Atualização de Contratos
def atualizacao_contrato():
    st.header("🔄 Atualização de Contratos")

    if not st.session_state.contratos:
        st.warning("Nenhum contrato cadastrado ainda.")
        return

    # Filtros de busca
    st.subheader("🔍 Buscar Contrato")
    col1, col2, col3 = st.columns(3)
    
    with col1:
        filtro_setor = st.multiselect("Filtrar por Setor", 
                                      options=sorted(list(set([c['setor'] for c in st.session_state.contratos]))),
                                      default=sorted(list(set([c['setor'] for c in st.session_state.contratos]))))
    with col2:
        filtro_status = st.multiselect("Filtrar por Status",
                                       options=["Ativo", "Em Análise", "Suspenso", "Finalizado"],
                                       default=["Ativo", "Em Análise", "Suspenso", "Finalizado"])
    with col3:
        busca_texto = st.text_input("Buscar por número ou fornecedor", placeholder="Digite para buscar...")

    # Aplicar filtros
    contratos_filtrados = [c for c in st.session_state.contratos 
                          if c['setor'] in filtro_setor 
                          and c['status'] in filtro_status
                          and (not busca_texto or busca_texto.lower() in c['numero_contrato'].lower() 
                               or busca_texto.lower() in c['fornecedor'].lower())]

    if not contratos_filtrados:
        st.warning("Nenhum contrato encontrado com os filtros aplicados.")
        return

    # Seleção do contrato
    contratos_opcoes = {f"{c['numero_contrato']} - {c['fornecedor']} ({c['setor']}) - {formatar_real(c['valor'])}": c['id']
                        for c in contratos_filtrados}

    contrato_selecionado = st.selectbox("Selecione o Contrato para Atualizar", 
                                        list(contratos_opcoes.keys()),
                                        help="Escolha o contrato que deseja atualizar")

    if contrato_selecionado:
        contrato_id = contratos_opcoes[contrato_selecionado]
        contrato = next((c for c in st.session_state.contratos if c['id'] == contrato_id), None)

        if contrato:
            # Mostrar informações do contrato
            st.divider()
            st.subheader("📄 Informações Atuais do Contrato")
            
            col1, col2, col3, col4 = st.columns(4)
            with col1:
                st.metric("Status", contrato['status'])
            with col2:
                st.metric("Valor", formatar_real(contrato['valor']))
            with col3:
                st.metric("Início", formatar_data(contrato['data_inicio']))
            with col4:
                st.metric("Término Previsto", formatar_data(contrato['data_fim_prevista']))
            
            # Calcular dias restantes
            dias_restantes = (datetime.strptime(contrato['data_fim_prevista'], '%Y-%m-%d').date() - datetime.now().date()).days
            if dias_restantes < 0:
                st.error(f"⚠️ Contrato vencido há {abs(dias_restantes)} dias!")
            elif dias_restantes <= 30:
                st.warning(f"⚠️ Contrato vence em {dias_restantes} dias!")
            else:
                st.info(f"ℹ️ Faltam {dias_restantes} dias para o término do contrato")

            st.divider()

            with st.form("form_atualizacao", clear_on_submit=False):
                st.subheader("✏️ Atualizar Dados")

                col1, col2 = st.columns(2)

                with col1:
                    novo_status = st.selectbox("Status",
                                             ["Ativo", "Em Análise", "Suspenso", "Finalizado"],
                                             index=["Ativo", "Em Análise", "Suspenso", "Finalizado"].index(contrato['status']),
                                             help="Altere o status do contrato se necessário")
                    novo_valor = st.number_input("Valor (R$)", value=float(contrato['valor']), format="%.2f",
                                                help="Atualize o valor em caso de aditivos")
                    nova_data_fim = st.date_input("Data de Término Prevista",
                                                 value=datetime.strptime(contrato['data_fim_prevista'], '%Y-%m-%d'),
                                                 help="Altere a data de término se houver prorrogação")

                with col2:
                    data_fim_real = st.date_input("Data de Término Real (se aplicável)",
                                                 value=datetime.strptime(contrato['data_fim_real'], '%Y-%m-%d')
                                                 if contrato['data_fim_real'] else None,
                                                 help="Informe quando o contrato foi efetivamente encerrado")
                    novo_gestor = st.text_input("Gestor Responsável", value=contrato['gestor'],
                                               help="Altere o gestor responsável se necessário")
                    novo_setor = st.selectbox("Setor",
                                            ["TI", "Financeiro", "RH", "Operações", "Compras", "Jurídico", "Marketing"],
                                            index=["TI", "Financeiro", "RH", "Operações", "Compras", "Jurídico", "Marketing"].index(contrato['setor']),
                                            help="Altere o setor responsável se necessário")

                st.subheader("📝 Observações e Justificativa")
                novas_observacoes = st.text_area("Observações", value=contrato['observacoes'], height=80,
                                                help="Atualize as observações do contrato")
                motivo_atualizacao = st.text_area("Motivo da Atualização*",
                                                 placeholder="Descreva o motivo desta atualização (obrigatório)",
                                                 height=100,
                                                 help="Justifique as alterações realizadas - este campo é obrigatório")

                # Preview das alterações
                st.divider()
                st.subheader("👁️ Preview das Alterações")
                alteracoes_preview = []
                
                if contrato['status'] != novo_status:
                    alteracoes_preview.append(f"• Status: **{contrato['status']}** → **{novo_status}**")
                
                if contrato['valor'] != novo_valor:
                    alteracoes_preview.append(f"• Valor: **{formatar_real(contrato['valor'])}** → **{formatar_real(novo_valor)}**")
                
                if contrato['data_fim_prevista'] != nova_data_fim.strftime('%Y-%m-%d'):
                    alteracoes_preview.append(f"• Data Fim: **{formatar_data(contrato['data_fim_prevista'])}** → **{formatar_data(nova_data_fim.strftime('%Y-%m-%d'))}**")
                
                nova_data_fim_real_str = data_fim_real.strftime('%Y-%m-%d') if data_fim_real else None
                if contrato['data_fim_real'] != nova_data_fim_real_str:
                    antiga = formatar_data(contrato['data_fim_real']) if contrato['data_fim_real'] else "Não definida"
                    nova = formatar_data(nova_data_fim_real_str) if nova_data_fim_real_str else "Não definida"
                    alteracoes_preview.append(f"• Data Fim Real: **{antiga}** → **{nova}**")
                
                if contrato['gestor'] != novo_gestor:
                    alteracoes_preview.append(f"• Gestor: **{contrato['gestor']}** → **{novo_gestor}**")
                
                if contrato['setor'] != novo_setor:
                    alteracoes_preview.append(f"• Setor: **{contrato['setor']}** → **{novo_setor}**")
                
                if contrato['observacoes'] != novas_observacoes:
                    alteracoes_preview.append(f"• Observações foram alteradas")

                if alteracoes_preview:
                    st.warning("As seguintes alterações serão aplicadas:")
                    for alt in alteracoes_preview:
                        st.markdown(alt)
                else:
                    st.info("Nenhuma alteração detectada nos campos do formulário")

                col1, col2, col3 = st.columns([2, 1, 2])
                with col2:
                    submitted = st.form_submit_button("💾 Confirmar Atualização", use_container_width=True, type="primary")

                if submitted:
                    if not motivo_atualizacao or not motivo_atualizacao.strip():
                        st.error("⚠️ O campo 'Motivo da Atualização' é obrigatório!")
                    elif not novo_gestor or not novo_gestor.strip():
                        st.error("⚠️ O campo 'Gestor Responsável' não pode estar vazio!")
                    else:
                        # Detectar alterações
                        alteracoes = []
                        
                        if contrato['status'] != novo_status:
                            alteracoes.append(f"Status: {contrato['status']} → {novo_status}")
                        
                        if contrato['valor'] != novo_valor:
                            alteracoes.append(f"Valor: {formatar_real(contrato['valor'])} → {formatar_real(novo_valor)}")
                        
                        if contrato['data_fim_prevista'] != nova_data_fim.strftime('%Y-%m-%d'):
                            alteracoes.append(f"Data Fim Prevista: {formatar_data(contrato['data_fim_prevista'])} → {formatar_data(nova_data_fim.strftime('%Y-%m-%d'))}")
                        
                        nova_data_fim_real_str = data_fim_real.strftime('%Y-%m-%d') if data_fim_real else None
                        if contrato['data_fim_real'] != nova_data_fim_real_str:
                            antiga = formatar_data(contrato['data_fim_real']) if contrato['data_fim_real'] else "Não definida"
                            nova = formatar_data(nova_data_fim_real_str) if nova_data_fim_real_str else "Não definida"
                            alteracoes.append(f"Data Fim Real: {antiga} → {nova}")
                        
                        if contrato['gestor'] != novo_gestor:
                            alteracoes.append(f"Gestor: {contrato['gestor']} → {novo_gestor}")
                        
                        if contrato['setor'] != novo_setor:
                            alteracoes.append(f"Setor: {contrato['setor']} → {novo_setor}")
                        
                        if contrato['observacoes'] != novas_observacoes:
                            alteracoes.append(f"Observações alteradas")

                        # Atualizar contrato
                        idx = next(i for i, c in enumerate(st.session_state.contratos) if c['id'] == contrato_id)

                        st.session_state.contratos[idx].update({
                            'status': novo_status,
                            'valor': novo_valor,
                            'data_fim_prevista': nova_data_fim.strftime('%Y-%m-%d'),
                            'data_fim_real': data_fim_real.strftime('%Y-%m-%d') if data_fim_real else None,
                            'gestor': novo_gestor.strip(),
                            'setor': novo_setor,
                            'observacoes': novas_observacoes.strip() if novas_observacoes else "",
                            'ultima_atualizacao': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
                        })

                        save_data(CONTRATOS_FILE, st.session_state.contratos)

                        # Registrar log detalhado
                        log_alteracoes = " | ".join(alteracoes) if alteracoes else "Nenhuma alteração detectada"
                        registrar_acao('ATUALIZAÇÃO',
                                     f'Contrato {contrato["numero_contrato"]} atualizado. Motivo: {motivo_atualizacao.strip()}. Alterações: {log_alteracoes}',
                                     'Sistema')

                        st.success("✅ Contrato atualizado com sucesso!")
                        st.rerun()

# Parte 3: Dashboard de Gestão (Alta Gestão)
def dashboard_gestao():
    if not st.session_state.logged_in:
        login_page()
        return

    st.title("📊 Dashboard de Gestão - Alta Gestão")

    # Botão de logout
    col1, col2, col3 = st.columns([4, 1, 1])
    with col2:
        st.write(f"👤 {st.session_state.current_user}")
    with col3:
        if st.button("🚪 Sair"):
            st.session_state.logged_in = False
            st.session_state.user_nivel = None
            registrar_acao('LOGOUT', f'Usuário {st.session_state.current_user} fez logout',
                          st.session_state.current_user)
            st.rerun()

    if not st.session_state.contratos:
        st.warning("Nenhum contrato cadastrado ainda.")
        return

    # Converter para DataFrame
    df = pd.DataFrame(st.session_state.contratos)
    df['valor'] = df['valor'].astype(float)
    df['data_inicio'] = pd.to_datetime(df['data_inicio'])
    df['data_fim_prevista'] = pd.to_datetime(df['data_fim_prevista'])

    # Calcular métricas
    total_contratos = len(df)
    valor_total = df['valor'].sum()
    contratos_ativos = len(df[df['status'] == 'Ativo'])

    # Métricas principais
    col1, col2, col3, col4 = st.columns(4)
    col1.metric("Total de Contratos", total_contratos)
    col2.metric("Valor Total", formatar_real(valor_total))
    col3.metric("Contratos Ativos", contratos_ativos)
    col4.metric("Em Análise", len(df[df['status'] == 'Em Análise']))

    st.divider()

    # Gráficos
    tab1, tab2, tab3, tab4, tab5 = st.tabs(["📈 Visão Geral", "💰 Análise Financeira",
                                             "⏱️ Prazos", "👥 Gestores", "📜 Histórico"])

    with tab1:
        col1, col2 = st.columns(2)

        with col1:
            st.subheader("Contratos por Status")
            status_count = df['status'].value_counts()
            fig_status = px.pie(values=status_count.values, names=status_count.index,
                               title="Distribuição por Status")
            st.plotly_chart(fig_status, use_container_width=True)

        with col2:
            st.subheader("Contratos por Setor")
            setor_count = df['setor'].value_counts()
            fig_setor = px.bar(x=setor_count.index, y=setor_count.values,
                              labels={'x': 'Setor', 'y': 'Quantidade'},
                              title="Quantidade de Contratos por Setor")
            st.plotly_chart(fig_setor, use_container_width=True)

    with tab2:
        st.subheader("💰 Setores com Maiores Verbas")
        verba_setor = df.groupby('setor')['valor'].sum().sort_values(ascending=False)

        col1, col2 = st.columns([2, 1])
        with col1:
            fig_verba = px.bar(x=verba_setor.index, y=verba_setor.values,
                              labels={'x': 'Setor', 'y': 'Valor (R$)'},
                              title="Investimento por Setor")
            st.plotly_chart(fig_verba, use_container_width=True)

        with col2:
            df_verba = pd.DataFrame({
                'Setor': verba_setor.index,
                'Valor': [formatar_real(v) for v in verba_setor.values]
            })
            st.dataframe(df_verba, use_container_width=True)

    with tab3:
        st.subheader("⏱️ Cumprimento de Prazos")

        # Calcular dias até o fim
        hoje = pd.Timestamp.now()
        df['dias_restantes'] = (df['data_fim_prevista'] - hoje).dt.days
        df['prazo_status'] = df['dias_restantes'].apply(
            lambda x: 'Vencido' if x < 0 else ('Crítico' if x <= 30 else 'Normal')
        )

        col1, col2 = st.columns(2)

        with col1:
            prazo_count = df['prazo_status'].value_counts()
            fig_prazo = px.pie(values=prazo_count.values, names=prazo_count.index,
                              title="Situação de Prazos",
                              color_discrete_map={'Normal': 'green', 'Crítico': 'orange', 'Vencido': 'red'})
            st.plotly_chart(fig_prazo, use_container_width=True)

        with col2:
            st.markdown("**Contratos Críticos/Vencidos:**")
            criticos = df[df['prazo_status'].isin(['Crítico', 'Vencido'])][
                ['numero_contrato', 'fornecedor', 'dias_restantes', 'prazo_status']
            ].sort_values('dias_restantes')
            st.dataframe(criticos, use_container_width=True)

    with tab4:
        st.subheader("👥 Perfil dos Gestores")

        gestor_stats = df.groupby('gestor').agg({
            'id': 'count',
            'valor': 'sum',
            'status': lambda x: (x == 'Finalizado').sum()
        }).reset_index()
        gestor_stats.columns = ['Gestor', 'Qtd Contratos', 'Valor Total', 'Finalizados']
        gestor_stats['Taxa Conclusão'] = (gestor_stats['Finalizados'] / gestor_stats['Qtd Contratos'] * 100).round(1)
        
        # Formatar valor total
        gestor_stats['Valor Total Formatado'] = gestor_stats['Valor Total'].apply(formatar_real)
        gestor_stats['Taxa Conclusão Formatada'] = gestor_stats['Taxa Conclusão'].apply(lambda x: f"{x:.1f}%")
        
        display_stats = gestor_stats[['Gestor', 'Qtd Contratos', 'Valor Total Formatado', 'Finalizados', 'Taxa Conclusão Formatada']]
        display_stats.columns = ['Gestor', 'Qtd Contratos', 'Valor Total', 'Finalizados', 'Taxa Conclusão']

        st.dataframe(display_stats, use_container_width=True)

        col1, col2 = st.columns(2)
        with col1:
            fig_gestor_qtd = px.bar(gestor_stats, x='Gestor', y='Qtd Contratos',
                                   title="Contratos por Gestor")
            st.plotly_chart(fig_gestor_qtd, use_container_width=True)

        with col2:
            fig_gestor_valor = px.bar(gestor_stats, x='Gestor', y='Valor Total',
                                     title="Valor Total por Gestor")
            st.plotly_chart(fig_gestor_valor, use_container_width=True)

    with tab5:
        st.subheader("📜 Histórico de Operações")

        if st.session_state.historico:
            df_hist = pd.DataFrame(st.session_state.historico)
            df_hist = df_hist.sort_values('timestamp', ascending=False)
            
            # Formatar timestamp
            df_hist['timestamp_formatado'] = df_hist['timestamp'].apply(formatar_data_hora)

            # Filtros
            col1, col2 = st.columns(2)
            with col1:
                tipo_filtro = st.multiselect("Filtrar por Tipo",
                                            df_hist['tipo'].unique(),
                                            default=df_hist['tipo'].unique())
            with col2:
                usuario_filtro = st.multiselect("Filtrar por Usuário",
                                               df_hist['usuario'].unique(),
                                               default=df_hist['usuario'].unique())

            df_filtrado = df_hist[
                (df_hist['tipo'].isin(tipo_filtro)) &
                (df_hist['usuario'].isin(usuario_filtro))
            ]
            
            # Mostrar com timestamp formatado
            df_display = df_filtrado[['timestamp_formatado', 'tipo', 'descricao', 'usuario']].copy()
            df_display.columns = ['Data/Hora', 'Tipo', 'Descrição', 'Usuário']

            st.dataframe(df_display, use_container_width=True)
        else:
            st.info("Nenhum registro no histórico ainda.")

    st.divider()

    # Tabela completa de contratos
    st.subheader("📋 Todos os Contratos")
    
    # Criar cópia para display formatado
    df_display = df[['numero_contrato', 'fornecedor', 'setor', 'gestor', 'valor',
                     'status', 'data_inicio', 'data_fim_prevista']].copy()
    
    # Formatar valores e datas
    df_display['valor'] = df_display['valor'].apply(formatar_real)
    df_display['data_inicio'] = df_display['data_inicio'].apply(lambda x: x.strftime('%d/%m/%Y'))
    df_display['data_fim_prevista'] = df_display['data_fim_prevista'].apply(lambda x: x.strftime('%d/%m/%Y'))
    
    # Renomear colunas
    df_display.columns = ['Número', 'Fornecedor', 'Setor', 'Gestor', 'Valor', 'Status', 'Início', 'Fim Previsto']
    
    st.dataframe(df_display, use_container_width=True)

# =========================
# ALTERADO: Menu principal sem sidebar -> Tabs
# =========================
def main():
    st.title("🏢 Sistema de Gestão de Contratos")

    # (sem sidebar) — coloquei as instruções como expander para não alterar lógica do app
    with st.expander("📌 Instruções / Credenciais", expanded=False):
        st.markdown("""
        **Instruções:**
        - Use o Cadastro para novos contratos  
        - Use Atualização para modificar contratos existentes  
        - Dashboard requer login (alta gestão)
        """)

    tab_cad, tab_att, tab_dash = st.tabs([
        "📝 Cadastro de Contrato",
        "🔄 Atualização de Contratos",
        "📊 Dashboard - Alta Gestão"
    ])

    with tab_cad:
        cadastro_contrato()

    with tab_att:
        atualizacao_contrato()

    with tab_dash:
        dashboard_gestao()

if __name__ == "__main__":
    main()