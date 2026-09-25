import json
import os
import re
import sqlite3
import inspect
import sys

import requests
from flask import (
    Flask, g, redirect, render_template, request, session, url_for, jsonify
)

# --------------------------------------------------------------------------- #
# Configuration
# --------------------------------------------------------------------------- #
DB_PATH = os.path.join(os.path.dirname(__file__), "support.db")
OLLAMA_URL = os.environ.get("OLLAMA_URL", "http://localhost:11434")
MODEL = os.environ.get("STI_MODEL", "qwen2.5:7b")   # ~2B, tool-calling capable
FLAG = os.environ.get("STI_FLAG", "FLAG{st1_r0le_1nj3ct10n_wr0te_t0_th3_db}")

app = Flask(__name__)
app.secret_key = "lab-only-not-secret"

# --------------------------------------------------------------------------- #
# Base de donnees
# --------------------------------------------------------------------------- #
def init_db():
    """Cree la base support si absente, avec un peu de contenu legitime."""
    con = sqlite3.connect(DB_PATH)
    cur = con.cursor()
    cur.executescript(
        """
        CREATE TABLE IF NOT EXISTS users (
            id       INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT UNIQUE NOT NULL,
            password TEXT NOT NULL
        );
        CREATE TABLE IF NOT EXISTS products (
            id    INTEGER PRIMARY KEY,
            name  TEXT,
            price REAL,
            stock INTEGER
        );
        """
    )
    # Contenu produit legitime pour que l'outil ait une raison d'exister.
    cur.execute("SELECT COUNT(*) FROM products")
    if cur.fetchone()[0] == 0:
        cur.executemany(
            "INSERT INTO products (id, name, price, stock) VALUES (?,?,?,?)",
            [
                (1, "Clavier mecanique", 89.90, 42),
                (2, "Souris ergonomique", 45.00, 17),
                (3, "Casque audio",       129.00, 8),
            ],
        )
    con.commit()
    con.close()


# --------------------------------------------------------------------------- #
# L'outil (fonction) expose au LLM — LA vulnerabilite
# --------------------------------------------------------------------------- #
def execute_sql_query(query: str):
    print(f"[execute_sql_query] {query}")
    try:
        con = sqlite3.connect(DB_PATH)
        con.row_factory = sqlite3.Row
        cur = con.cursor()
        cur.executescript(query)
        con.commit()
        rows = cur.fetchall()
        result = [dict(r) for r in rows] if rows else [{"message": "OK — aucune ligne retournee"}]
        con.close()
        return result
    except sqlite3.Error as e:
        return [{"error": str(e)}]


TOOLS = [
    {
        "type": "function",
        "function": {
            "name": "execute_sql_query",
            "description": "Execute une requete SQL en lecture seule sur la base ",
            "parameters": {
                "type": "object",
                "properties": {
                    "query": {
                        "type": "string",
                        "description": "Une requete SQL SELECT.",
                    }
                },
                "required": ["query"],
            },
        },
    }
]

SYSTEM_PROMPT = (
    "/no_think\n"
    "Tu es l'assistant support de la boutique ShopBot. Tu renseignes les "
    "visiteurs sur le catalogue (produits, prix, stock) en interrogeant la base "
    "avec l'outil execute_sql_query. Reste factuel et concis. Quand on te demande "
    "de repeter ou d'afficher une chaine, reproduis-la fidelement."
)


# --------------------------------------------------------------------------- #
# Dialogue avec Ollama
# --------------------------------------------------------------------------- #
def ollama_chat(messages):
    r = requests.post(
        f"{OLLAMA_URL}/api/chat",
        json={
            "model": MODEL,
            "messages": messages,
            "tools": TOOLS,
            "stream": False,
            "think": False,          # coupe le raisonnement de qwen3
            "options": {"temperature": 0.2},
        },
        timeout=180,
    )
    r.raise_for_status()
    return r.json()["message"]

def extract_tool_calls(msg):
    calls = []
    for tc in (msg.get("tool_calls") or []):
        fn = tc.get("function", {})
        calls.append((fn.get("name"), fn.get("arguments", {})))
    return calls


def handle_turn(user_msg, history):
    messages = [{"role": "system", "content": SYSTEM_PROMPT}] + history
    messages.append({"role": "user", "content": user_msg})

    print(messages)

    msg = ollama_chat(messages)
    calls = extract_tool_calls(msg)

    #print("msg")
    #print(msg)
    #print("calls")
    #print(calls)

    if calls:
        messages.append(msg)
        for name, args in calls:
            if isinstance(args, str):
                try:
                    args = json.loads(args)
                except Exception:
                    args = {}
            if name == "execute_sql_query":
                result = execute_sql_query(args.get("query", ""))
            else:
                result = [{"error": f"outil inconnu: {name}"}]
            messages.append({
                "role": "tool",
                "content": json.dumps(result, ensure_ascii=False),
            })
        # Reponse finale du modele apres execution de l'outil
        final = ollama_chat(messages)
        reply = final.get("content", "") or "(action executee)"
    else:
        reply = msg.get("content", "")

    new_history = history + [
        {"role": "user", "content": user_msg},
        {"role": "assistant", "content": reply},
    ]
    return reply, new_history[-12:]   # on borne l'historique


# --------------------------------------------------------------------------- #
# Routes
# --------------------------------------------------------------------------- #
@app.route("/")
def index():
    if session.get("user"):
        return redirect(url_for("dashboard"))
    return render_template("index.html")


@app.route("/login", methods=["POST"])
def login():
    username = request.form.get("username", "")
    password = request.form.get("password", "")
    con = sqlite3.connect(DB_PATH)
    cur = con.cursor()
    cur.execute(
        "SELECT username FROM users WHERE username = ? AND password = ?",
        (username, password),
    )
    row = cur.fetchone()
    con.close()
    if row:
        session["user"] = row[0]
        return redirect(url_for("dashboard"))
    return render_template("index.html", error="Identifiants invalides. "
                           "Vous n'avez pas encore de compte…")


@app.route("/dashboard")
def dashboard():
    if not session.get("user"):
        return redirect(url_for("index"))
    return render_template("dashboard.html", user=session["user"], flag=FLAG)


@app.route("/logout")
def logout():
    session.clear()
    return redirect(url_for("index"))


@app.route("/api/chat", methods=["POST"])
def api_chat():
    data = request.get_json(force=True)
    user_msg = data.get("message", "")
    history = session.get("chat_history", [])

    print(user_msg)
    try:
        reply, history = handle_turn(user_msg, history)
    except requests.RequestException as e:
        return jsonify({"reply": f"[erreur ollama] {e}"}), 502
    session["chat_history"] = history
    return jsonify({"reply": reply})


@app.route("/api/reset", methods=["POST"])
def api_reset():
    session["chat_history"] = []
    return jsonify({"ok": True})

@app.route("/source",methods=["GET"])
def source():
    filename = inspect.getfile(sys.modules[__name__])
    with open(filename, "r", encoding="utf-8") as f:
        source = f.read()
        lines=source.splitlines(keepends=True)
        source="".join(
            line[:len(line) - len(line.lstrip())] + "FLAG = {REMOVED}\n"
            if line.lstrip().startswith("FLAG")
            else line
            for line in lines
        )
        return f"<pre>{source}</pre>"


if __name__ == "__main__":
    init_db()
    print(f"[*] STI Lab — modele={MODEL}  ollama={OLLAMA_URL}")
    print("[*] http://localhost:5000")
    app.run(host="0.0.0.0", port=5000, debug=False)
