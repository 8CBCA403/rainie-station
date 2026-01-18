-- 极简用户表
CREATE TABLE IF NOT EXISTS users (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    username TEXT NOT NULL,
    created_at INTEGER NOT NULL
);

-- 巡演信息表
CREATE TABLE IF NOT EXISTS tours (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    city TEXT NOT NULL,
    tour_date TEXT NOT NULL, -- ISO 8601 format: YYYY-MM-DDTHH:MM:SS
    venue TEXT,              -- 场馆
    status TEXT DEFAULT 'scheduled' -- scheduled, completed, cancelled
);
