import os
import shutil
from datetime import datetime
import streamlit as st
import sqlite3

# Banco de dados SQLite para controle de usuários e histórico
conn = sqlite3.connect('document_manager.db', check_same_thread=False)
c = conn.cursor()
c.execute('''CREATE TABLE IF NOT EXISTS users (
    username TEXT PRIMARY KEY,
    password TEXT,
    projects TEXT,
    permissions TEXT
)''')
c.execute('''CREATE TABLE IF NOT EXISTS logs (
    timestamp TEXT,
    user TEXT,
    action TEXT,
    file TEXT
)''')
conn.commit()

# Função para criar caminho com estrutura hierárquica
BASE_DIR = "uploads"
if not os.path.exists(BASE_DIR):
    os.makedirs(BASE_DIR)

def get_project_path(project, discipline, phase):
    path = os.path.join(BASE_DIR, project, discipline, phase)
    os.makedirs(path, exist_ok=True)
    return path

def save_versioned_file(file_path):
    if os.path.exists(file_path):
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        base, ext = os.path.splitext(file_path)
        versioned_path = f"{base}_v{timestamp}{ext}"
        shutil.move(file_path, versioned_path)

def log_action(user, action, file):
    c.execute("INSERT INTO logs (timestamp, user, action, file) VALUES (?, ?, ?, ?)",
              (datetime.now().isoformat(), user, action, file))
    conn.commit()

# Inicialização de sessão
if "authenticated" not in st.session_state:
    st.session_state.authenticated = False
if "registration_mode" not in st.session_state:
    st.session_state.registration_mode = False
if "registration_unlocked" not in st.session_state:
    st.session_state.registration_unlocked = False
if "admin_mode" not in st.session_state:
    st.session_state.admin_mode = False
if "admin_authenticated" not in st.session_state:
    st.session_state.admin_authenticated = False

# TELA DE LOGIN
st.title("Gerenciador de Documentos Inteligente")

if not st.session_state.authenticated and not st.session_state.registration_mode and not st.session_state.admin_mode:
    st.subheader("Login")
    login_user = st.text_input("Usuário")
    login_pass = st.text_input("Senha", type="password")
    if st.button("Entrar"):
        c.execute("SELECT * FROM users WHERE username=? AND password=?", (login_user, login_pass))
        if c.fetchone():
            st.session_state.authenticated = True
            st.session_state.username = login_user
            st.rerun()
        else:
            st.error("Credenciais inválidas.")

    st.markdown("---")
    st.markdown("### Novo no sistema?")
    if st.button("Registrar novo usuário"):
        st.session_state.registration_mode = True
        st.rerun()
    if st.button("Painel Administrativo"):
        st.session_state.admin_mode = True
        st.rerun()

# TELA DE SENHA MESTRA PARA PAINEL ADMIN
elif st.session_state.admin_mode and not st.session_state.admin_authenticated:
    st.subheader("Painel Administrativo - Acesso Restrito")
    master_pass = st.text_input("Senha Mestra", type="password")
    if st.button("Liberar Painel Admin"):
        if master_pass == "#Heisenberg7":
            st.session_state.admin_authenticated = True
            st.success("Acesso ao painel liberado.")
            st.rerun()
        else:
            st.error("Senha mestra incorreta.")
    if st.button("Voltar ao Login"):
        st.session_state.admin_mode = False
        st.rerun()

# PAINEL ADMINISTRATIVO
elif st.session_state.admin_mode and st.session_state.admin_authenticated:
    st.subheader("Painel Administrativo")

    filtro = st.text_input("🔍 Filtrar usuários por nome")

    usuarios = c.execute("SELECT username, projects, permissions FROM users").fetchall()
    usuarios = [u for u in usuarios if filtro.lower() in u[0].lower()] if filtro else usuarios

    todos_projetos = [p for p in os.listdir(BASE_DIR) if os.path.isdir(os.path.join(BASE_DIR, p))]

    for user, projetos_atuais, permissoes_atuais in usuarios:
        st.markdown(f"#### 👤 {user}")
        col1, col2 = st.columns([1, 2])

        with col1:
            if st.button(f"Excluir {user}"):
                c.execute("DELETE FROM users WHERE username=?", (user,))
                conn.commit()
                st.success(f"Usuário {user} removido.")
                st.rerun()

        with col2:
            projetos_selecionados = st.multiselect(
                f"Projetos ({user})",
                options=todos_projetos,
                default=projetos_atuais.split(',') if projetos_atuais else [],
                key=f"projetos_{user}"
            )

            permissoes = st.multiselect(
                f"Permissões ({user})",
                options=["upload", "download"],
                default=permissoes_atuais.split(',') if permissoes_atuais else [],
                key=f"perms_{user}"
            )

            nova_senha = st.text_input(f"Nova senha ({user})", key=f"senha_{user}")
            if st.button(f"Atualizar senha {user}"):
                c.execute(
                    "UPDATE users SET password=?, projects=?, permissions=? WHERE username=?",
                    (nova_senha, ','.join(projetos_selecionados), ','.join(permissoes), user)
                )
                conn.commit()
                st.success(f"Senha e permissões de {user} atualizadas.")
                st.rerun()

    if st.button("Sair do Painel Admin"):
        st.session_state.admin_authenticated = False
        st.session_state.admin_mode = False
        st.rerun()

