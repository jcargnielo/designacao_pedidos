import streamlit as st
import pandas as pd
import hashlib
import os
from datetime import datetime
from io import BytesIO
from time import time

# ============================================
# CONFIGURAÇÕES INICIAIS
# ============================================
DB_PEDIDOS = "pedidos.csv"
DB_USUARIOS = "usuarios.csv"
COLUNAS_PEDIDOS = ["ID", "Pedido", "Funcionário", "Status", "Data Início", "Data Conclusão"]
COLUNAS_USUARIOS = ["username", "password", "role", "nome_completo"]
TIMEOUT_MINUTOS = 30

# Variáveis de sessão
if 'ultimo_pedido' not in st.session_state:
    st.session_state.ultimo_pedido = None
if 'notificado' not in st.session_state:
    st.session_state.notificado = False
if 'last_activity' not in st.session_state:
    st.session_state.last_activity = time()

# Cores para os status
CORES_STATUS = {
    "Pendente": "#FFCDD2",
    "Em andamento": "#E0E0E0",
    "Pausado": "#FFF9C4",
    "Concluído": "#C8E6C9"
}

# ============================================
# FUNÇÕES DE INICIALIZAÇÃO
# ============================================
def inicializar_arquivos():
    if not os.path.exists(DB_PEDIDOS):
        pd.DataFrame(columns=COLUNAS_PEDIDOS).to_csv(DB_PEDIDOS, index=False)
    
    if not os.path.exists(DB_USUARIOS):
        admin = pd.DataFrame([{
            "username": "admin",
            "password": hashlib.sha256("admin123".encode()).hexdigest(),
            "role": "lider",
            "nome_completo": "Administrador"
        }])
        admin.to_csv(DB_USUARIOS, index=False)

# ============================================
# FUNÇÕES DE USUÁRIOS
# ============================================
def carregar_usuarios():
    try:
        df = pd.read_csv(DB_USUARIOS)
        for col in COLUNAS_USUARIOS:
            if col not in df.columns:
                df[col] = "" if col != "role" else "funcionario"
        return df
    except FileNotFoundError:
        return pd.DataFrame(columns=COLUNAS_USUARIOS)

def salvar_usuarios(df):
    df.to_csv(DB_USUARIOS, index=False)

def verificar_login(username, senha):
    usuarios = carregar_usuarios()
    usuario = usuarios[usuarios["username"] == username]
    
    if not usuario.empty:
        hashed_pw = hashlib.sha256(senha.encode()).hexdigest()
        if usuario.iloc[0]["password"] == hashed_pw:
            st.session_state.last_activity = time()  # Resetar atividade ao logar
            return {
                "autenticado": True,
                "username": username,
                "role": usuario.iloc[0]["role"],
                "nome_completo": usuario.iloc[0]["nome_completo"]
            }
    return {"autenticado": False}

# ============================================
# FUNÇÕES DE PEDIDOS
# ============================================
def carregar_pedidos():
    try:
        df = pd.read_csv(DB_PEDIDOS)
        for col in COLUNAS_PEDIDOS:
            if col not in df.columns:
                df[col] = ""
        return df
    except FileNotFoundError:
        return pd.DataFrame(columns=COLUNAS_PEDIDOS)

def salvar_pedidos(df):
    df.to_csv(DB_PEDIDOS, index=False)

def adicionar_pedido(num_pedido, funcionario):
    df = carregar_pedidos()
    novo_id = df["ID"].max() + 1 if not df.empty else 1
    novo_pedido = pd.DataFrame([[
        novo_id,
        num_pedido,
        funcionario,
        "Pendente",
        datetime.now().strftime("%d/%m/%Y %H:%M"),
        ""
    ]], columns=COLUNAS_PEDIDOS)
    df = pd.concat([df, novo_pedido], ignore_index=True)
    salvar_pedidos(df)
    
    # Atualiza o último pedido adicionado para notificação
    st.session_state.ultimo_pedido = {
        "numero": num_pedido,
        "funcionario": funcionario,
        "timestamp": time()
    }
    st.session_state.notificado = False

