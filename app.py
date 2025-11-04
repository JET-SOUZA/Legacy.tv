from flask import Flask, render_template, request, redirect, url_for, session, g, flash
import sqlite3
import os
import requests

app = Flask(__name__)
app.secret_key = "legacytv_secret_2025"

# =====================================================
# 🔹 CONFIGURAÇÃO DO BANCO DE DADOS (compatível com Render)
# =====================================================
os.makedirs("/tmp/db", exist_ok=True)
DB_PATH = "/tmp/db/users.db"

def get_db():
    if "db" not in g:
        g.db = sqlite3.connect(DB_PATH)
        g.db.row_factory = sqlite3.Row
    return g.db

@app.teardown_appcontext
def close_db(error):
    db = g.pop("db", None)
    if db is not None:
        db.close()

def init_db():
    with app.app_context():
        db = get_db()
        db.execute(
            """CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                username TEXT UNIQUE NOT NULL,
                password TEXT NOT NULL
            )"""
        )
        db.commit()

init_db()

# --- Cria admin padrão se não existir ---
def create_admin():
    with app.app_context():
        db = get_db()
        admin = db.execute("SELECT * FROM users WHERE username = ?", ("admin",)).fetchone()
        if not admin:
            db.execute("INSERT INTO users (username, password) VALUES (?, ?)", ("admin", "admin123"))
            db.commit()
            print("✅ Usuário admin criado com sucesso (admin / admin123)")

create_admin()

# =====================================================
# 🔹 PLAYLIST M3U
# =====================================================
PLAYLIST_URL = "https://raw.githubusercontent.com/JET-SOUZA/Legacy.tv/refs/heads/main/playlist_djy7adcm_ts"

def carregar_canais():
    canais = []
    try:
        r = requests.get(PLAYLIST_URL, timeout=10)
        if r.status_code == 200:
            linhas = r.text.splitlines()
            canal = {}
            for linha in linhas:
                if linha.startswith("#EXTINF"):
                    nome = linha.split(",")[-1].strip()
                    canal["name"] = nome
                elif linha.startswith("http"):
                    canal["url"] = linha.strip()
                    canal["id"] = len(canais) + 1
                    canais.append(canal)
                    canal = {}
    except Exception as e:
        print("❌ Erro ao carregar playlist:", e)
    return canais

canais = carregar_canais()

# =====================================================
# 🔹 ROTAS DE LOGIN / REGISTRO
# =====================================================
@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        username = request.form["username"]
        password = request.form["password"]

        db = get_db()
        user = db.execute(
            "SELECT * FROM users WHERE username = ? AND password = ?",
            (username, password)
        ).fetchone()

        if user:
            session["user"] = username
            return redirect(url_for("index"))
        else:
            return "Usuário ou senha incorretos."

    return render_template("login.html")


@app.route("/register", methods=["GET", "POST"])
def register():
    if request.method == "POST":
        username = request.form["username"]
        password = request.form["password"]

        db = get_db()
        try:
            db.execute("INSERT INTO users (username, password) VALUES (?, ?)", (username, password))
            db.commit()
            flash("Usuário criado com sucesso! Faça login.")
            return redirect(url_for("login"))
        except sqlite3.IntegrityError:
            flash("Nome de usuário já existe.")
            return redirect(url_for("register"))

    return render_template("register.html")


@app.route("/logout")
def logout():
    session.pop("user", None)
    flash("Você saiu da conta.")
    return redirect(url_for("login"))


# =====================================================
# 🔹 ROTAS PRINCIPAIS
# =====================================================
@app.route("/")
def index():
    if "user" not in session:
        return redirect(url_for("login"))
    return render_template("index.html", canais=canais, titulo="Canais Disponíveis")


@app.route("/play/<int:id>")
def play(id):
    if "user" not in session:
        return redirect(url_for("login"))

    canal = next((c for c in canais if c["id"] == id), None)
    if not canal:
        flash("Canal não encontrado.")
        return redirect(url_for("index"))
    return render_template("player.html", canal=canal)


@app.route("/reload")
def reload_playlist():
    if "user" not in session:
        return redirect(url_for("login"))

    global canais
    canais = carregar_canais()
    flash("Playlist recarregada com sucesso.")
    return redirect(url_for("index"))


# =====================================================
# 🔹 STATUS (API)
# =====================================================
@app.route("/status")
def status():
    return {"ok": True, "total_canais": len(canais)}


# =====================================================
# 🔹 EXECUÇÃO LOCAL
# =====================================================
if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.getenv("PORT", 10000)), debug=True)
