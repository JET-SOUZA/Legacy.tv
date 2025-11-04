from flask import Flask, render_template, request, redirect, url_for, session, flash
import sqlite3, os, requests
from datetime import datetime, timedelta
from werkzeug.security import generate_password_hash, check_password_hash

# ==============================
# CONFIGURAÇÕES PRINCIPAIS
# ==============================
app = Flask(__name__)
app.secret_key = os.getenv("SECRET_KEY", "Jtlm@043007/Legacy.tv")

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DB_PATH = os.path.join(BASE_DIR, "database.db")

# ==============================
# BANCO DE DADOS
# ==============================
def get_db_conn():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    conn = get_db_conn()
    cur = conn.cursor()
    cur.execute("""
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT UNIQUE NOT NULL,
            password TEXT NOT NULL,
            premium INTEGER DEFAULT 0,
            is_admin INTEGER DEFAULT 0,
            expires_at TEXT DEFAULT NULL
        )
    """)
    conn.commit()
    conn.close()

init_db()

# ==============================
# CRIAR ADMIN INICIAL
# ==============================
def ensure_admin():
    admin_user = "Legacy.tv"
    admin_pass = "Jtlm@043007"
    conn = get_db_conn()
    cur = conn.cursor()
    cur.execute("SELECT * FROM users WHERE username=?", (admin_user,))
    if not cur.fetchone():
        cur.execute("INSERT INTO users (username, password, premium, is_admin) VALUES (?, ?, ?, ?)",
                    (admin_user, generate_password_hash(admin_pass), 1, 1))
        conn.commit()
    conn.close()

ensure_admin()

# ==============================
# DECORADORES DE LOGIN E PREMIUM
# ==============================
def login_required(f):
    from functools import wraps
    @wraps(f)
    def decorated(*args, **kwargs):
        if "user_id" not in session:
            flash("Faça login para continuar.")
            return redirect(url_for("login"))
        return f(*args, **kwargs)
    return decorated

def premium_required(f):
    from functools import wraps
    @wraps(f)
    def decorated(*args, **kwargs):
        if session.get("premium") != 1:
            flash("Acesso Premium necessário.")
            return redirect(url_for("index"))
        return f(*args, **kwargs)
    return decorated

# ==============================
# CARREGAR PLAYLIST DO GITHUB
# ==============================
def carregar_playlist_remota():
    url = "https://raw.githubusercontent.com/JET-SOUZA/Legacy.tv/refs/heads/main/playlist_djy7adcm_ts"
    canais = []
    try:
        r = requests.get(url, timeout=10)
        r.raise_for_status()
        linhas = r.text.splitlines()

        nome = None
        for linha in linhas:
            linha = linha.strip()
            if linha.startswith("#EXTINF:"):
                partes = linha.split(",")
                if len(partes) > 1:
                    nome = partes[1]
            elif linha.startswith("http") and nome:
                canais.append({"name": nome, "url": linha})
                nome = None
    except Exception as e:
        print("Erro ao carregar playlist:", e)
    return canais

# ==============================
# ROTAS DE AUTENTICAÇÃO
# ==============================
@app.route("/register", methods=["GET", "POST"])
def register():
    if request.method == "POST":
        username = request.form["username"].strip()
        password = request.form["password"].strip()

        if not username or not password:
            flash("Preencha todos os campos.")
            return redirect(url_for("register"))

        conn = get_db_conn()
        cur = conn.cursor()
        try:
            cur.execute("INSERT INTO users (username, password) VALUES (?, ?)",
                        (username, generate_password_hash(password)))
            conn.commit()
            flash("Conta criada com sucesso!")
            return redirect(url_for("login"))
        except sqlite3.IntegrityError:
            flash("Usuário já existe.")
        finally:
            conn.close()
    return render_template("register.html")

@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        username = request.form["username"].strip()
        password = request.form["password"].strip()

        conn = get_db_conn()
        cur = conn.cursor()
        cur.execute("SELECT * FROM users WHERE username=?", (username,))
        user = cur.fetchone()
        conn.close()

        if user and check_password_hash(user["password"], password):
            # Verifica validade
            expires_at = user["expires_at"]
            if expires_at:
                exp = datetime.strptime(expires_at, "%Y-%m-%d %H:%M:%S")
                if datetime.now() > exp:
                    flash("Sua conta expirou.")
                    return redirect(url_for("login"))

            session["user_id"] = user["id"]
            session["username"] = user["username"]
            session["premium"] = user["premium"]
            session["is_admin"] = user["is_admin"]
            flash("Login realizado com sucesso!")

            if user["is_admin"]:
                return redirect(url_for("admin_panel"))
            return redirect(url_for("index"))
        else:
            flash("Usuário ou senha incorretos.")
    return render_template("login.html")

@app.route("/logout")
def logout():
    session.clear()
    flash("Você saiu da conta.")
    return redirect(url_for("login"))

# ==============================
# ÁREA PRINCIPAL / PLAYER
# ==============================
@app.route("/")
@login_required
def index():
    canais = carregar_playlist_remota()
    return render_template("index.html", categorias=["Ao Vivo"], canais=canais)

@app.route("/player")
@login_required
@premium_required
def player():
    nome = request.args.get("name", "Canal")
    url = request.args.get("url")
    return render_template("player.html", name=nome, stream_url=url)

# ==============================
# ADMIN
# ==============================
@app.route("/admin")
@login_required
def admin_panel():
    if session.get("is_admin") != 1:
        flash("Acesso restrito ao administrador.")
        return redirect(url_for("index"))

    conn = get_db_conn()
    cur = conn.cursor()
    cur.execute("SELECT * FROM users ORDER BY id DESC")
    users = cur.fetchall()
    conn.close()

    return render_template("admin.html", users=users)

@app.route("/admin/create", methods=["POST"])
@login_required
def admin_create():
    if session.get("is_admin") != 1:
        flash("Acesso negado.")
        return redirect(url_for("index"))

    username = request.form.get("username")
    password = request.form.get("password")
    premium = 1 if request.form.get("premium") else 0
    hours = request.form.get("expires_hours")

    expires_at = None
    if hours:
        try:
            expires_at = (datetime.now() + timedelta(hours=int(hours))).strftime("%Y-%m-%d %H:%M:%S")
        except:
            expires_at = None

    conn = get_db_conn()
    cur = conn.cursor()
    try:
        cur.execute("INSERT INTO users (username, password, premium, expires_at) VALUES (?, ?, ?, ?)",
                    (username, generate_password_hash(password), premium, expires_at))
        conn.commit()
        flash("Usuário criado com sucesso!")
    except sqlite3.IntegrityError:
        flash("Usuário já existe.")
    finally:
        conn.close()
    return redirect(url_for("admin_panel"))

@app.route("/admin/delete/<int:user_id>", methods=["POST"])
@login_required
def admin_delete(user_id):
    if session.get("is_admin") != 1:
        flash("Acesso negado.")
        return redirect(url_for("index"))

    conn = get_db_conn()
    cur = conn.cursor()
    cur.execute("DELETE FROM users WHERE id=?", (user_id,))
    conn.commit()
    conn.close()
    flash("Usuário removido.")
    return redirect(url_for("admin_panel"))

# ==============================
# RODAR NO RENDER
# ==============================
if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port, debug=True)