def atualizar_status_pedido(id_pedido, novo_status):
    df = carregar_pedidos()
    idx = df[df["ID"] == id_pedido].index
    
    if not idx.empty:
        status_atual = df.loc[idx, "Status"].values[0]
        df.loc[idx, "Status"] = novo_status
        
        agora = datetime.now().strftime("%d/%m/%Y %H:%M")
        
        if novo_status == "Em andamento" and status_atual != "Em andamento":
            df.loc[idx, "Data Início"] = agora
        elif novo_status == "Concluído":
            df.loc[idx, "Data Conclusão"] = agora
        
        salvar_pedidos(df)
        return True
    return False

# ============================================
# FUNÇÕES AUXILIARES
# ============================================
def darken_color(hex_color, factor=0.2):
    """Escurece uma cor HEX pelo fator especificado"""
    hex_color = hex_color.lstrip('#')
    rgb = tuple(int(hex_color[i:i+2], 16) for i in (0, 2, 4))
    rgb = [int(x * (1 - factor)) for x in rgb]
    return f"#{rgb[0]:02x}{rgb[1]:02x}{rgb[2]:02x}"

def to_excel(df):
    output = BytesIO()
    with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
        df.to_excel(writer, index=False, sheet_name='Pedidos')
    return output.getvalue()

# ============================================
# TELAS DO SISTEMA
# ============================================
def tela_login():
    st.title("🔐 Sistema de Pedidos - Login")
    
    with st.form("form_login"):
        username = st.text_input("Usuário")
        senha = st.text_input("Senha", type="password")
        
        if st.form_submit_button("Entrar"):
            login = verificar_login(username, senha)
            if login["autenticado"]:
                st.session_state.update(login)
                st.rerun()
            else:
                st.error("Credenciais inválidas")

def tela_gerenciar_usuarios():
    st.title("👥 Gerenciamento de Usuários")
    st.session_state.last_activity = time()  # Registrar atividade
    
    usuarios_df = carregar_usuarios()
    usuarios_lista = usuarios_df["username"].tolist()
    
    col1, col2 = st.columns([1, 2])
    
    with col1:
        st.subheader("Lista de Usuários")
        usuario_selecionado = st.selectbox(
            "Selecione um usuário",
            [""] + usuarios_lista,
            format_func=lambda x: "Selecione..." if x == "" else x,
            key="select_usuario"
        )
        
        if st.button("➕ Novo Usuário", key="btn_novo_usuario"):
            st.session_state["usuario_editando"] = {
                "username": "",
                "nome_completo": "",
                "role": "funcionario",
                "modo": "criar"
            }
            st.rerun()

    with col2:
        if usuario_selecionado == "" and "usuario_editando" not in st.session_state:
            st.info("Selecione um usuário ou clique em 'Novo Usuário'")
            return
        
        if usuario_selecionado and ("usuario_editando" not in st.session_state or 
                                  st.session_state["usuario_editando"]["modo"] != "criar"):
            usuario_data = usuarios_df[usuarios_df["username"] == usuario_selecionado].iloc[0]
            st.session_state["usuario_editando"] = {
                "username": usuario_data["username"],
                "nome_completo": usuario_data["nome_completo"],
                "role": usuario_data["role"],
                "modo": "editar"
            }
        
        if "usuario_editando" in st.session_state:
            modo = st.session_state["usuario_editando"]["modo"]
            
            if modo == "editar":
                st.subheader(f"📝 Editando: {st.session_state['usuario_editando']['username']}")
            else:
                st.subheader("➕ Criar Novo Usuário")
            
            with st.form("form_usuario"):
                if modo == "criar":
                    st.session_state["usuario_editando"]["username"] = st.text_input(
                        "Nome de usuário*",
                        value=st.session_state["usuario_editando"]["username"]
                    )
                
                st.session_state["usuario_editando"]["nome_completo"] = st.text_input(
                    "Nome completo*",
                    value=st.session_state["usuario_editando"]["nome_completo"]
                )
                
                if modo == "editar":
                    nova_senha = st.text_input("Nova senha (deixe em branco para manter)", type="password")
                    if nova_senha:
                        st.session_state["usuario_editando"]["password"] = nova_senha
                else:
                    st.session_state["usuario_editando"]["password"] = st.text_input(
                        "Senha*",
                        type="password"
                    )
                
                st.session_state["usuario_editando"]["role"] = st.selectbox(
                    "Tipo de usuário*",
                    ["lider", "funcionario"],
                    index=0 if st.session_state["usuario_editando"]["role"] == "lider" else 1,
                    format_func=lambda x: "Líder" if x == "lider" else "Funcionário"
                )
                
                col1, col2 = st.columns(2)
                with col1:
                    if st.form_submit_button("💾 Salvar"):
                        username = st.session_state["usuario_editando"]["username"]
                        nome_completo = st.session_state["usuario_editando"]["nome_completo"]
                        role = st.session_state["usuario_editando"]["role"]
                        
                        if not username or not nome_completo or (modo == "criar" and not st.session_state["usuario_editando"]["password"]):
                            st.error("Preencha todos os campos obrigatórios (*)")
                        else:
                            if modo == "editar":
                                usuarios_df.loc[usuarios_df["username"] == username, "nome_completo"] = nome_completo
                                usuarios_df.loc[usuarios_df["username"] == username, "role"] = role
                                if "password" in st.session_state["usuario_editando"]:
                                    usuarios_df.loc[usuarios_df["username"] == username, "password"] = hashlib.sha256(
                                        st.session_state["usuario_editando"]["password"].encode()
                                    ).hexdigest()
                                salvar_usuarios(usuarios_df)
                                st.success("Usuário atualizado com sucesso!")
                            else:
                                if username in usuarios_lista:
                                    st.error("Nome de usuário já existe")
                                else:
                                    novo_usuario = pd.DataFrame([{
                                        "username": username,
                                        "password": hashlib.sha256(
                                            st.session_state["usuario_editando"]["password"].encode()
                                        ).hexdigest(),
                                        "role": role,
                                        "nome_completo": nome_completo
                                    }])
                                    usuarios_df = pd.concat([usuarios_df, novo_usuario], ignore_index=True)
                                    salvar_usuarios(usuarios_df)
                                    st.success("Usuário criado com sucesso!")
                            
                            st.session_state.pop("usuario_editando")
                            st.rerun()
                
                with col2:
                    if modo == "editar":
                        if st.form_submit_button("🗑️ Excluir Usuário"):
                            username = st.session_state["usuario_editando"]["username"]
                            role = st.session_state["usuario_editando"]["role"]
                            
                            if role == "lider" and len(usuarios_df[usuarios_df["role"] == "lider"]) <= 1:
                                st.error("Não é possível remover o último líder")
                            else:
                                usuarios_df = usuarios_df[usuarios_df["username"] != username]
                                salvar_usuarios(usuarios_df)
                                st.success("Usuário removido com sucesso!")
                                st.session_state.pop("usuario_editando")
                                st.rerun()
                    else:
                        if st.form_submit_button("❌ Cancelar"):
                            st.session_state.pop("usuario_editando")
                            st.rerun()

