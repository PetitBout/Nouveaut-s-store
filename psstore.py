import json, os, re, smtplib, ssl, urllib.request
from collections import Counter
from email.message import EmailMessage

URL = "https://store.playstation.com/fr-fr/category/e1699f77-77e1-43ca-a296-26d08abacb0f/1"
SEEN_FILE = "seen.json"

def recuperer_jeux():
    req = urllib.request.Request(URL, headers={"User-Agent": "Mozilla/5.0", "Accept-Language": "fr-FR"})
    try:
        html = urllib.request.urlopen(req, timeout=30).read().decode("utf-8", "ignore")
    except Exception as e:
        return {}, f"Erreur : {e}"
    m = re.search(r'<script id="__NEXT_DATA__"[^>]*>(.*?)</script>', html, re.S)
    if not m:
        return {}, "Pas de __NEXT_DATA__"
    data = json.loads(m.group(1))
    jeux, types, exemples, apollo = {}, Counter(), [], []
    def parcourir(x):
        if isinstance(x, dict):
            t = x.get("__typename")
            if t:
                types[t] += 1
            if t and x.get("id") and isinstance(x.get("name"), str):
                if len(exemples) < 5:
                    exemples.append(f"{t} | {x['id']} | {x['name']}")
                if "Product" in t or "Concept" in t:
                    jeux[x["id"]] = x["name"]
            if "apolloState" in x and isinstance(x["apolloState"], dict) and not apollo:
                apollo.extend(list(x["apolloState"].keys())[:10])
            for v in x.values():
                parcourir(v)
        elif isinstance(x, list):
            for v in x:
                parcourir(v)
    parcourir(data)
    infos = f"Taille JSON: {len(m.group(1))}\n"
    infos += f"Clés racine: {list(data.keys())[:10]}\n"
    infos += f"Types trouvés: {types.most_common(15)}\n"
    infos += f"Exemples: {exemples}\n"
    infos += f"Clés apolloState: {apollo}\n"
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
    envoyer("PS Store : diagnostic 2", "Aucun jeu trouvé.\n\n" + infos)
    raise SystemExit(1)

vus = json.load(open(SEEN_FILE)) if os.path.exists(SEEN_FILE) else []
nouveaux = {i: n for i, n in jeux.items() if i not in vus}
if nouveaux:
    texte = "\n".join("- " + n for n in list(nouveaux.values())[:50])
else:
    texte = "Rien de nouveau aujourd'hui."
envoyer(f"PS Store : {len(nouveaux)} nouveauté(s)", texte)
json.dump(list(set(vus) | set(jeux)), open(SEEN_FILE, "w"))
