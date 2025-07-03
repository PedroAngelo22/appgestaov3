import os
import shutil
from datetime import datetime
import streamlit as st
import sqlite3

# Banco de dados SQLite para controle de usuários e histórico
conn = sqlite3.connect('document_manager.db', check_same_thread=False)
c = conn.cursor()
c.execute('''CREATE TABLE IF NOT EXISTS users (username TEXT PRIMARY KEY, password TEXT, projects TEXT, permissions TEXT)''')
c.execute('''CREATE TABLE IF NOT EXISTS logs (timestamp TEXT, user TEXT, action TEXT, file TEXT)''')
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

# Interface de login ou registro protegido
st.title("Gerenciador de Documentos Inteligente")

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

# Tela de login principal
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

# Tela de autenticação do administrador
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

# Painel Administrativo com funcionalidades futuras
elif st.session_state.admin_mode and st.session_state.admin_authenticated:
    st.subheader("Painel Administrativo")
    usuarios = c.execute("SELECT username, permissions FROM users").fetchall()
    filtro = st.text_input("🔍 Filtrar usuários por nome")
    usuarios = [u for u in usuarios if filtro.lower() in u[0].lower()] if filtro else usuarios
    for u in usuarios:
        user, permissoes_atuais = u
        st.markdown(f"#### 👤 {user}")
        col1, col2 = st.columns([1, 2])
        with col1:
            if st.button(f"Excluir {user}"):
                c.execute("DELETE FROM users WHERE username=?", (user,))
                conn.commit()
                st.success(f"Usuário {user} removido.")
                st.rerun()
        with col2:
            nova_senha = st.text_input(f"Nova senha ({user})", key=f"senha_{user}")
        user_data = c.execute("SELECT projects FROM users WHERE username=?", (user,)).fetchone()
        projetos_atuais = user_data[0].split(",") if user_data and user_data[0] else []
        todos_projetos = [p for p in os.listdir(BASE_DIR) if os.path.isdir(os.path.join(BASE_DIR, p))]
        projetos_selecionados = st.multiselect(f"Projetos ({user})", options=todos_projetos, default=projetos_atuais, key=f"projetos_{user}")
                    permissoes = st.multiselect(
            f"Permissões ({user})",
            options=["upload", "download", "view"],
            default=permissoes_atuais.split(',') if permissoes_atuais else [],
            key=f"perms_{user}"
        )