def tela_pedidos_lider():
    st.title("📋 Gerenciamento de Pedidos")
    st.session_state.last_activity = time()  # Registrar atividade

    with st.expander("➕ Novo Pedido", expanded=True):
        col1, col2 = st.columns(2)
        num_pedido = col1.text_input("Número do Pedido*", key="novo_pedido_num")
        funcionarios = carregar_usuarios()
        funcionarios = funcionarios[funcionarios["role"] == "funcionario"]["nome_completo"].tolist()
        funcionario = col2.selectbox("Designar para*", funcionarios, key="novo_pedido_func")

        if st.button("Adicionar", key="btn_adicionar_pedido"):
            if num_pedido and num_pedido.isdigit():
                adicionar_pedido(int(num_pedido), funcionario)
                st.success("Pedido adicionado!")
                st.rerun()
            else:
                st.error("Número de pedido inválido")

    st.subheader("🔍 Filtros Avançados")
    pedidos_df = carregar_pedidos()
    
    col1, col2 = st.columns(2)
    with col1:
        filtro_funcionario = st.selectbox(
            "Funcionário",
            ["Todos"] + sorted(pedidos_df["Funcionário"].unique().tolist()) if not pedidos_df.empty else ["Todos"]
        )
    with col2:
        filtro_status = st.selectbox("Status", ["Todos"] + list(CORES_STATUS.keys()))

    if filtro_funcionario != "Todos":
        pedidos_df = pedidos_df[pedidos_df["Funcionário"] == filtro_funcionario]
    if filtro_status != "Todos":
        pedidos_df = pedidos_df[pedidos_df["Status"] == filtro_status]

    # Botões exportar
    st.write("")
    col1, col2 = st.columns(2)
    with col1:
        st.download_button(
            label="📥 Baixar Relatório Completo (Excel)",
            data=to_excel(pedidos_df),
            file_name='relatorio_pedidos.xlsx',
            mime='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
        )
    with col2:
        st.download_button(
            label="📥 Baixar Relatório Completo (CSV)",
            data=pedidos_df.to_csv(index=False).encode('utf-8'),
            file_name='relatorio_pedidos.csv',
            mime='text/csv'
        )

    st.subheader("📝 Todos os Pedidos")

    if not pedidos_df.empty:
        for _, row in pedidos_df.iterrows():
            cor_status = CORES_STATUS.get(row["Status"], "#FFFFFF")
            
            with st.container():
                st.markdown(
                    f'<div style="background-color:{cor_status}; padding:12px; border-radius:10px; margin-bottom:15px; box-shadow:0 2px 4px rgba(0,0,0,0.1);">'
                    f'<div style="font-size:18px; font-weight:bold; margin-bottom:8px;">Pedido #{row["Pedido"]}</div>'
                    f'<div style="display:flex; justify-content:space-between; margin-bottom:10px;">'
                    f'<span>Funcionário: {row["Funcionário"]}</span>'
                    f'<span style="background-color:{darken_color(cor_status)}; padding:2px 8px; border-radius:4px;">{row["Status"]}</span>'
                    f'</div>',
                    unsafe_allow_html=True
                )
                
                with st.expander("🔍 Ver detalhes", expanded=False):
                    st.markdown(
                        f'<div style="padding:8px;">'
                        f'{f"<p><strong>Iniciado em:</strong> {row['Data Início']}</p>" if row["Data Início"] else ""}'
                        f'{f"<p><strong>Concluído em:</strong> {row['Data Conclusão']}</p>" if row["Data Conclusão"] else ""}'
                        '</div>',
                        unsafe_allow_html=True
                    )
                    
                    col1, col2, col3 = st.columns(3)
                    with col1:
                        novo_funcionario = st.selectbox(
                            "Designar para",
                            funcionarios,
                            index=funcionarios.index(row["Funcionário"]) if row["Funcionário"] in funcionarios else 0,
                            key=f"func_{row['ID']}"
                        )
                    with col2:
                        novo_status = st.selectbox(
                            "Status",
                            list(CORES_STATUS.keys()),
                            index=list(CORES_STATUS.keys()).index(row["Status"]),
                            key=f"status_{row['ID']}"
                        )
                    
                    col4, col5 = st.columns(2)
                    with col4:
                        if st.button("💾 Salvar", key=f"save_{row['ID']}"):
                            if row["Funcionário"] != novo_funcionario or row["Status"] != novo_status:
                                pedidos_df.loc[pedidos_df["ID"] == row["ID"], "Funcionário"] = novo_funcionario
                                atualizar_status_pedido(row["ID"], novo_status)
                                st.success("Alterações salvas!")
                                st.rerun()
                    with col5:
                        if st.button("🗑️ Excluir", key=f"del_{row['ID']}"):
                            pedidos_df = pedidos_df[pedidos_df["ID"] != row["ID"]]
                            salvar_pedidos(pedidos_df)
                            st.success("Pedido excluído!")
                            st.rerun()
                
                st.markdown('</div>', unsafe_allow_html=True)
    else:
        st.info("Nenhum pedido encontrado com os filtros selecionados.")

