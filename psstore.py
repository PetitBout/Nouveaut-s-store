import json, os, re, smtplib, ssl, urllib.request, urllib.error
from email.message import EmailMessage

URL = "https://store.playstation.com/fr-fr/category/e1699f77-77e1-43ca-a296-26d08abacb0f/1"
SEEN_FILE = "seen.json"

def recuperer_jeux():
    req = urllib.request.Request(URL, headers={"User-Agent": "Mozilla/5.0", "Accept-Language": "fr-FR"})
    infos = ""
    try:
        r = urllib.request.urlopen(req, timeout=30)
        html = r.read().decode("utf-8", "ignore")
        infos = f"Code: {r.status}\nAdresse finale: {r.geturl()}\nTaille: {len(html)}\n"
    except urllib.error.HTTPError as e:
        return {}, f"Erreur HTTP {e.code} : {e.reason}"
    except Exception as e:
        return {}, f"Erreur : {e}"
    m = re.search(r'<script id="__NEXT_DATA__"[^>]*>(.*?)</script>', html, re.S)
    infos += f"__NEXT_DATA__ trouvé: {bool(m)}\n"
    infos += "Début de la page:\n" + html[:300]
    if not m:
        return {}, infos
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
    return jeux, infos

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

jeux, infos = recuperer_jeux()
if not jeux:
    envoyer("PS Store : diagnostic", "Aucun jeu trouvé.\n\n" + infos)
    raise SystemExit(1)

vus = json.load(open(SEEN_FILE)) if os.path.exists(SEEN_FILE) else []
nouveaux = {i: n for i, n in jeux.items() if i not in vus}
if nouveaux:
    texte = "\n".join("- " + n for n in list(nouveaux.values())[:50])
else:
    texte = "Rien de nouveau aujourd'hui."
envoyer(f"PS Store : {len(nouveaux)} nouveauté(s)", texte)
json.dump(list(set(vus) | set(jeux)), open(SEEN_FILE, "w"))
