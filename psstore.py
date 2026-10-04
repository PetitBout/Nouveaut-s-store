import json, os, re, smtplib, ssl, urllib.request
from email.message import EmailMessage

URL = "https://store.playstation.com/fr-fr/category/e1699f77-77e1-43ca-a296-26d08abacb0f/1"
SEEN_FILE = "seen.json"

def recuperer_jeux():
    req = urllib.request.Request(URL, headers={"User-Agent": "Mozilla/5.0", "Accept-Language": "fr-FR"})
    html = urllib.request.urlopen(req, timeout=30).read().decode("utf-8")
    m = re.search(r'<script id="__NEXT_DATA__"[^>]*>(.*?)</script>', html, re.S)
    if not m:
        return {}
    jeux = {}
    def parcourir(x):
        if isinstance(x, dict):
            if x.get("__typename") == "Product" and x.get("id") and x.get("name"):
                jeux[x["id"]] = x["name"]
            for v in x.values():
                parcourir(v)
        elif isinstance(x, list):
            for v in x:
                parcourir(v)
    parcourir(json.loads(m.group(1)))
    return jeux

def envoyer(sujet, texte):
    adresse = os.environ["GMAIL_ADDRESS"]
    mdp = os.environ["GMAIL_APP_PASSWORD"].replace(" ", "")
    msg = EmailMessage()
    msg["Subject"] = sujet
    msg["From"] = adresse
    msg["To"] = adresse
    msg.set_content(texte)
    with smtplib.SMTP_SSL("smtp.gmail.com", 465, context=ssl.create_default_context()) as s:
        s.login(adresse, mdp)
        s.send_message(msg)

jeux = recuperer_jeux()
if not jeux:
    envoyer("PS Store : problème", "Le script n'a trouvé aucun jeu. La page du store a peut-être changé.")
    raise SystemExit(1)

vus = json.load(open(SEEN_FILE)) if os.path.exists(SEEN_FILE) else []
nouveaux = {i: n for i, n in jeux.items() if i not in vus}
if nouveaux:
    texte = "\n".join("- " + n for n in list(nouveaux.values())[:50])
else:
    texte = "Rien de nouveau aujourd'hui."
envoyer(f"PS Store : {len(nouveaux)} nouveauté(s)", texte)
json.dump(list(set(vus) | set(jeux)), open(SEEN_FILE, "w"))
