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
('南昌', '2025-12-31T21:00:00', '南昌国际体育中心体育馆'),
('佛山', '2026-01-10T19:00:00', '佛山国际体育文化演艺中心主馆'),
('绍兴', '2026-01-17T19:00:00', '绍兴诸暨西施篮球中心体育馆'),
('西安', '2026-02-07T19:00:00', '西安奥体中心体育馆'),
('苏州', '2026-03-07T19:00:00', '苏州奥林匹克体育中心体育馆'),
('泉州', '2026-03-14T19:30:00', '晋江市第二体育中心体育馆'),
('成都', '2026-03-28T19:00:00', '凤凰山体育公园综合体育馆');
