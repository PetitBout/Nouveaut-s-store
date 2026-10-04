import json, os, smtplib, ssl, time, urllib.error, urllib.parse, urllib.request
from datetime import datetime, timezone
from email.message import EmailMessage

CID = os.environ["TWITCH_CLIENT_ID"]
SECRET = os.environ["TWITCH_CLIENT_SECRET"]
TYPES_EXCLUS = (1, 2, 3, 5, 6, 7, 13, 14)

def jeton():
    data = urllib.parse.urlencode({"client_id": CID, "client_secret": SECRET, "grant_type": "client_credentials"}).encode()
    r = urllib.request.urlopen(urllib.request.Request("https://id.twitch.tv/oauth2/token", data=data), timeout=30)
    return json.loads(r.read())["access_token"]

def requete(token, corps):
    req = urllib.request.Request("https://api.igdb.com/v4/release_dates", data=corps.encode(),
        headers={"Client-ID": CID, "Authorization": "Bearer " + token, "Accept": "application/json"})
    return json.loads(urllib.request.urlopen(req, timeout=30).read())

def principal():
    token = jeton()
    now = int(time.time())
    debut, fin = now - 7 * 86400, now + 86400
    corps = ("fields date,platform.abbreviation,game.name,game.game_type,game.genres.name,game.aggregated_rating,game.videos.video_id; "
             f"where date >= {debut} & date < {fin} & platform = 167; sort date desc; limit 200;")
    jeux = {}
    retires = set()
    for l in requete(token, corps):
        g = l.get("game")
        if not isinstance(g, dict):
            continue
        t = g.get("game_type")
        if isinstance(t, dict):
            t = t.get("id")
        if t in TYPES_EXCLUS:
            retires.add(g["id"])
            continue
        e = jeux.setdefault(g["id"], {"nom": g.get("name", "?"), "date": l["date"], "pf": set(),
            "genres": [x["name"] for x in g.get("genres", [])], "note": g.get("aggregated_rating"),
            "video": ((g.get("videos") or [{}])[0]).get("video_id")})
        e["pf"].add((l.get("platform") or {}).get("abbreviation", "?"))
    liste = sorted(jeux.values(), key=lambda e: -e["date"])
    stats = (f"{len(liste)} jeux PS5 sur 7 jours (sans DLC)\n"
             f"DLC, extensions et packs retirés : {len(retires)}\n"
             f"avec genres : {sum(1 for e in liste if e['genres'])}\n"
             f"avec note presse : {sum(1 for e in liste if e['note'])}\n"
             f"avec trailer : {sum(1 for e in liste if e['video'])}\n\n")
    lignes = []
    for e in liste[:40]:
        d = datetime.fromtimestamp(e["date"], timezone.utc).strftime("%d/%m/%Y")
        note = round(e["note"]) if e["note"] else "-"
        tr = "https://youtu.be/" + e["video"] if e["video"] else "pas de trailer"
        lignes.append(f"- {e['nom']} ({d}) | {', '.join(e['genres']) or '-'} | note {note} | {tr}")
    return f"IGDB : {len(liste)} jeux", stats + "\n".join(lignes)

def envoyer(sujet, texte):
    adresse = os.environ["GMAIL_ADDRESS"]
    msg = EmailMessage()
    msg["Subject"], msg["From"], msg["To"] = sujet, adresse, adresse
    msg.set_content(texte)
    with smtplib.SMTP_SSL("smtp.gmail.com", 465, context=ssl.create_default_context()) as s:
        s.login(adresse, os.environ["GMAIL_APP_PASSWORD"].replace(" ", ""))
        s.send_message(msg)

try:
    sujet, texte = principal()
except urllib.error.HTTPError as e:
    sujet, texte = "IGDB : erreur", f"Erreur HTTP {e.code}\n{e.read().decode('utf-8', 'ignore')[:500]}"
except Exception as e:
    sujet, texte = "IGDB : erreur", str(e)
envoyer(sujet, texte)
