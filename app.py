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

# API: 搜索歌手并获取热门歌曲 (代理 tool.curleyg.info)
@app.get("/api/search_singer")
def search_singer():
    name = request.args.get("name", "杨丞琳")
    
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36",
        "Referer": "https://tool.curleyg.info/"
    }

    try:
        # 第一步：搜索歌手获取 MID
        # 注意：这里直接模拟该网站的搜索行为
        search_url = f"https://tool.curleyg.info/api/search?k={urllib.parse.quote(name)}"
        req_search = urllib.request.Request(search_url, headers=headers)
        
        singer_mid = ""
        singer_info = {}
        
        with urllib.request.urlopen(req_search) as response:
            search_data = json.loads(response.read().decode('utf-8'))
            if search_data.get("data") and len(search_data["data"]) > 0:
                # 假设第一个结果就是目标歌手
                singer = search_data["data"][0]
                singer_mid = singer.get("mid")
                singer_info = singer

        if not singer_mid:
             return jsonify({"code": -1, "msg": "Singer not found"}), 404

        # 第二步：获取歌手详细数据（包含收听人数等）
        detail_url = f"https://tool.curleyg.info/api/singer?mid={singer_mid}"
        req_detail = urllib.request.Request(detail_url, headers=headers)
        
        with urllib.request.urlopen(req_detail) as response:
            detail_data = json.loads(response.read().decode('utf-8'))
            
            # 整合数据返回给前端，保持一定的结构兼容性
            return jsonify({
                "code": 0,
                "data": {
                    "singer": singer_info,
                    "stats": detail_data.get("data", {})
                }
            })

    except Exception as e:
        return jsonify({"error": str(e)}), 500

# API: 获取歌曲详细统计信息 (收藏量)
@app.get("/api/song_stats")
def song_stats():
    songmids = request.args.get("songmids")
    if not songmids:
        return jsonify({"error": "songmids is required"}), 400

    mid_list = songmids.split(",")
    
    url = "https://u.y.qq.com/cgi-bin/musicu.fcg"
    
    # 构造请求
    payload = {
        "comm": {
            "cv": 4747474,
            "ct": 24,
            "format": "json",
            "inCharset": "utf-8",
            "outCharset": "utf-8",
            "notice": 0,
            "platform": "yqq.json",
            "needNewCode": 1
        },
        "song_stats": {
             "module": "music.social_interaction_svr.SocialInteraction",
             "method": "GetSongCollectCount",
             "param": {
                 "song_mid_list": mid_list
             }
        }
    }
    
    data = json.dumps(payload).encode('utf-8')
    
    headers = {
        "Referer": "https://y.qq.com/",
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36",
        "Content-Type": "application/x-www-form-urlencoded"
    }
    
    try:
        req = urllib.request.Request(url, data=data, headers=headers, method="POST")
        with urllib.request.urlopen(req) as response:
            resp_data = json.loads(response.read().decode('utf-8'))
            return jsonify(resp_data)
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
