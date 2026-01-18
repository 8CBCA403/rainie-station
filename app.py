import os
import sqlite3
import datetime
from pathlib import Path
from flask import Flask, send_from_directory, jsonify

BASE_DIR = Path(__file__).resolve().parent
DB_PATH = BASE_DIR / "db" / "room64.db"
SCHEMA_PATH = BASE_DIR / "db" / "schema.sql"

app = Flask(__name__, static_folder="static", static_url_path="/static")

def get_db_connection():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    """初始化数据库结构"""
    if not DB_PATH.parent.exists():
        DB_PATH.parent.mkdir(parents=True)
    
    con = get_db_connection()
    with open(SCHEMA_PATH, "r", encoding="utf-8") as f:
        con.executescript(f.read())
    con.close()
    print(f"Database schema initialized at {DB_PATH}")
    
    # 尝试填充初始数据
    seed_tours()

def seed_tours():
    """填充初始巡演数据"""
    con = get_db_connection()
    cur = con.cursor()
    
    # 检查是否已有数据
    cur.execute("SELECT count(*) FROM tours")
    if cur.fetchone()[0] == 0:
        print("Seeding initial tour data...")
        tours = [
            ("佛山", "2026-01-10T19:00:00", "佛山国际体育文化演艺中心"),
            ("绍兴", "2026-01-17T19:00:00", "西施篮球中心"),
            ("苏州", "2026-03-07T19:00:00", "苏州奥林匹克体育中心"),
            ("泉州", "2026-03-14T19:30:00", "晋江第二体育中心体育馆"),
        ]
        cur.executemany("INSERT INTO tours (city, tour_date, venue) VALUES (?, ?, ?)", tours)
        con.commit()
        print("Tour data seeded.")
    
    con.close()

# 主页 - 直接返回静态页面
@app.get("/")
def index():
    return send_from_directory(app.static_folder, "index.html")

# API: 获取未来所有巡演
@app.get("/api/upcoming-tours")
def get_upcoming_tours():
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

if __name__ == "__main__":
    # 总是尝试初始化（为了应对schema变更或初次运行）
    init_db()
        
    # 简单的静态网页服务器
    app.run(host="0.0.0.0", port=8000, debug=False)
