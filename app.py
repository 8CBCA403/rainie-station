import sqlite3
import datetime
from pathlib import Path
from flask import Flask, send_from_directory, jsonify, request
import urllib.request
import urllib.parse
import json

import re
import logging
from scrape_selenium import scrape_music_index

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
        "warning": "proxy_unavailable_using_fallback",
    }

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
    seed_tours_from_json(con)
    con.commit()
    con.close()
    print(f"Database schema initialized at {DB_PATH}")

# 辅助函数：计算 g_tk
def get_g_tk(cookie_str):
    # 尝试提取 qm_keyst (首选) 或 p_skey 或 skey
    key = ""
    if "qm_keyst=" in cookie_str:
        match = re.search(r'qm_keyst=([^; ]+)', cookie_str)
        if match: key = match.group(1)
    elif "p_skey=" in cookie_str:
        match = re.search(r'p_skey=([^; ]+)', cookie_str)
        if match: key = match.group(1)
    elif "skey=" in cookie_str:
        match = re.search(r'skey=([^; ]+)', cookie_str)
        if match: key = match.group(1)

    if not key:
        return 5381

    h = 5381
    for c in key:
        h += (h << 5) + ord(c)
    return h & 0x7fffffff

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
    name = request.args.get("name", "杨丞琳")
    return jsonify(build_fallback_search_payload(name))

# API: 获取歌曲详细统计信息 (收藏量)
# 注意：由于风控原因，目前仅保留接口定义，实际上不进行敏感数据请求
# 前端已改为不调用此接口，或仅用作占位
@app.get("/api/song_stats")
def song_stats():
    # 直接返回空数据，不再处理 Cookie 或请求 QQ 音乐
    return jsonify({"code": 0, "song_stats": {"data": {"list": []}}})

# API: 获取歌词
@app.get("/api/lyrics")
def get_lyrics():
    songmid = request.args.get("mid")
    if not songmid:
        return jsonify({"error": "Missing songmid"}), 400

    return jsonify({
        "lyric": "[00:00.00] 当前歌词服务暂不可用\n[00:05.00] 已进入离线模式\n[00:10.00] 如需实时歌词，可配置新的外部数据源"
    })

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
            "message": "offline_fallback",
            "data": {
                "music_index": "-",
                "global_rank": "-",
                "yesterday_index": "-",
                "index_change": "-",
                "yesterday_rank": "-",
                "rank_change": "-",
                "update_time": "离线模式",
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
