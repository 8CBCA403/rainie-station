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

-- 插入默认演示数据（确保日期足够靠后，以免过期不显示）
-- 删除旧数据，确保每次运行都是最新的
DELETE FROM tours;

INSERT INTO tours (city, tour_date, venue) VALUES 
('Xi''an', '2026-02-07T19:00:00', 'Xi''an Olympic Sports Center'),
('Suzhou', '2026-03-07T19:00:00', 'Suzhou Olympic Sports Centre'),
('Quanzhou', '2026-03-14T19:30:00', 'Jinjiang Second Sports Center'),
('Chengdu', '2026-03-28T19:00:00', 'Phoenix Hill Sports Park');
