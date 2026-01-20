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
    
    url = "https://c.y.qq.com/soso/fcgi-bin/client_search_cp"
    params = {
        "w": name,
        "t": 0,
        "n": 30,  # 修改为 30 首
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
        
    url = "https://c.y.qq.com/lyric/fcgi-bin/fcg_query_lyric_new.fcg"
    params = {
        "songmid": songmid,
        "format": "json",
        "nobase64": 1,
        "g_tk": 5381
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
            content = response.read().decode('utf-8')
            # QQ Music lyrics API sometimes returns JSONP-ish or loose JSON
            # But with format=json, it should be clean JSON.
            # However, sometimes it wraps in callback. Let's check.
            # Based on previous test, it returned clean JSON: {"retcode":0,...}
            data = json.loads(content)
            return jsonify(data)
    except Exception as e:
        return jsonify({"error": str(e)}), 500

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
    app.run(host="0.0.0.0", port=8000, debug=False)
