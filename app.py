import os
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
    # 当用户访问此页面时，尝试触发刷新
    try_trigger_auto_refresh()
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

# === Worker 指令控制系统 ===
# 使用简单的内存队列存储指令 (重启后丢失，但在此时够用了)
# 生产环境建议用 Redis 或 数据库
COMMAND_QUEUE = []
LAST_AUTO_REFRESH_TIME = None # 记录上一次自动触发刷新的时间
AUTO_REFRESH_COOLDOWN = 1800  # 冷却时间：30分钟 (1800秒)

def try_trigger_auto_refresh():
    """尝试触发自动刷新 (带冷却检查)"""
    global LAST_AUTO_REFRESH_TIME
    now = datetime.datetime.now()
    
    # 检查冷却时间
    if LAST_AUTO_REFRESH_TIME:
        elapsed = (now - LAST_AUTO_REFRESH_TIME).total_seconds()
        if elapsed < AUTO_REFRESH_COOLDOWN:
            logger.info(f"自动刷新处于冷却中 (剩余 {int(AUTO_REFRESH_COOLDOWN - elapsed)} 秒)")
            return False
            
    # 触发刷新
    LAST_AUTO_REFRESH_TIME = now
    COMMAND_QUEUE.append({
        "command": "refresh_all",
        "timestamp": now.isoformat(),
        "params": {"source": "auto_visit_trigger"}
    })
    logger.info("界面访问触发自动刷新指令 (refresh_all)")
    return True

@app.route('/api/worker/command', methods=['POST'])
def send_worker_command():
    """前端或管理员调用此接口，给树莓派下达指令"""
    try:
        data = request.json
        cmd = data.get('command')
        if not cmd:
            return jsonify({"error": "Missing command"}), 400
            
        # 将指令加入队列
        COMMAND_QUEUE.append({
            "command": cmd,
            "timestamp": datetime.datetime.now().isoformat(),
            "params": data.get('params', {})
        })
        logger.info(f"指令已入列: {cmd}")
        return jsonify({"status": "queued", "queue_length": len(COMMAND_QUEUE)})
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/api/worker/poll', methods=['GET'])
def worker_poll():
    """树莓派 Worker 每分钟调用一次此接口，获取最新指令"""
    if COMMAND_QUEUE:
        # 取出最早的一条指令 (FIFO)
        cmd = COMMAND_QUEUE.pop(0)
        logger.info(f"指令已下发给 Worker: {cmd['command']}")
        return jsonify({"has_command": True, "data": cmd})
    else:
        return jsonify({"has_command": False})

# API: 搜索歌手并获取热门歌曲
@app.get("/api/search_singer")
def search_singer():
    name = request.args.get("name", "杨丞琳")
    
    # 由于服务器端网络限制，无法直接访问 QQ 音乐
    # 我们改为将搜索请求转发给树莓派 (Tailscale IP: 100.93.253.71)
    
    pi_url = f"http://100.93.253.71:5000/api/search_singer?name={urllib.parse.quote(name)}"
    
    try:
        # 设置超时时间，避免前端等太久
        req = urllib.request.Request(pi_url)
        with urllib.request.urlopen(req, timeout=8) as response:
            content = response.read().decode('utf-8')
            # 增加对 QQ 音乐不规范 JSON 的容错处理
            # 有时候 QQ 音乐会返回 callback(...) 格式
            if content.strip().startswith("callback"):
                 # 去掉 callback( ... )
                 start = content.find("(") + 1
                 end = content.rfind(")")
                 if start > 0 and end > start:
                     content = content[start:end]
            
            # 有时返回的内容前面有空字符
            data = json.loads(content.strip())
            return jsonify(data)
            
    except json.JSONDecodeError as e:
        logger.error(f"JSON Parse Error from Pi: {e}, Content preview: {content[:100] if 'content' in locals() else 'None'}")
        return jsonify({"error": f"Invalid JSON from Pi: {str(e)}"}), 502
    except Exception as e:
        logger.error(f"Forward search to Pi failed: {e}")
        # 如果树莓派也挂了，返回 500
        return jsonify({"error": f"Search failed (Proxy): {str(e)}"}), 500

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
        
    # 转发给树莓派
    pi_url = f"http://100.93.253.71:5000/api/get_lyrics?mid={songmid}"
    
    try:
        req = urllib.request.Request(pi_url)
        with urllib.request.urlopen(req, timeout=5) as response:
            data = json.loads(response.read().decode('utf-8'))
            return jsonify(data)
    except Exception as e:
        logger.error(f"Forward lyrics to Pi failed: {e}")
        return jsonify({"error": f"Get lyrics failed (Proxy): {str(e)}"}), 500

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

