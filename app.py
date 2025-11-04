import os, sqlite3, requests
from flask import Flask, render_template, request, redirect, url_for, flash
from datetime import datetime

app = Flask(__name__)
app.secret_key = os.getenv("SECRET_KEY", "LegacySecretKey")

# ================================
# CONFIGURAÇÃO DO BANCO
# ================================
DB_PATH = os.path.join(os.path.dirname(__file__), "database.db")

def get_db_conn():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

# ================================
# INICIALIZAÇÃO DO BANCO
# ================================
def init_db():
    conn = get_db_conn()
    cursor = conn.cursor()
    cursor.execute("""
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

# ================================
# FUNÇÃO PARA CARREGAR PLAYLIST .M3U
# ================================
PLAYLIST_URL = "https://raw.githubusercontent.com/JET-SOUZA/Legacy.tv/refs/heads/main/playlist_djy7adcm_ts"

def carregar_canais():
    canais = []
    try:
        r = requests.get(PLAYLIST_URL, timeout=10)
        r.raise_for_status()
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

# ================================
# ROTAS PRINCIPAIS
# ================================
@app.route("/")
def index():
    return render_template("index.html", canais=canais, titulo="Canais Disponíveis")

@app.route("/play/<int:id>")
def play(id):
    canal = next((c for c in canais if c["id"] == id), None)
    if not canal:
        flash("Canal não encontrado.")
        return redirect(url_for("index"))
    return render_template("player.html", canal=canal)

@app.route("/play")
def play_default():
    """Se o usuário acessar /play direto, abre o primeiro canal disponível."""
    if canais:
        return redirect(url_for("play", id=canais[0]["id"]))
    flash("Nenhum canal disponível.")
    return redirect(url_for("index"))

@app.route("/reload")
def reload_playlist():
    """Recarrega a playlist manualmente"""
    global canais
    canais = carregar_canais()
    flash("Playlist recarregada com sucesso.")
    return redirect(url_for("index"))

# ================================
# ROTA DE STATUS
# ================================
@app.route("/status")
def status():
    return {"ok": True, "total_canais": len(canais), "ultima_atualizacao": str(datetime.now())}

# ================================
# EXECUÇÃO LOCAL
# ================================
if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.getenv("PORT", 5000)), debug=True)
