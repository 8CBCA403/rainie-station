import sqlite3
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent
DB_PATH = BASE_DIR / "db" / "room64.db"

def update_tours():
    print(f"Connecting to database at {DB_PATH}...")
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    # 清空旧数据
    print("Clearing old tours...")
    cursor.execute("DELETE FROM tours")
    
    # 插入新数据
    new_tours = [
        ('Xi\'an', '2026-02-07T19:00:00', 'Xi\'an Olympic Sports Center'),
        ('Suzhou', '2026-03-07T19:00:00', 'Suzhou Olympic Sports Centre'),
        ('Quanzhou', '2026-03-14T19:30:00', 'Jinjiang Second Sports Center'),
        ('Chengdu', '2026-03-28T19:00:00', 'Phoenix Hill Sports Park')
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