# REGISTRO DE NOVO USUÁRIO
elif st.session_state.registration_mode and not st.session_state.authenticated:
    st.subheader("Registro de Novo Usuário")
    master_pass = st.text_input("Senha Mestra", type="password")
    if st.button("Liberar Acesso"):
        if master_pass == "#Heisenberg7":
            st.session_state.registration_unlocked = True
            st.success("Acesso liberado. Preencha os dados do novo usuário.")
        else:
            st.error("Senha Mestra incorreta.")

    if st.session_state.registration_unlocked:
        new_user = st.text_input("Novo Usuário")
        new_pass = st.text_input("Nova Senha", type="password")
        if st.button("Criar usuário"):
            c.execute("SELECT * FROM users WHERE username=?", (new_user,))
            if c.fetchone():
                st.error("Usuário já existe.")
            else:
                c.execute("INSERT INTO users (username, password, projects, permissions) VALUES (?, ?, ?, ?)",
                          (new_user, new_pass, '', 'upload,download'))
                conn.commit()
                st.success("Usuário registrado com sucesso.")
                st.session_state.registration_mode = False
                st.session_state.registration_unlocked = False
                st.rerun()

    if st.button("Voltar ao Login"):
        st.session_state.registration_mode = False
        st.session_state.registration_unlocked = False
        st.rerun()

# INTERFACE PRINCIPAL APÓS LOGIN
elif st.session_state.authenticated:
    username = st.session_state.username
    user_info = c.execute("SELECT permissions FROM users WHERE username=?", (username,)).fetchone()
    user_permissions = user_info[0].split(',') if user_info and user_info[0] else []

    st.sidebar.markdown(f"🔐 Logado como: **{username}**")
    if st.sidebar.button("Logout"):
        st.session_state.authenticated = False
        st.session_state.username = ""
        st.rerun()

    # UPLOAD DE ARQUIVOS
    if "upload" in user_permissions:
        st.markdown("### Upload de Arquivos")
        with st.form("upload_form"):
            project = st.text_input("Projeto")
            discipline = st.text_input("Disciplina")
            phase = st.text_input("Fase")
            uploaded_file = st.file_uploader("Escolha o arquivo")
            submitted = st.form_submit_button("Enviar")

            if submitted and uploaded_file:
                filename = uploaded_file.name
                path = get_project_path(project, discipline, phase)
                file_path = os.path.join(path, filename)
                save_versioned_file(file_path)
                with open(file_path, "wb") as f:
                    f.write(uploaded_file.read())
                st.success(f"Arquivo '{filename}' salvo com sucesso em {path}.")
                log_action(username, "upload", file_path)

    # BUSCA E DOWNLOAD DE DOCUMENTOS
    if "download" in user_permissions:
        st.markdown("### Pesquisa de Documentos")
        keyword = st.text_input("Buscar por palavra-chave")
        if keyword:
            matched_files = []
            for root, _, files in os.walk(BASE_DIR):
                for file in files:
                    if keyword.lower() in file.lower():
                        matched_files.append(os.path.join(root, file))

            if matched_files:
                st.markdown("#### Resultados da busca:")
                for file in matched_files:
                    relative_path = os.path.relpath(file, BASE_DIR)
                    st.write(f"📄 {relative_path}")
                    with open(file, "rb") as f:
                        if file.endswith(".pdf"):
                            st.download_button(label="📥 Baixar PDF", data=f, file_name=os.path.basename(file), mime="application/pdf")
                        elif file.endswith(('.png', '.jpg', '.jpeg')):
                            st.image(f.read(), caption=os.path.basename(file))
                            f.seek(0)
                            st.download_button(label="📥 Baixar Imagem", data=f, file_name=os.path.basename(file))
                        else:
                            st.download_button(label="📥 Baixar Arquivo", data=f, file_name=os.path.basename(file))
                    log_action(username, "download", file)
            else:
                st.warning("Nenhum arquivo encontrado com esse termo.")

    # LOG DE AÇÕES
    st.markdown("### Histórico de Ações")
    if st.checkbox("Mostrar log de ações"):
        logs = c.execute("SELECT * FROM logs ORDER BY timestamp DESC LIMIT 100").fetchall()
        for log in logs:
            st.write(f"{log[0]} | Usuário: {log[1]} | Ação: {log[2]} | Arquivo: {log[3]}")
