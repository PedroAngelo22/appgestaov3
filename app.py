import os
import shutil
from datetime import datetime
import streamlit as st
import sqlite3

# Banco de dados SQLite
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

BASE_DIR = "uploads"
os.makedirs(BASE_DIR, exist_ok=True)

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

# Estado da sessão
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

st.title("Gerenciador de Documentos Inteligente")

# LOGIN
if not st.session_state.authenticated and not st.session_state.registration_mode and not st.session_state.admin_mode:
    st.subheader("Login")
    login_user = st.text_input("Usuário")
    login_pass = st.text_input("Senha", type="password")
    if st.button("Entrar"):
        result = c.execute("SELECT * FROM users WHERE username=? AND password=?", (login_user, login_pass)).fetchone()
        if result:
            st.session_state.authenticated = True
            st.session_state.username = login_user
            st.rerun()
        else:
            st.error("Credenciais inválidas.")

    if st.button("Registrar novo usuário"):
        st.session_state.registration_mode = True
        st.rerun()

    if st.button("Painel Administrativo"):
        st.session_state.admin_mode = True
        st.rerun()

# REGISTRO
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
            if c.execute("SELECT * FROM users WHERE username=?", (new_user,)).fetchone():
                st.error("Usuário já existe.")
            else:
                c.execute("INSERT INTO users (username, password, projects, permissions) VALUES (?, ?, ?, ?)",
                          (new_user, new_pass, '', ''))
                conn.commit()
                st.success("Usuário registrado com sucesso.")
                st.session_state.registration_mode = False
                st.session_state.registration_unlocked = False
                st.rerun()

    if st.button("Voltar ao Login"):
        st.session_state.registration_mode = False
        st.session_state.registration_unlocked = False
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
            projetos = st.multiselect(
                f"Projetos ({user})",
                options=todos_projetos,
                default=projetos_atuais.split(',') if projetos_atuais else [],
                key=f"projetos_{user}"
            )
            permissoes = st.multiselect(
                f"Permissões ({user})",
                options=["upload", "download", "view"],
                default=permissoes_atuais.split(',') if permissoes_atuais else [],
                key=f"perms_{user}"
            )
            nova_senha = st.text_input(f"Nova senha ({user})", key=f"senha_{user}")
            if st.button(f"Atualizar senha {user}"):
                c.execute("UPDATE users SET password=?, projects=?, permissions=? WHERE username=?",
                          (nova_senha, ','.join(projetos), ','.join(permissoes), user))
                conn.commit()
                st.success(f"Usuário {user} atualizado.")
                st.rerun()

    if st.button("Sair do Painel Admin"):
        st.session_state.admin_authenticated = False
        st.session_state.admin_mode = False
        st.rerun()

# AUTENTICAR ADMIN
elif st.session_state.admin_mode and not st.session_state.admin_authenticated:
    st.subheader("Autenticação do Administrador")
    master = st.text_input("Senha Mestra", type="password")
    if st.button("Liberar Painel Admin"):
        if master == "#Heisenberg7":
            st.session_state.admin_authenticated = True
            st.success("Acesso concedido.")
            st.rerun()
        else:
            st.error("Senha incorreta.")

# USUÁRIO LOGADO
elif st.session_state.authenticated:
    username = st.session_state.username
    user_data = c.execute("SELECT projects, permissions FROM users WHERE username=?", (username,)).fetchone()
    user_projects = user_data[0].split(',') if user_data and user_data[0] else []
    user_permissions = user_data[1].split(',') if user_data and user_data[1] else []

    st.sidebar.markdown(f"🔐 Logado como: **{username}**")
    if st.sidebar.button("Logout"):
        st.session_state.authenticated = False
        st.session_state.username = ""
        st.rerun()

    # UPLOAD
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
                st.success(f"Arquivo '{filename}' salvo com sucesso.")
                log_action(username, "upload", file_path)

    # VISUALIZAÇÃO E DOWNLOAD
    if "download" in user_permissions or "view" in user_permissions:
        st.markdown("### Pesquisa de Documentos")
        keyword = st.text_input("Buscar por palavra-chave")
        if keyword:
            matched = []
            for root, _, files in os.walk(BASE_DIR):
                for file in files:
                    if keyword.lower() in file.lower():
                        matched.append(os.path.join(root, file))

            if matched:
                for file in matched:
                    st.write(f"📄 {os.path.relpath(file, BASE_DIR)}")
                    with open(file, "rb") as f:
                        if file.endswith(('.jpg', '.jpeg', '.png')):
                            st.image(f.read(), caption=os.path.basename(file))
                            f.seek(0)
                        if "download" in user_permissions:
                            st.download_button("📥 Baixar", f, file_name=os.path.basename(file))
                    log_action(username, "visualizar", file)
            else:
                st.warning("Nenhum arquivo encontrado.")

    # LOG
    st.markdown("### Histórico de Ações")
    if st.checkbox("Mostrar log"):
        for row in c.execute("SELECT * FROM logs ORDER BY timestamp DESC LIMIT 50"):
            st.write(f"{row[0]} | Usuário: {row[1]} | Ação: {row[2]} | Arquivo: {row[3]}")
