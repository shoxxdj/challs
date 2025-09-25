# app.py
from flask import Flask, request, render_template_string, Response
import pickle, base64, re, os, random
import random
from cryptography.hazmat.primitives.ciphers import Cipher, algorithms, modes
from cryptography.hazmat.backends import default_backend
from cryptography.hazmat.primitives import hashes, padding
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC

app = Flask(__name__)

# Flag côté serveur
FLAG = "hkdmb{use_good_keys}"

def get_random_secret(filename="harry-potter.txt") -> str:
    try:
        with open(filename, "r", encoding="utf-8", errors="ignore") as f:
            words = [line.strip() for line in f if line.strip()]
        if not words:
            raise ValueError("Fichier harry-potter.txt vide")
        return random.choice(words)
    except Exception as e:
        # fallback si fichier absent
        return "defaultpassword"

SECRET_WORD = get_random_secret("harry-potter.txt")
print(SECRET_WORD)

# --- Template HTML joli ---
TEMPLATE = """
<!doctype html>
<html lang="fr">
<head>
    <meta charset="utf-8">
    <title>ViewState Priv Esc</title>
    <style>
        body { font-family: Arial, sans-serif; background: #f4f4f9; color: #333; text-align: center; padding: 50px; }
        h1 { color: #444; }
        a { text-decoration: none; color: #2c7; font-weight: bold; }
        form { margin-top: 30px; background: #fff; display: inline-block; padding: 30px; border-radius: 10px; box-shadow: 0 4px 10px rgba(0,0,0,0.1); }
        input[type="submit"] { background-color: #2c7; color: white; border: none; padding: 10px 25px; font-size: 16px; border-radius: 5px; cursor: pointer; transition: 0.2s; }
        input[type="submit"]:hover { background-color: #28a745; }
        .note { font-size: 0.9em; color: #666; margin-top: 10px; }
    </style>
</head>
<body>
    <h1>ViewState Privilege Escalation</h1>
    <a href="/source">Voir le code source</a>
    <br/>
    <p>Cette fois nous chiffrons le viewstate !</p>
    <br/>
    <i>TODO: implémenter un salt pour plus de sécurité</i>
    <hr/>
    <form method="post">
        <input type="hidden" name="viewstate" value="{{ viewstate }}">
        <input type="submit" value="Continuer">
        <div class="note">Essayez de manipuler le viewstate pour devenir admin !</div>
    </form>
</body>
</html>
"""

# --- Fonctions de chiffrement / déchiffrement AES CBC ---
SALT = str(random.randint(10, 99)).encode() 
print(SALT)
def derive_key(secret: str) -> bytes:
    """Dérive une clé AES 256 à partir du mot secret sans salt."""
    kdf = PBKDF2HMAC(
        algorithm=hashes.SHA256(),
        length=32,
        salt=SALT,
        iterations=100_000,
        backend=default_backend()
    )
    return kdf.derive(secret.encode())

def encrypt(data: bytes) -> str:
    key = derive_key(SECRET_WORD)
    iv = os.urandom(16)
    cipher = Cipher(algorithms.AES(key), modes.CBC(iv), backend=default_backend())
    encryptor = cipher.encryptor()
    padder = padding.PKCS7(128).padder()
    padded_data = padder.update(data) + padder.finalize()
    ct = encryptor.update(padded_data) + encryptor.finalize()
    return base64.b64encode(iv + ct).decode()

def decrypt(enc_data: str) -> bytes:
    raw = base64.b64decode(enc_data)
    iv, ct = raw[:16], raw[16:]
    key = derive_key(SECRET_WORD)
    cipher = Cipher(algorithms.AES(key), modes.CBC(iv), backend=default_backend())
    decryptor = cipher.decryptor()
    padded_data = decryptor.update(ct) + decryptor.finalize()
    unpadder = padding.PKCS7(128).unpadder()
    data = unpadder.update(padded_data) + unpadder.finalize()
    return data

# --- Routes Flask ---
@app.route("/", methods=["GET", "POST"])
def index():
    if request.method == "POST":
        data = request.form.get("viewstate", "")
        try:
            raw = decrypt(data)
            obj = pickle.loads(raw)
        except Exception as e:
            return f"<p>Erreur de désérialisation ou déchiffrement: {e}</p>"

        if isinstance(obj, dict) and obj.get("is_admin") is True:
            return f"<h2>Bienvenue admin — FLAG: {FLAG}</h2>"
        else:
            return f"<h2>Bienvenue {obj.get('user', 'guest')} — accès restreint.</h2>"

    else:
        state = {"user": "guest"}
        raw = pickle.dumps(state)
        viewstate = encrypt(raw)
        return render_template_string(TEMPLATE, viewstate=viewstate)

@app.route("/source", methods=["GET"])
def view_source():
    path = os.path.abspath(__file__)
    try:
        with open(path, "r", encoding="utf-8") as f:
            src = f.read()
    except Exception as e:
        return Response(f"Impossible de lire le fichier source: {e}", status=500, mimetype="text/plain")

    redacted_src = re.sub(
        r'^(FLAG\s*=\s*).*$',
        r'FLAG = "<REDACTED_FOR_PARTICIPANTS>"',
        src,
        flags=re.MULTILINE
    )
    return Response(redacted_src, mimetype="text/plain")

@app.route("/harry-potter.txt", methods=["GET"])
def serve_harry_potter():
    path = os.path.abspath("harry-potter.txt")
    if not os.path.exists(path):
        return Response("Fichier harry-potter.txt introuvable", status=404, mimetype="text/plain")
    try:
        with open(path, "r", encoding="utf-8", errors="ignore") as f:
            content = f.read()
        return Response(content, mimetype="text/plain")
    except Exception as e:
        return Response(f"Impossible de lire le fichier: {e}", status=500, mimetype="text/plain")


if __name__ == "__main__":
    app.run(host="127.0.0.1", port=5000, debug=False)

