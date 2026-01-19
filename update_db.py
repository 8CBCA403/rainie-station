import sqlite3
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent
DB_PATH = BASE_DIR / "db" / "room64.db"

def update_tours():
    print(f"Connecting to database at {DB_PATH}...")
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    # 确保表存在
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS tours (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        city TEXT NOT NULL,
        tour_date TEXT NOT NULL,
        venue TEXT,
        status TEXT DEFAULT 'scheduled'
    )
    """)
    
    # 清空旧数据
    print("Clearing old tours...")
    cursor.execute("DELETE FROM tours")
    
    # 插入新数据
    new_tours = [
        ('西安', '2026-02-07T19:00:00', '西安奥体中心体育馆'),
        ('苏州', '2026-03-07T19:00:00', '苏州奥林匹克体育中心体育馆'),
        ('泉州', '2026-03-14T19:30:00', '晋江市第二体育中心体育馆'),
        ('成都', '2026-03-28T19:00:00', '凤凰山体育公园综合体育馆')
    ]
    
    print("Inserting new tours...")
    cursor.executemany(
        "INSERT INTO tours (city, tour_date, venue) VALUES (?, ?, ?)",
        new_tours
    )
    
    conn.commit()
    print(f"Successfully updated {len(new_tours)} tours.")
    conn.close()

if __name__ == "__main__":
    if DB_PATH.exists():
        update_tours()
    else:
        print("Database not found. It will be created when you run app.py")