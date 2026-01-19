import os
import sqlite3
import datetime
from pathlib import Path
from flask import Flask, send_from_directory, jsonify, request
import urllib.request
import urllib.parse
import json

BASE_DIR = Path(__file__).resolve().parent
DB_PATH = BASE_DIR / "db" / "room64.db"
SCHEMA_PATH = BASE_DIR / "db" / "schema.sql"

app = Flask(__name__, static_folder="static", static_url_path="/static")

def get_db_connection():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    if not DB_PATH.parent.exists():
        DB_PATH.parent.mkdir(parents=True)
    
    con = get_db_connection()
    with open(SCHEMA_PATH, "r", encoding="utf-8") as f:
        con.executescript(f.read())
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

# API: 搜索歌手并获取热门歌曲
@app.get("/api/search_singer")
def search_singer():
    name = request.args.get("name", "杨丞琳")
    
    url = "https://c.y.qq.com/soso/fcgi-bin/client_search_cp"
    params = {
        "w": name,
        "t": 0,
        "n": 5,
        "page": 1,
        "cr": 1,
        "catZhida": 1,
        "format": "json"
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

# API: 获取未来所有巡演
@app.get("/api/upcoming-tours")
def get_upcoming_tours():
    # 检查数据库是否存在
    if not DB_PATH.exists():
        return jsonify([])

    try:
        con = get_db_connection()
        # 查找 tour_date 大于现在的最近的所有场次
        now = datetime.datetime.now().isoformat()
        tours = con.execute(
            "SELECT * FROM tours WHERE tour_date > ? ORDER BY tour_date ASC",
            (now,)
        ).fetchall()
        con.close()
        
        return jsonify([
            {
                "city": tour["city"],
                "date": tour["tour_date"],
                "venue": tour["venue"]
            } for tour in tours
        ])
    except sqlite3.OperationalError:
        # 如果表不存在等数据库错误，返回空列表
        return jsonify([])

if __name__ == "__main__":
    # 总是尝试初始化（为了应对schema变更或初次运行）
    init_db()
        
    # 简单的静态网页服务器
    app.run(host="0.0.0.0", port=8000, debug=False)
