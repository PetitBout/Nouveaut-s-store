import json, os, time, urllib.parse, urllib.request
from datetime import datetime, timezone

CID = os.environ["TWITCH_CLIENT_ID"]
SECRET = os.environ["TWITCH_CLIENT_SECRET"]
JOURS = 14
TYPES_EXCLUS = (1, 2, 3, 5, 6, 7, 13, 14)

def jeton():
    data = urllib.parse.urlencode({"client_id": CID, "client_secret": SECRET, "grant_type": "client_credentials"}).encode()
    r = urllib.request.urlopen(urllib.request.Request("https://id.twitch.tv/oauth2/token", data=data), timeout=30)
    return json.loads(r.read())["access_token"]

def requete(token, corps):
    req = urllib.request.Request("https://api.igdb.com/v4/release_dates", data=corps.encode(),
        headers={"Client-ID": CID, "Authorization": "Bearer " + token, "Accept": "application/json"})
    return json.loads(urllib.request.urlopen(req, timeout=30).read())

token = jeton()
now = int(time.time())
corps = ("fields date,game.name,game.game_type,game.genres.name,game.aggregated_rating,game.videos.video_id,game.cover.image_id; "
         f"where date >= {now - JOURS * 86400} & date < {now + 86400} & platform = 167; sort date desc; limit 500;")
jeux = {}
for l in requete(token, corps):
    g = l.get("game")
    if not isinstance(g, dict) or g["id"] in jeux:
        continue
    t = g.get("game_type")
    if isinstance(t, dict):
        t = t.get("id")
    if t in TYPES_EXCLUS:
        continue
    cover = (g.get("cover") or {}).get("image_id")
    video = ((g.get("videos") or [{}])[0]).get("video_id")
    note = g.get("aggregated_rating")
    jeux[g["id"]] = {
        "id": g["id"],
        "nom": g.get("name", "?"),
        "date": datetime.fromtimestamp(l["date"], timezone.utc).strftime("%Y-%m-%d"),
        "genres": [x["name"] for x in g.get("genres", [])],
        "note": round(note) if note else None,
        "video": video,
        "affiche": f"https://images.igdb.com/igdb/image/upload/t_cover_big/{cover}.jpg" if cover else None,
    }
liste = sorted(jeux.values(), key=lambda j: j["date"], reverse=True)
sortie = {"maj": datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M"), "jeux": liste}
json.dump(sortie, open("games.json", "w", encoding="utf-8"), ensure_ascii=False, indent=1)
print(len(liste), "jeux")