def tela_pedidos_funcionario():
    # Verifica se há novos pedidos para este funcionário
    if (st.session_state.ultimo_pedido and 
        st.session_state.ultimo_pedido["funcionario"] == st.session_state["nome_completo"] and
        not st.session_state.notificado):
        
        st.toast(
            f"📢 Novo pedido #{st.session_state.ultimo_pedido['numero']} atribuído a você!",
            icon="⚠️"
        )
        st.session_state.notificado = True
    
    # Título com fonte menor
    st.markdown(
        f'<h1 style="font-size:22px;">📋 Meus Pedidos - {st.session_state["nome_completo"]}</h1>',
        unsafe_allow_html=True
    )
    
    st.session_state.last_activity = time()  # Registrar atividade
    
    pedidos_df = carregar_pedidos()
    meus_pedidos = pedidos_df[(pedidos_df["Funcionário"] == st.session_state["nome_completo"]) & 
                             (pedidos_df["Status"] != "Concluído")]
    
    if not meus_pedidos.empty:
        for _, row in meus_pedidos.iterrows():
            cor_status = CORES_STATUS.get(row["Status"], "#FFFFFF")
            
            with st.container():
                st.markdown(
                    f'<div style="background-color:{cor_status}; padding:12px; border-radius:10px; margin-bottom:15px; box-shadow:0 2px 4px rgba(0,0,0,0.1);">'
                    f'<div style="font-size:16px; font-weight:bold; margin-bottom:8px;">Pedido #{row["Pedido"]}</div>'
                    f'<div style="display:flex; justify-content:space-between; margin-bottom:10px;">'
                    f'<span>Status: {row["Status"]}</span>'
                    f'</div>',
                    unsafe_allow_html=True
                )
                
                with st.expander("🔍 Ver detalhes", expanded=False):
                    st.markdown(
                        f'<div style="padding:8px;">'
                        f'{f"<p><strong>Iniciado em:</strong> {row['Data Início']}</p>" if row["Data Início"] else ""}'
                        f'{f"<p><strong>Concluído em:</strong> {row['Data Conclusão']}</p>" if row["Data Conclusão"] else ""}'
                        '</div>',
                        unsafe_allow_html=True
                    )
                    
                    col1, col2, col3 = st.columns(3)
                    with col1:
                        if st.button("▶️ Iniciar", key=f"iniciar_{row['ID']}"):
                            if row["Status"] in ["Pendente", "Pausado"]:
                                if atualizar_status_pedido(row["ID"], "Em andamento"):
                                    st.success("Pedido iniciado!")
                                    st.rerun()
                            else:
                                st.warning("Ação não permitida")
                    with col2:
                        if st.button("⏸️ Pausar", key=f"pausar_{row['ID']}"):
                            if row["Status"] == "Em andamento":
                                if atualizar_status_pedido(row["ID"], "Pausado"):
                                    st.success("Pedido pausado!")
                                    st.rerun()
                            else:
                                st.warning("Só pausar em andamento")
                    with col3:
                        if st.button("✅ Finalizar", key=f"finalizar_{row['ID']}"):
                            if row["Status"] in ["Em andamento", "Pausado"]:
                                if atualizar_status_pedido(row["ID"], "Concluído"):
                                    st.success("Pedido finalizado!")
                                    st.rerun()
                            else:
                                st.warning("Só finalizar em andamento/pausado")
                
                st.markdown('</div>', unsafe_allow_html=True)
    else:
        st.info("Nenhum pedido atribuído a você")

