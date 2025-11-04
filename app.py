from flask import Flask, render_template, request, redirect, url_for, session, flash
import sqlite3, os, requests
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime

app = Flask(__name__)
app.secret_key = os.getenv("SECRET_KEY", "chave-super-secreta")

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DB_PATH = os.path.join(BASE_DIR, "database.db")

# ============================
# Banco de dados
# ============================
def get_db():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    conn = get_db()
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

# ============================
# Cria admin inicial
# ============================
def create_admin():
    conn = get_db()
    cur = conn.cursor()
    cur.execute("SELECT * FROM users WHERE username=?", ("Legacy.tv",))
    if not cur.fetchone():
        cur.execute("INSERT INTO users (username, password, premium, is_admin) VALUES (?, ?, ?, ?)",
                    ("Legacy.tv", generate_password_hash("Jtlm@043007"), 1, 1))
        conn.commit()
    conn.close()

create_admin()

# ============================
# Rotas principais
# ============================
@app.route("/")
def index():
    if "user_id" not in session:
        return redirect(url_for("login"))
    
    canais = [
        {"id": 1, "title": "Canal 1", "url": "https://test-streams.mux.dev/x36xhzz/x36xhzz.m3u8", "categoria": "Ao Vivo"},
        {"id": 2, "title": "Canal 2", "url": "https://bitdash-a.akamaihd.net/content/sintel/hls/playlist.m3u8", "categoria": "Filmes"},
    ]
    return render_template("index.html", canais=canais, titulo="Canais Disponíveis")

@app.route("/play/<int:id>")
def play(id):
    canais = [
        {"id": 1, "title": "Canal 1", "url": "https://test-streams.mux.dev/x36xhzz/x36xhzz.m3u8", "categoria": "Ao Vivo"},
        {"id": 2, "title": "Canal 2", "url": "https://bitdash-a.akamaihd.net/content/sintel/hls/playlist.m3u8", "categoria": "Filmes"},
    ]
    canal = next((c for c in canais if c["id"] == id), None)
    if not canal:
        flash("Canal não encontrado.")
        return redirect(url_for("index"))
    return render_template("player.html", canal=canal)

# ============================
# Login / Registro / Logout
# ============================
@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        username = request.form["username"].strip()
        password = request.form["password"].strip()
        conn = get_db()
        cur = conn.cursor()
        cur.execute("SELECT * FROM users WHERE username=?", (username,))
        user = cur.fetchone()
        conn.close()
        if user and check_password_hash(user["password"], password):
            session["user_id"] = user["id"]
            session["username"] = user["username"]
            flash("Login realizado com sucesso!")
            return redirect(url_for("index"))
        else:
            flash("Usuário ou senha inválidos.")
    return render_template("login.html")

@app.route("/register", methods=["GET", "POST"])
def register():
    if request.method == "POST":
        username = request.form["username"].strip()
        password = request.form["password"].strip()

        if not username or not password:
            flash("Preencha todos os campos!")
            return redirect(url_for("register"))

        conn = get_db()
        cur = conn.cursor()
        try:
            cur.execute("INSERT INTO users (username, password) VALUES (?, ?)",
                        (username, generate_password_hash(password)))
            conn.commit()
            flash("Usuário criado com sucesso!")
            return redirect(url_for("login"))
        except sqlite3.IntegrityError:
            flash("Usuário já existe.")
        finally:
            conn.close()
    return render_template("register.html")

@app.route("/logout")
def logout():
    session.clear()
    flash("Você saiu da conta.")
    return redirect(url_for("login"))

# ============================
# Admin básico
# ============================
@app.route("/admin")
def admin():
    if "user_id" not in session:
        return redirect(url_for("login"))
    
    conn = get_db()
    cur = conn.cursor()
    cur.execute("SELECT * FROM users")
    users = cur.fetchall()
    conn.close()

    return render_template("admin.html", users=users)

# ============================
# Playlist (link direto GitHub)
# ============================
@app.route("/playlist")
def playlist():
    return redirect("https://raw.githubusercontent.com/JET-SOUZA/Legacy.tv/refs/heads/main/playlist_djy7adcm_ts")

# ============================
# Run (Render)
# ============================
if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port, debug=True)
