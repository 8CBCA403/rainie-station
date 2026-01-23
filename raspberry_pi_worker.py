import time
import requests
import logging
import schedule
import json
import threading
import sqlite3
import os
import urllib.request
import urllib.parse
from flask import Flask, jsonify
from scrape_selenium import scrape_music_index

# === 配置 ===
DB_PATH = "pi_data.db"
PORT = 5000 # 树莓派服务端口

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler("worker.log", encoding='utf-8'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger("worker")

# 初始化 Flask
app = Flask(__name__)

def init_db():
    """初始化本地数据库"""
    with sqlite3.connect(DB_PATH) as conn:
        conn.execute("""
            CREATE TABLE IF NOT EXISTS song_stats (
                mid TEXT PRIMARY KEY,
                data TEXT,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)

def save_data(mid, data):
    """保存数据到本地"""
    try:
        with sqlite3.connect(DB_PATH) as conn:
            conn.execute("""
                INSERT OR REPLACE INTO song_stats (mid, data, updated_at)
                VALUES (?, ?, datetime('now', 'localtime'))
            """, (mid, json.dumps(data)))
        logger.info(f"数据已保存到本地: {mid}")
    except Exception as e:
        logger.error(f"保存数据失败: {e}")

@app.route('/api/get_data/<mid>', methods=['GET'])
def get_data(mid):
    """供服务器调用的接口：获取指定歌曲数据"""
    try:
        with sqlite3.connect(DB_PATH) as conn:
            cursor = conn.execute("SELECT data, updated_at FROM song_stats WHERE mid = ?", (mid,))
            row = cursor.fetchone()
            if row:
                return jsonify({
                    "code": 0,
                    "mid": mid,
                    "data": json.loads(row[0]),
                    "updated_at": row[1]
                })
            else:
                return jsonify({"code": 1, "message": "Not found"}), 404
    except Exception as e:
        return jsonify({"code": -1, "error": str(e)}), 500

@app.route('/api/search_singer', methods=['GET'])
def api_search_singer():
    """供服务器调用的接口：搜索歌手"""
    try:
        # 获取 URL 参数，默认杨丞琳
        from flask import request
        name = request.args.get("name", "杨丞琳")
        logger.info(f"Received search request for: {name}")
        
        # 复用 fetch_song_list 的逻辑，但这里我们需要返回完整的 QQ 音乐 API 结构
        # 为了简单起见，我们直接调用 client_search_cp 并返回它的原始 JSON
        
        url = "https://c.y.qq.com/soso/fcgi-bin/client_search_cp"
        params = {
            "w": name,
            "t": 0,
            "n": 30,
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
        
        req = urllib.request.Request(full_url, headers=headers)
        with urllib.request.urlopen(req) as response:
            content = response.read().decode('utf-8')
            # 直接返回原始数据
            return jsonify(json.loads(content))
            
    except Exception as e:
        logger.error(f"Search failed: {e}")
        return jsonify({"code": -1, "error": str(e)}), 500

def fetch_song_list(singer_name="杨丞琳", count=30):
    """从 QQ 音乐获取实时热门歌曲列表"""
    logger.info(f"正在获取 {singer_name} 的实时歌单...")
    url = "https://c.y.qq.com/soso/fcgi-bin/client_search_cp"
    params = {
        "w": singer_name,
        "t": 0,
        "n": count,
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
            if "data" in data and "song" in data["data"] and "list" in data["data"]["song"]:
                songs = data["data"]["song"]["list"]
                song_mids = [song["songmid"] for song in songs]
                logger.info(f"成功获取 {len(song_mids)} 首歌曲")
                return song_mids
            else:
                logger.error("获取歌单结构解析失败")
                return []
    except Exception as e:
        logger.error(f"获取歌单失败: {e}")
        return []

def crawl_job():
    """爬虫任务"""
    logger.info("开始新一轮数据采集任务...")
    song_list = fetch_song_list(count=30)
    
    if not song_list:
        logger.warning("未能获取到歌曲列表，跳过本次任务")
        return

    for mid in song_list:
        try:
            logger.info(f"正在爬取: {mid}")
            data = scrape_music_index(mid)
            
            if data and "error" not in data:
                save_data(mid, data)
            else:
                logger.error(f"爬取失败: {mid} - {data.get('error')}")
            
            time.sleep(5) 
            
        except Exception as e:
            logger.error(f"任务异常: {e}")

    logger.info("本轮任务结束")

def run_scheduler():
    """调度器线程"""
    # 立即运行一次
    crawl_job()
    
    # 定时任务
    schedule.every().day.at("03:00").do(crawl_job)
    schedule.every().day.at("15:00").do(crawl_job)
    
    while True:
        schedule.run_pending()
        time.sleep(60)

if __name__ == "__main__":
    init_db()
    
    # 在单独线程中运行调度器和爬虫，主线程运行 Flask
    t = threading.Thread(target=run_scheduler)
    t.daemon = True
    t.start()
    
    logger.info(f"树莓派数据节点已启动，监听端口 {PORT}")
    # 监听所有 IP (包括 Tailscale IP)
    app.run(host="0.0.0.0", port=PORT, debug=False, use_reloader=False)