def tela_principal():
    st.sidebar.title(f"👋 Olá, {st.session_state['nome_completo']}")
    st.sidebar.subheader(f"Perfil: {'Líder' if st.session_state['role'] == 'lider' else 'Funcionário'}")
    
    # Atualiza atividade apenas em interações reais
    if st.sidebar.button("🚪 Sair"):
        st.session_state.clear()
        st.rerun()
    
    if st.session_state["role"] == "lider":
        opcao = st.sidebar.radio("Menu", ["📋 Pedidos", "👥 Usuários"])
        
        if opcao == "📋 Pedidos":
            tela_pedidos_lider()
        else:
            tela_gerenciar_usuarios()
    else:
        tela_pedidos_funcionario()

# ============================================
# APLICAÇÃO PRINCIPAL
# ============================================
def main():
    st.set_page_config(page_title="Sistema de Pedidos", layout="wide")
    inicializar_arquivos()
    
    # Verifica timeout apenas se autenticado
    if st.session_state.get("autenticado", False):
        inactive_seconds = time() - st.session_state.last_activity
        if inactive_seconds > TIMEOUT_MINUTOS * 60:
            st.warning(f"Sessão encerrada após {TIMEOUT_MINUTOS} minutos de inatividade")
            st.session_state.clear()
            st.rerun()
    
    if "autenticado" not in st.session_state:
        st.session_state["autenticado"] = False
    
    if not st.session_state["autenticado"]:
        tela_login()
    else:
        tela_principal()

if __name__ == "__main__":
    main()