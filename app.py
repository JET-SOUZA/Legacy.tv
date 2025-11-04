from flask import Flask, render_template, request, redirect, url_for, session, g
import sqlite3
import os

app = Flask(__name__)
app.secret_key = "legacytv_secret_2025"

# Caminho do banco SQLite
DB_PATH = os.path.join(os.path.dirname(__file__), "users.db")

# -------- Função para conectar ao banco --------
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

# -------- Inicializa o banco se não existir --------
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

# -------- Página inicial --------
@app.route("/")
def index():
    if "user_id" not in session:
        return redirect(url_for("login"))
    
    # Exemplo de lista de canais (pode ser carregada de uma M3U)
    canais = [
        {"id": 1, "nome": "Canal Esportes", "link": "https://example.com/stream1.m3u8"},
        {"id": 2, "nome": "Canal Filmes", "link": "https://example.com/stream2.m3u8"},
        {"id": 3, "nome": "Canal Séries", "link": "https://example.com/stream3.m3u8"},
    ]
    return render_template("index.html", canais=canais)

# -------- Página de player --------
@app.route("/play/<int:canal_id>")
def play(canal_id):
    if "user_id" not in session:
        return redirect(url_for("login"))
    
    canais = [
        {"id": 1, "nome": "Canal Esportes", "link": "https://example.com/stream1.m3u8"},
        {"id": 2, "nome": "Canal Filmes", "link": "https://example.com/stream2.m3u8"},
        {"id": 3, "nome": "Canal Séries", "link": "https://example.com/stream3.m3u8"},
    ]
    canal = next((c for c in canais if c["id"] == canal_id), None)
    return render_template("player.html", canal=canal)

# -------- Página de registro --------
@app.route("/register", methods=["GET", "POST"])
def register():
    if request.method == "POST":
        username = request.form["username"]
        password = request.form["password"]

        db = get_db()
        try:
            db.execute("INSERT INTO users (username, password) VALUES (?, ?)", (username, password))
            db.commit()
            return redirect(url_for("login"))
        except sqlite3.IntegrityError:
            return "Usuário já existe!"

    return render_template("register.html")

# -------- Página de login --------
@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        username = request.form["username"]
        password = request.form["password"]

        db = get_db()
        user = db.execute(
            "SELECT * FROM users WHERE username = ? AND password = ?", (username, password)
        ).fetchone()

        if user:
            session["user_id"] = user["id"]
            session["username"] = user["username"]
            return redirect(url_for("index"))
        else:
            return "Usuário ou senha incorretos."

    return render_template("login.html")

# -------- Logout --------
@app.route("/logout")
def logout():
    session.clear()
    return redirect(url_for("login"))

# -------- Healthcheck --------
@app.route("/health")
def health():
    return {"ok": True}

# -------- Execução --------
if __name__ == "__main__":
    app.run(host="0.0.0.0", port=10000)
