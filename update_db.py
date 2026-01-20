import sqlite3
import json
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent
DB_PATH = BASE_DIR / "db" / "room64.db"
JSON_PATH = BASE_DIR / "db" / "tours.json"

def update_tours():
    print(f"Connecting to database at {DB_PATH}...")
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    # 因为修改了 schema，我们需要重新创建表
    # 注意：这会删除旧表及其数据。对于开发环境是可以的。
    print("Recreating tours table...")
    cursor.execute("DROP TABLE IF EXISTS tours")
    
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS tours (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        tour_name TEXT NOT NULL,
        city TEXT NOT NULL,
        tour_date TEXT NOT NULL,
        venue TEXT,
        status TEXT DEFAULT 'scheduled'
    )
    """)
    
    # 从 JSON 加载数据
    new_tours = []
    if JSON_PATH.exists():
        print(f"Loading tours from {JSON_PATH}...")
        with open(JSON_PATH, "r", encoding="utf-8") as f:
            data = json.load(f)
            for item in data:
                new_tours.append((
                    item.get("tour_name", "Unknown Tour"),
                    item["city"],
                    item.get("date", item.get("tour_date")), # Handle both keys just in case
                    item["venue"],
                    item.get("status", "scheduled")
                ))
    else:
        print("Warning: tours.json not found. Using empty list.")
        
    print(f"Inserting {len(new_tours)} tours...")
    cursor.executemany(
        "INSERT INTO tours (tour_name, city, tour_date, venue, status) VALUES (?, ?, ?, ?, ?)",
        new_tours
    )
    
    conn.commit()
    print("Database updated successfully.")
    conn.close()

if __name__ == "__main__":
    # Ensure db directory exists
    if not DB_PATH.parent.exists():
        DB_PATH.parent.mkdir(parents=True)
        
    update_tours()
