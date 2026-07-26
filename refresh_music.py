import json
import sqlite3
import urllib.parse
import urllib.request
from datetime import datetime
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent
DB_PATH = BASE_DIR / "db" / "room64.db"
API_URL = "http://127.0.0.1:8000/api/search_singer?" + urllib.parse.urlencode({"name": "杨丞琳"})

with sqlite3.connect(DB_PATH) as con:
    con.execute("UPDATE music_search_cache SET updated_at = 0 WHERE query LIKE 'provider-v2:%' OR query LIKE 'multi-platform-v4:%'")
    con.commit()

with urllib.request.urlopen(API_URL, timeout=60) as response:
    payload = json.loads(response.read().decode("utf-8"))

songs = payload.get("data", {}).get("song", {}).get("list", [])
if payload.get("code") != 0 or not songs:
    raise RuntimeError("song catalog refresh returned no usable songs")

providers = payload.get("data", {}).get("_providers", {})
print(f"{datetime.now().isoformat(timespec='seconds')} refreshed {len(songs)} songs providers={providers}")