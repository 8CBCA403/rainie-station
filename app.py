import os
import sqlite3
import datetime
from pathlib import Path
from flask import Flask, send_from_directory, jsonify, request
import urllib.request
import urllib.parse
import json

import re

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

# API: 获取歌曲详细统计信息 (收藏量)
@app.get("/api/song_stats")
def song_stats():
    songmids = request.args.get("songmids")
    if not songmids:
        return jsonify({"error": "songmids is required"}), 400

    mid_list = songmids.split(",")
    
    url = "https://u.y.qq.com/cgi-bin/musicu.fcg"
    
    # 尝试从环境变量或本地文件读取 Cookie
    cookie_str = os.environ.get("QQ_COOKIE", "")
    if not cookie_str and (BASE_DIR / ".cookie").exists():
        with open(BASE_DIR / ".cookie", "r", encoding="utf-8") as f:
            cookie_str = f.read().strip()

    # 计算 g_tk 和提取 uin
    g_tk = get_g_tk(cookie_str)
    
    uin = 0
    # 尝试提取 uin (例如 o123456 -> 123456)
    uin_match = re.search(r'uin=[o0]?(\d+)', cookie_str)
    if uin_match:
        uin = int(uin_match.group(1))
    
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
            "needNewCode": 1,
            "uin": uin,
            "g_tk": g_tk
        },
        "song_stats": {
             "module": "music.social_interaction_svr.SocialInteraction",
             "method": "GetSongCollectCount",
             "param": {
                 "song_mid_list": mid_list
             }
        }
    }
    
    # 关键修改：QQ 音乐接口有时不接受 raw body，而是需要 data=JSON
    # 我们尝试直接发送 raw string，但确保 Content-Type 是 text/plain 或留空
    # 或者，某些环境（如 requests）会自动处理，这里我们用 urllib
    data = json.dumps(payload, ensure_ascii=False).encode('utf-8')
    
    headers = {
        "Referer": "https://y.qq.com/",
        "Origin": "https://y.qq.com",
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36",
        # "Content-Type": "application/x-www-form-urlencoded", # 尝试移除这个，让它默认为 text/plain
        "Cookie": cookie_str
    }
    
    # 特别处理：如果 Cookie 中没有 qm_keyst，尝试添加一个假的或者报错提示
    # 但根据你的截图，Cookie 是有的
    
    try:
        # URL 中也建议带上 g_tk
        full_url = f"{url}?g_tk={g_tk}"
        req = urllib.request.Request(full_url, data=data, headers=headers, method="POST")
        with urllib.request.urlopen(req) as response:
            raw_resp = response.read().decode('utf-8')
            # print(f"DEBUG: {raw_resp}") # 调试用
            resp_data = json.loads(raw_resp)
            return jsonify(resp_data)
    except Exception as e:
        print(f"Error fetching stats: {e}")
        # 如果出错，返回空数据结构，避免前端报错
        return jsonify({"code": -1, "song_stats": {"data": {"list": []}}})

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
