# app.py
from flask import Flask, request, render_template_string,Response
import pickle, base64, re, os

app = Flask(__name__)

# Flag stocké côté serveur (non envoyé dans le viewstate initial)
FLAG ="hkdmb{viewstates_are_dangerous}"

TEMPLATE = """
<!doctype html>
<html lang="fr">
<head>
    <meta charset="utf-8">
    <title>ViewState Priv Esc</title>
    <style>
        body {
            font-family: Arial, sans-serif;
            background: #f4f4f9;
            color: #333;
            text-align: center;
            padding: 50px;
        }
        h1 {
            color: #444;
        }
        a {
            text-decoration: none;
            color: #2c7;
            font-weight: bold;
        }
        form {
            margin-top: 30px;
            background: #fff;
            display: inline-block;
            padding: 30px;
            border-radius: 10px;
            box-shadow: 0 4px 10px rgba(0,0,0,0.1);
        }
        input[type="submit"] {
            background-color: #2c7;
            color: white;
            border: none;
            padding: 10px 25px;
            font-size: 16px;
            border-radius: 5px;
            cursor: pointer;
            transition: 0.2s;
        }
        input[type="submit"]:hover {
            background-color: #28a745;
        }
        .note {
            font-size: 0.9em;
            color: #666;
            margin-top: 10px;
        }
    </style>
</head>
<body>
    <h1>ViewState Privilege Escalation</h1>
    <a href="/source">Voir le code source</a>
    <br/>
    <form method="post">
        <input type="hidden" name="viewstate" value="{{ viewstate }}">
        <input type="submit" value="Continuer">
        <div class="note">Essayez de manipuler le viewstate pour devenir admin !</div>
    </form>
</body>
</html>
"""

@app.route("/", methods=["GET", "POST"])
def index():
    if request.method == "POST":
        data = request.form.get("viewstate", "")
        try:
            obj = pickle.loads(base64.b64decode(data))
        except Exception as e:
            return f"Erreur de désérialisation: {e}"

        # Le serveur fait confiance au champ is_admin — vulnérabilité pédagogique.
        if isinstance(obj, dict) and obj.get("is_admin") is True:
            return f"Bienvenue admin — FLAG: {FLAG}"
        else:
            return f"Bienvenue {obj.get('user', 'guest')} — accès restreint."

    else:
        # état initial : pas d'is_admin, pas de flag côté client
        state = {"user": "guest"}
        viewstate = base64.b64encode(pickle.dumps(state)).decode()
        return render_template_string(TEMPLATE, viewstate=viewstate)

@app.route("/source", methods=["GET"])
def view_source():
    path = os.path.abspath(__file__)  # chemin du fichier courant (app.py)
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

if __name__ == "__main__":
    app.run(host="127.0.0.1", port=5000, debug=False)