# API: 接收来自树莓派/本地爬虫的数据推送
# 为了安全，您可以加一个简单的 token 验证
@app.post("/api/update_song_stats")
def update_song_stats():
    try:
        # === 安全验证 ===
        # 只有带上正确 Token 的请求才会被处理
        token = request.headers.get("Authorization")
        if token != "Bearer rainie-forever-2026": # 您可以随便改这个密码
            logger.warning(f"Unauthorized access attempt from {request.remote_addr}")
            return jsonify({"error": "Unauthorized"}), 401
            
        data = request.json
        mid = data.get("mid")
        stats_data = data.get("data")
        
        if not mid or not stats_data:
            return jsonify({"error": "Missing mid or data"}), 400
            
        con = get_db_connection()
        now_str = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        
        # 存入数据库
        con.execute("""
            INSERT OR REPLACE INTO song_stats_cache (mid, data, updated_at)
            VALUES (?, ?, ?)
        """, (mid, json.dumps(stats_data), now_str))
        con.commit()
        con.close()
        
        logger.info(f"Received stats update for {mid} from worker")
        return jsonify({"code": 0, "message": "success"})
        
    except Exception as e:
        logger.error(f"Failed to update stats: {e}")
        return jsonify({"code": -1, "error": str(e)}), 500

# API: 获取歌曲详细指数 (优先查库，查不到则尝试从树莓派拉取)
@app.get("/api/song_index")
def get_song_index():
    mid = request.args.get("mid")
    if not mid:
        return jsonify({"error": "Missing mid"}), 400
        
    try:
        # 1. 检查本地缓存
        con = get_db_connection()
        cached = con.execute("SELECT data, updated_at FROM song_stats_cache WHERE mid = ?", (mid,)).fetchone()
        con.close()
        
        # 缓存策略：如果有数据，直接返回 (因为现在树莓派会主动推送最新数据过来)
        # 只要推送成功，本地缓存就是最新的
        if cached:
            # 检查是否过期太久 (比如超过24小时)，如果太久可能推送机制挂了
            updated_at = datetime.datetime.strptime(cached["updated_at"], "%Y-%m-%d %H:%M:%S")
            now = datetime.datetime.now()
            
            # 只有在数据非常老 (超过4小时) 的情况下，才尝试主动去拉
            # 正常情况下，树莓派的推送会保证数据是新鲜的 (30分钟-1小时)
            if (now - updated_at).total_seconds() < 14400: 
                return jsonify({"code": 0, "data": json.loads(cached["data"])})
            else:
                logger.info(f"数据已过期 (>4h)，尝试主动从树莓派拉取: {mid}")
        
        # 2. 尝试从树莓派主动拉取 (Failover)
        # 注意：这里会阻塞请求约 1-2 秒，取决于树莓派响应速度
        try:
            # 树莓派 Tailscale IP
            pi_url = f"http://100.93.253.71:5000/api/get_data/{mid}"
            resp = urllib.request.urlopen(pi_url, timeout=3)
            if resp.status == 200:
                pi_data = json.loads(resp.read().decode('utf-8'))
                if pi_data.get("code") == 0 and pi_data.get("data"):
                    # 拉取成功，更新本地数据库
                    new_data = pi_data["data"]
                    con = get_db_connection()
                    now_str = now.strftime("%Y-%m-%d %H:%M:%S")
                    con.execute("""
                        INSERT OR REPLACE INTO song_stats_cache (mid, data, updated_at)
                        VALUES (?, ?, ?)
                    """, (mid, json.dumps(new_data), now_str))
                    con.commit()
                    con.close()
                    logger.info(f"Pulled data for {mid} from Raspberry Pi")
                    return jsonify({"code": 0, "data": new_data})
        except Exception as e:
            logger.warning(f"Failed to pull from Raspberry Pi: {e}")

        # 3. 如果拉取失败，退回到旧缓存 (如果有)
        if cached:
            return jsonify({"code": 0, "data": json.loads(cached["data"]), "warning": "using_stale_cache"})
            
        # 4. 彻底没有数据
        return jsonify({
            "code": 1, 
            "message": "Data queuing...", 
            "data": None
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
