import sqlite3
import datetime
import time
import base64
import re
import secrets
import string
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path
from flask import Flask, send_from_directory, jsonify, request
import urllib.request
import urllib.parse
import json

import logging
from Crypto.Cipher import AES
from Crypto.PublicKey import RSA

# 复用或重新配置日志 (为了确保 app.py 也能打日志)
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler("server.log", encoding='utf-8'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger("app")

BASE_DIR = Path(__file__).resolve().parent
DB_PATH = BASE_DIR / "db" / "room64.db"
SCHEMA_PATH = BASE_DIR / "db" / "schema.sql"
TOURS_JSON_PATH = BASE_DIR / "db" / "tours.json"
QQ_SEARCH_URL = "https://c.y.qq.com/splcloud/fcgi-bin/smartbox_new.fcg"
NETEASE_SEARCH_URL = "https://music.163.com/weapi/cloudsearch/pc"
KUGOU_SEARCH_URL = "https://songsearch.kugou.com/song_search_v2"
SEARCH_CACHE_TTL_SECONDS = 12 * 60 * 60
LYRICS_CACHE_TTL_SECONDS = 7 * 24 * 60 * 60
NETEASE_AES_IV = b"0102030405060708"
NETEASE_PRESET_KEY = b"0CoJUm6Qyw8W8jud"
NETEASE_PUBLIC_KEY = b"""-----BEGIN PUBLIC KEY-----
MIGfMA0GCSqGSIb3DQEBAQUAA4GNADCBiQKBgQDgtQn2JZ34ZC28NWYpAUd98iZ37BUrX/aKzmFbt7clFSs6sXqHauqKWqdtLkF2KexO40H1YTX8z2lSgBBOAxLsvaklV8k4cBFK9snQXE9/DDaFt6Rr7iVZMldczhC0JNgTz+SHXT6CBHuX3e9SdB1Ua44oncaTWz7OBGLbCiK45wIDAQAB
-----END PUBLIC KEY-----"""

app = Flask(__name__, static_folder="static", static_url_path="/static")


def build_fallback_search_payload(name: str):
    """Return a local fallback payload so /music remains usable when proxy is down."""
    singer_name = name or "杨丞琳"
    fallback_songs = [
        {
            "songmid": "fallback_001",
            "songname": "年轮说",
            "albumname": "年轮说",
            "albummid": "fallback_album_001",
            "time_public": "2016-09-30",
            "singer": [{"name": singer_name, "mid": "fallback_singer_001"}],
        },
        {
            "songmid": "fallback_002",
            "songname": "雨爱",
            "albumname": "Rainie & Love...? 雨爱",
            "albummid": "fallback_album_002",
            "time_public": "2010-01-01",
            "singer": [{"name": singer_name, "mid": "fallback_singer_001"}],
        },
        {
            "songmid": "fallback_003",
            "songname": "带我走",
            "albumname": "半熟宣言",
            "albummid": "fallback_album_003",
            "time_public": "2008-11-07",
            "singer": [{"name": singer_name, "mid": "fallback_singer_001"}],
        },
        {
            "songmid": "fallback_004",
            "songname": "暧昧",
            "albumname": "暧昧",
            "albummid": "fallback_album_004",
            "time_public": "2005-09-09",
            "singer": [{"name": singer_name, "mid": "fallback_singer_001"}],
        },
        {
            "songmid": "fallback_005",
            "songname": "左边",
            "albumname": "遇上爱",
            "albummid": "fallback_album_005",
            "time_public": "2006-03-17",
            "singer": [{"name": singer_name, "mid": "fallback_singer_001"}],
        },
        {
            "songmid": "fallback_006",
            "songname": "仰望",
            "albumname": "仰望",
            "albummid": "fallback_album_006",
            "time_public": "2011-07-29",
            "singer": [{"name": singer_name, "mid": "fallback_singer_001"}],
        },
    ]

    return {
        "code": 0,
        "data": {
            "_fallback": True,
            "zhida": {
                "zhida_singer": {
                    "singerName": singer_name,
                    "singerPic": "https://y.gtimg.cn/music/photo_new/T001R500x500M000fallback_singer_001.jpg",
                    "songNum": len(fallback_songs),
                    "albumNum": len({s["albummid"] for s in fallback_songs}),
                    "mvNum": 0,
                }
            },
            "song": {"list": fallback_songs},
        },
        "warning": "live_catalog_unavailable_using_local_fallback",
    }


def compact_song_key(name: str):
    key = re.sub(r"[\s·・]+", "", name or "").casefold()
    # Different providers commonly append equivalent live markers to the title.
    # Treat these as the same catalog song so the preferred provider can win.
    return re.sub(
        r"[\(\[（【](?:live(?:版|version)?|现场(?:版)?)[\)\]）】]$",
        "",
        key,
        flags=re.IGNORECASE,
    )


def source_link(provider: str, source_id: str, album_id: str = ""):
    if provider == "qq":
        return f"https://y.qq.com/n/ryqq/songDetail/{source_id}"
    if provider == "netease":
        return f"https://music.163.com/#/song?id={source_id}"
    if provider == "kugou":
        query = urllib.parse.urlencode({"hash": source_id, "album_id": album_id})
        return f"https://www.kugou.com/song/?{query}"
    return ""


def make_source(provider: str, source_id: str, album_id: str = ""):
    labels = {"qq": "QQ音乐", "netease": "网易云", "kugou": "酷狗"}
    return {
        "provider": provider,
        "label": labels[provider],
        "id": str(source_id),
        "url": source_link(provider, str(source_id), str(album_id or "")),
    }


def fetch_qq_catalog(name: str):
    fallback = build_fallback_search_payload(name)
    fallback_songs = fallback["data"]["song"]["list"]
    fallback_by_name = {song["songname"]: song for song in fallback_songs}

    query = urllib.parse.urlencode({"key": name, "format": "json"})
    req = urllib.request.Request(
        f"{QQ_SEARCH_URL}?{query}",
        headers={
            "Referer": "https://y.qq.com/",
            "User-Agent": "Mozilla/5.0",
        },
    )
    with urllib.request.urlopen(req, timeout=8) as response:
        raw = json.loads(response.read().decode("utf-8"))
    if raw.get("code") != 0 or not raw.get("data"):
        raise ValueError("QQ Music search returned no usable data")

    source_data = raw["data"]
    singer_items = source_data.get("singer", {}).get("itemlist", [])
    song_items = source_data.get("song", {}).get("itemlist", [])
    album_items = source_data.get("album", {}).get("itemlist", [])
    mv_items = source_data.get("mv", {}).get("itemlist", [])

    singer = singer_items[0] if singer_items else {}
    singer_name = singer.get("name") or name
    singer_mid = singer.get("mid") or "fallback_singer_001"
    singer_pic = (singer.get("pic") or "").replace("http://", "https://")

    songs = []
    seen_names = set()
    for item in song_items:
        song_name = item.get("name")
        song_mid = item.get("mid")
        if not song_name or not song_mid:
            continue

        song = dict(fallback_by_name.get(song_name, {}))
        song.update({
            "songmid": song_mid,
            "songname": song_name,
            "source": "qq",
            "sources": [make_source("qq", song_mid)],
            "duration_seconds": None,
            "aliases": [],
            "qualities": [],
            "has_mv": False,
            "cover_url": "",
            "heat_level": None,
            "owner_count": None,
            "singer": [{
                "name": item.get("singer") or singer_name,
                "mid": singer_mid,
            }],
        })
        songs.append(song)
        seen_names.add(compact_song_key(song_name))

    return {
        "provider": "qq",
        "songs": songs,
        "profile": {
            "singerName": singer_name,
            "singerPic": singer_pic,
            "songNum": source_data.get("song", {}).get("count", len(songs)),
            "albumNum": source_data.get("album", {}).get("count", len(album_items)),
            "mvNum": source_data.get("mv", {}).get("count", len(mv_items)),
        },
        "albums": album_items,
    }


def netease_aes_encrypt(data: bytes, key: bytes):
    padding_length = 16 - len(data) % 16
    padded = data + bytes([padding_length]) * padding_length
    encrypted = AES.new(key, AES.MODE_CBC, NETEASE_AES_IV).encrypt(padded)
    return base64.b64encode(encrypted).decode("ascii")


def netease_encrypt_payload(payload: dict):
    secret_key = "".join(
        secrets.choice(string.ascii_letters + string.digits) for _ in range(16)
    ).encode("ascii")
    serialized = json.dumps(
        payload, ensure_ascii=False, separators=(",", ":")
    ).encode("utf-8")
    first_pass = netease_aes_encrypt(serialized, NETEASE_PRESET_KEY).encode("ascii")
    params = netease_aes_encrypt(first_pass, secret_key)
    public_key = RSA.import_key(NETEASE_PUBLIC_KEY)
    encrypted_key = pow(
        int.from_bytes(secret_key[::-1], "big"),
        public_key.e,
        public_key.n,
    )
    return {
        "params": params,
        "encSecKey": format(encrypted_key, "0256x"),
    }


def fetch_netease_catalog(name: str):
    encrypted = netease_encrypt_payload({
        "s": name,
        "type": 1,
        "limit": 30,
        "offset": 0,
        "total": True,
    })
    req = urllib.request.Request(
        NETEASE_SEARCH_URL,
        data=urllib.parse.urlencode(encrypted).encode("utf-8"),
        headers={
            "Content-Type": "application/x-www-form-urlencoded",
            "Referer": "https://music.163.com/",
            "User-Agent": "Mozilla/5.0",
        },
    )
    with urllib.request.urlopen(req, timeout=12) as response:
        raw = json.loads(response.read().decode("utf-8"))
    if raw.get("code") != 200:
        raise ValueError("NetEase Cloud Music search failed")

    songs = []
    for item in raw.get("result", {}).get("songs", []):
        artists = item.get("ar") or item.get("artists") or []
        artist_names = [artist.get("name", "") for artist in artists]
        if name not in "/".join(artist_names):
            continue
        album = item.get("al") or item.get("album") or {}
        publish_time = album.get("publishTime")
        date_text = ""
        if publish_time:
            date_text = datetime.datetime.fromtimestamp(
                publish_time / 1000
            ).strftime("%Y-%m-%d")
        source_id = str(item.get("id"))
        duration_ms = item.get("dt") or item.get("duration") or 0
        aliases = item.get("alia") or item.get("alias") or []
        cover_url = album.get("picUrl") or album.get("blurPicUrl") or ""
        songs.append({
            "songmid": f"netease_{source_id}",
            "songname": item.get("name"),
            "albumname": album.get("name") or "",
            "time_public": date_text,
            "source": "netease",
            "sources": [make_source("netease", source_id)],
            "duration_seconds": round(duration_ms / 1000) if duration_ms else None,
            "aliases": aliases,
            "qualities": [],
            "has_mv": bool(item.get("mv") or item.get("mvid")),
            "cover_url": cover_url.replace("http://", "https://"),
            "popularity": item.get("pop"),
            "heat_level": None,
            "owner_count": None,
            "singer": [{"name": artist, "mid": ""} for artist in artist_names],
        })
    if not songs:
        raise ValueError("NetEase returned no matching artist results")
    return {"provider": "netease", "songs": songs}


def fetch_kugou_catalog(name: str):
    query = urllib.parse.urlencode({
        "keyword": name,
        "page": 1,
        "pagesize": 30,
        "userid": -1,
        "platform": "WebFilter",
        "filter": 2,
        "iscorrection": 1,
        "privilege_filter": 0,
    })
    req = urllib.request.Request(
        f"{KUGOU_SEARCH_URL}?{query}",
        headers={
            "Referer": "https://www.kugou.com/",
            "User-Agent": "Mozilla/5.0",
        },
    )
    with urllib.request.urlopen(req, timeout=10) as response:
        raw = json.loads(response.read().decode("utf-8"))
    if raw.get("status") != 1:
        raise ValueError("KuGou Music search failed")

    songs = []
    for item in raw.get("data", {}).get("lists", []):
        singer_name = item.get("SingerName") or ""
        if name not in singer_name:
            continue
        source_id = item.get("FileHash") or item.get("MixSongID")
        if not source_id:
            continue
        album_id = item.get("AlbumID") or ""
        qualities = ["标准"]
        if item.get("HQFileHash"):
            qualities.append("HQ")
        if item.get("SQFileHash"):
            qualities.append("SQ无损")
        if item.get("ResFileHash"):
            qualities.append("Hi-Res")
        if item.get("SuperFileHash"):
            qualities.append("超清")
        cover_url = item.get("Image") or item.get("AlbumImage") or ""
        cover_url = cover_url.replace("{size}", "240").replace("http://", "https://")
        songs.append({
            "songmid": f"kugou_{source_id}",
            "songname": item.get("SongName"),
            "albumname": item.get("AlbumName") or "",
            "time_public": item.get("PublishDate") or "",
            "source": "kugou",
            "sources": [make_source("kugou", source_id, album_id)],
            "duration_seconds": item.get("Duration"),
            "aliases": [
                value for value in (item.get("OtherName"), item.get("OriOtherName"))
                if value
            ],
            "qualities": qualities,
            "has_mv": bool(item.get("MvHash")),
            "cover_url": cover_url,
            "popularity": None,
            "heat_level": item.get("HeatLevel"),
            "owner_count": item.get("OwnerCount"),
            "singer": [{"name": singer_name, "mid": ""}],
        })
    if not songs:
        raise ValueError("KuGou returned no matching artist results")
    return {"provider": "kugou", "songs": songs}


def merge_catalog_results(name: str, results: dict, errors: dict):
    # Keep NetEase metadata when the same song appears on multiple platforms.
    provider_order = ("netease", "qq", "kugou")
    merged = {}
    profile = None
    albums = []

    for provider in provider_order:
        result = results.get(provider)
        if not result:
            continue
        if result.get("profile"):
            profile = result["profile"]
        if result.get("albums"):
            albums = result["albums"]

        for song in result["songs"]:
            song_name = song.get("songname") or ""
            key = compact_song_key(song_name)
            if not key:
                continue
            if key not in merged:
                merged[key] = song
                continue

            existing = merged[key]
            known = {source["provider"] for source in existing.get("sources", [])}
            for source in song.get("sources", []):
                if source["provider"] not in known:
                    existing.setdefault("sources", []).append(source)
            for field in ("albumname", "albummid", "time_public"):
                if not existing.get(field) and song.get(field):
                    existing[field] = song[field]
            for field in (
                "duration_seconds",
                "cover_url",
                "popularity",
                "heat_level",
                "owner_count",
            ):
                if existing.get(field) is None or existing.get(field) == "":
                    if song.get(field) is not None and song.get(field) != "":
                        existing[field] = song[field]
            existing["has_mv"] = bool(existing.get("has_mv") or song.get("has_mv"))
            existing["aliases"] = list(dict.fromkeys(
                (existing.get("aliases") or []) + (song.get("aliases") or [])
            ))
            existing["qualities"] = list(dict.fromkeys(
                (existing.get("qualities") or []) + (song.get("qualities") or [])
            ))

    songs = list(merged.values())
    if not songs:
        raise ValueError("No music provider returned usable results")

    if not profile:
        profile = {
            "singerName": name,
            "singerPic": "",
            "songNum": len(songs),
            "albumNum": len({
                song.get("albumname") for song in songs if song.get("albumname")
            }),
            "mvNum": 0,
        }
    else:
        profile["songNum"] = len(songs)
        profile["albumNum"] = max(
            profile.get("albumNum", 0),
            len({song.get("albumname") for song in songs if song.get("albumname")}),
        )

    return {
        "code": 0,
        "data": {
            "_fallback": False,
            "_skip_index": True,
            "_source": "multi_platform",
            "_providers": {
                provider: {
                    "ok": provider in results,
                    "count": len(results.get(provider, {}).get("songs", [])),
                    "error": errors.get(provider, ""),
                }
                for provider in provider_order
            },
            "zhida": {"zhida_singer": profile},
            "song": {"list": songs},
            "album": {"list": albums},
        },
    }


def fetch_aggregated_search_payload(name: str):
    fetchers = {
        "qq": fetch_qq_catalog,
        "netease": fetch_netease_catalog,
        "kugou": fetch_kugou_catalog,
    }
    results = {}
    errors = {}
    now = int(time.time())
    stale_provider_cache = {}
    pending_fetchers = {}

    for provider, fetcher in fetchers.items():
        cache_key = f"provider-v2:{provider}:{name}"
        cached = read_search_cache(cache_key)
        if cached and now - cached["updated_at"] < SEARCH_CACHE_TTL_SECONDS:
            results[provider] = cached["payload"]
        else:
            if cached:
                stale_provider_cache[provider] = cached["payload"]
            pending_fetchers[provider] = fetcher

    with ThreadPoolExecutor(max_workers=len(fetchers)) as executor:
        futures = {
            executor.submit(fetcher, name): provider
            for provider, fetcher in pending_fetchers.items()
        }
        for future in as_completed(futures):
            provider = futures[future]
            try:
                result = future.result()
                results[provider] = result
                write_search_cache(f"provider-v2:{provider}:{name}", result)
            except Exception as exc:
                if provider in stale_provider_cache:
                    results[provider] = stale_provider_cache[provider]
                    errors[provider] = f"using stale provider cache: {exc}"
                else:
                    errors[provider] = str(exc)
                logger.warning(f"{provider} search failed for {name}: {exc}")
    return merge_catalog_results(name, results, errors)


def read_search_cache(query: str):
    con = get_db_connection()
    row = con.execute(
        "SELECT payload, updated_at FROM music_search_cache WHERE query = ?",
        (query,),
    ).fetchone()
    con.close()
    if not row:
        return None
    return {
        "payload": json.loads(row["payload"]),
        "updated_at": int(row["updated_at"]),
    }


def write_search_cache(query: str, payload: dict):
    updated_at = int(time.time())
    con = get_db_connection()
    con.execute(
        """
        INSERT INTO music_search_cache (query, payload, updated_at)
        VALUES (?, ?, ?)
        ON CONFLICT(query) DO UPDATE SET
            payload = excluded.payload,
            updated_at = excluded.updated_at
        """,
        (query, json.dumps(payload, ensure_ascii=False), updated_at),
    )
    con.commit()
    con.close()
    return updated_at


def get_db_connection():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

def seed_tours_from_json(con):
    if not TOURS_JSON_PATH.exists():
        return
    try:
        with open(TOURS_JSON_PATH, "r", encoding="utf-8") as f:
            data = json.load(f) or []
    except Exception as e:
        logger.warning(f"Failed to load tours.json: {e}")
        return

    for item in data:
        tour_name = item.get("tour_name") or "Unknown Tour"
        city = item.get("city")
        tour_date = item.get("date") or item.get("tour_date")
        venue = item.get("venue")
        status = item.get("status") or "scheduled"
        if not city or not tour_date:
            continue

        con.execute(
            """
            INSERT INTO tours (tour_name, city, tour_date, venue, status)
            SELECT ?, ?, ?, ?, ?
            WHERE NOT EXISTS (
                SELECT 1 FROM tours WHERE tour_name = ? AND city = ? AND tour_date = ?
            )
            """,
            (tour_name, city, tour_date, venue, status, tour_name, city, tour_date),
        )

def init_db():
    if not DB_PATH.parent.exists():
        DB_PATH.parent.mkdir(parents=True)

    con = get_db_connection()
    with open(SCHEMA_PATH, "r", encoding="utf-8") as f:
        con.executescript(f.read())

    # Create cache table if not exists
    con.execute("""
        CREATE TABLE IF NOT EXISTS song_stats_cache (
            mid TEXT PRIMARY KEY,
            data TEXT,
            updated_at TIMESTAMP
        )
    """)
    con.execute("""
        CREATE TABLE IF NOT EXISTS music_search_cache (
            query TEXT PRIMARY KEY,
            payload TEXT NOT NULL,
            updated_at INTEGER NOT NULL
        )
    """)
    seed_tours_from_json(con)
    con.commit()
    con.close()
    print(f"Database schema initialized at {DB_PATH}")

# 主页 - 直接返回静态页面
@app.get("/")
def index():
    return send_from_directory(app.static_folder, "index.html")

# 音乐统计页
@app.get("/music")
def music_stats():
    return send_from_directory(app.static_folder, "stats.html")

# 巡演成就页 (Desktop only)
@app.get("/tour")
def tour_archive():
    # 这里我们暂时复用 stats.html 或者创建一个新的页面
    # 根据用户需求，这里应该是一个展示演唱会成就的界面
    # 暂时先返回一个简单的 placeholder 页面或者复用 stats.html
    # 如果没有专门的 tour.html，我们可以先指向 stats.html 或者创建一个简单的
    if (Path(app.static_folder) / "tour.html").exists():
        return send_from_directory(app.static_folder, "tour.html")
    else:
        # 如果没有 tour.html，暂时用 stats.html 顶替，或者返回一个建设中页面
        return "Tour Archive Page (Under Construction)"

# API: 搜索歌手并获取热门歌曲
@app.get("/api/search_singer")
def search_singer():
    name = request.args.get("name", "杨丞琳").strip() or "杨丞琳"
    now = int(time.time())
    cache_key = f"multi-platform-v4:{name}"
    cached = read_search_cache(cache_key)

    if cached and now - cached["updated_at"] < SEARCH_CACHE_TTL_SECONDS:
        payload = cached["payload"]
        payload["data"]["_cached"] = True
        payload["data"]["_cache_age_seconds"] = now - cached["updated_at"]
        return jsonify(payload)

    try:
        payload = fetch_aggregated_search_payload(name)
        all_providers_ok = all(
            provider["ok"]
            for provider in payload["data"]["_providers"].values()
        )
        updated_at = (
            write_search_cache(cache_key, payload)
            if all_providers_ok
            else now
        )
        payload["data"]["_cached"] = False
        payload["data"]["_updated_at"] = updated_at
        return jsonify(payload)
    except Exception as e:
        logger.warning(f"Multi-platform music search failed for {name}: {e}")
        if cached:
            payload = cached["payload"]
            payload["data"]["_cached"] = True
            payload["data"]["_stale"] = True
            payload["data"]["_cache_age_seconds"] = now - cached["updated_at"]
            return jsonify(payload)
        return jsonify(build_fallback_search_payload(name))

# API: 获取歌曲详细统计信息 (收藏量)
# 注意：由于风控原因，目前仅保留接口定义，实际上不进行敏感数据请求
# 前端已改为不调用此接口，或仅用作占位
@app.get("/api/song_stats")
def song_stats():
    # 直接返回空数据，不再处理 Cookie 或请求 QQ 音乐
    return jsonify({"code": 0, "song_stats": {"data": {"list": []}}})

def fetch_json_url(url: str, params: dict, headers=None):
    query = urllib.parse.urlencode(params)
    req = urllib.request.Request(
        f"{url}?{query}",
        headers=headers or {"User-Agent": "Mozilla/5.0"},
    )
    with urllib.request.urlopen(req, timeout=15) as response:
        return json.loads(response.read().decode("utf-8"))


def fetch_provider_lyrics(provider: str, song_id: str):
    if provider == "netease":
        data = fetch_json_url(
            "https://music.163.com/api/song/lyric",
            {"os": "pc", "id": song_id, "lv": -1, "kv": -1, "tv": -1},
            {"User-Agent": "Mozilla/5.0", "Referer": "https://music.163.com/"},
        )
        return {
            "lyric": data.get("lrc", {}).get("lyric", ""),
            "trans": data.get("tlyric", {}).get("lyric", ""),
        }

    if provider == "qq":
        data = fetch_json_url(
            "https://c.y.qq.com/lyric/fcgi-bin/fcg_query_lyric_new.fcg",
            {"songmid": song_id, "format": "json", "nobase64": 1, "g_tk": 5381},
            {"User-Agent": "Mozilla/5.0", "Referer": "https://y.qq.com/"},
        )
        return {"lyric": data.get("lyric", ""), "trans": data.get("trans", "")}

    if provider == "kugou":
        search = fetch_json_url(
            "https://lyrics.kugou.com/search",
            {"ver": 1, "man": "yes", "client": "pc", "hash": song_id},
        )
        candidates = search.get("candidates") or []
        if not candidates:
            return {"lyric": "", "trans": ""}
        candidate = candidates[0]
        data = fetch_json_url(
            "https://lyrics.kugou.com/download",
            {
                "ver": 1,
                "client": "pc",
                "id": candidate["id"],
                "accesskey": candidate["accesskey"],
                "fmt": "lrc",
                "charset": "utf8",
            },
        )
        content = data.get("content", "")
        lyric = base64.b64decode(content).decode("utf-8", errors="replace") if content else ""
        return {"lyric": lyric, "trans": ""}

    return {"lyric": "", "trans": ""}


# API: 获取歌词
@app.get("/api/lyrics")
def get_lyrics():
    songmid = request.args.get("mid")
    if not songmid:
        return jsonify({"error": "Missing songmid"}), 400

    sources = []
    raw_sources = request.args.get("sources", "")
    if raw_sources:
        try:
            parsed = json.loads(raw_sources)
            if isinstance(parsed, list):
                sources = parsed
        except (TypeError, ValueError, json.JSONDecodeError):
            pass

    refs = {}
    for source in sources:
        provider = str(source.get("provider", "")).lower()
        source_id = str(source.get("id", ""))
        if provider in {"netease", "qq", "kugou"} and re.fullmatch(r"[A-Za-z0-9_-]{1,64}", source_id):
            refs[provider] = source_id
    refs.setdefault("qq", songmid)

    errors = []
    for provider in ("netease", "qq", "kugou"):
        source_id = refs.get(provider)
        if not source_id:
            continue
        cache_key = f"lyrics-v1:{provider}:{source_id}"
        cached = read_search_cache(cache_key)
        if cached and int(time.time()) - cached["updated_at"] < LYRICS_CACHE_TTL_SECONDS:
            payload = cached["payload"]
            payload.update({"provider": provider, "cached": True})
            return jsonify(payload)
        try:
            payload = fetch_provider_lyrics(provider, source_id)
            if payload.get("lyric", "").strip():
                write_search_cache(cache_key, payload)
                payload.update({"provider": provider, "cached": False})
                return jsonify(payload)
            errors.append(f"{provider}: empty")
        except Exception as exc:
            logger.warning("Lyrics fetch failed for %s:%s: %s", provider, source_id, exc)
            errors.append(f"{provider}: unavailable")

    return jsonify({"lyric": "", "trans": "", "error": "；".join(errors)}), 502

# API: 获取专辑详情（含歌曲列表）
@app.get("/api/album_songs")
def get_album_songs():
    albummid = request.args.get("mid")
    if not albummid:
        return jsonify({"error": "Missing albummid"}), 400

    url = "https://c.y.qq.com/v8/fcg-bin/fcg_v8_album_info_cp.fcg"
    params = {
        "albummid": albummid,
        "format": "json",
        "newsong": 1
    }

    query_string = urllib.parse.urlencode(params)
    full_url = f"{url}?{query_string}"

    headers = {
        "Referer": "https://y.qq.com/",
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"
    }

    try:
        req = urllib.request.Request(full_url, headers=headers)
        with urllib.request.urlopen(req) as response:
            data = json.loads(response.read().decode('utf-8'))
            return jsonify(data)
    except Exception as e:
        return jsonify({"error": str(e)}), 500

# API: 获取歌曲详细指数（仅使用本地缓存）
@app.get("/api/song_index")
def get_song_index():
    mid = request.args.get("mid")
    if not mid:
        return jsonify({"error": "Missing mid"}), 400

    try:
        con = get_db_connection()
        cached = con.execute("SELECT data, updated_at FROM song_stats_cache WHERE mid = ?", (mid,)).fetchone()
        con.close()

        if cached:
            return jsonify({
                "code": 0,
                "data": json.loads(cached["data"]),
                "updated_at": cached["updated_at"],
            })

        return jsonify({
            "code": 0,
            "message": "realtime_index_unavailable",
            "data": {
                "music_index": "-",
                "global_rank": "-",
                "yesterday_index": "-",
                "index_change": "-",
                "yesterday_rank": "-",
                "rank_change": "-",
                "update_time": "暂无实时指数",
                "chart_image": "",
                "achievements": []
            }
        })

    except Exception as e:
        logger.error(f"Unhandled exception in get_song_index: {e}")
        return jsonify({"code": -1, "error": str(e)}), 500

# API: 获取未来所有巡演
@app.get("/api/upcoming-tours")
def get_upcoming_tours():
    # 检查数据库是否存在
    if not DB_PATH.exists():
        return jsonify([])

    try:
        con = get_db_connection()
        print("DEBUG: Executing query SELECT * FROM tours ORDER BY tour_date ASC")
        # 查找所有场次，按时间排序
        tours = con.execute(
            "SELECT * FROM tours ORDER BY tour_date ASC"
        ).fetchall()
        con.close()
        print(f"DEBUG: Found {len(tours)} tours")

        return jsonify([
            {
                "tour_name": tour["tour_name"],
                "city": tour["city"],
                "date": tour["tour_date"],
                "venue": tour["venue"],
                "status": tour["status"]
            } for tour in tours
        ])
    except sqlite3.OperationalError:
        # 如果表不存在等数据库错误，返回空列表
        return jsonify([])

if __name__ == "__main__":
    # 总是尝试初始化（为了应对schema变更或初次运行）
    init_db()

    # 简单的静态网页服务器
    # 使用 8000 端口
    app.run(host="0.0.0.0", port=8000, debug=False)
