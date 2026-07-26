# Rainie Station

这是一个部署在 Linux 云服务器上的 Web 项目，主题为杨丞琳的《房间里的大象》演唱会。它提供了一个极具设计感的静态展示页面。

线上访问地址：<https://rainieclub.top/>

## 🌟 功能特性

- **视觉设计**：采用杨丞琳《房间里的大象》演唱会风格，深色星空背景 + 磨砂玻璃质感。
- **响应式布局**：完美适配桌面、平板和移动端（支持 PWA 风格显示）。
- **动态时间**：实时显示当前日期和时间。
- **轻量级后端**：基于 Flask 的极简服务器，支持自动初始化 SQLite 数据库。

## 🛠️ 技术栈

- **Backend**: Python 3, Flask, SQLite
- **Frontend**: HTML5, CSS3 (Flexbox/Grid), Vanilla JS
- **Deployment**: Linux, Systemd

## 🚀 快速开始

### 1. 环境准备

确保你的环境已安装 Python 3.8+。

```bash
# 克隆项目或下载代码
git clone <your-repo-url>
cd rainie-station

# 创建虚拟环境
python3 -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate
```

### 2. 安装依赖

```bash
pip install -r requirements.txt
```

### 3. 运行开发服务器

```bash
python app.py
```

访问 [http://localhost:8000](http://localhost:8000) 即可预览。
*首次运行时，系统会自动在 `db/` 目录下初始化 `room64.db` 数据库。*

## 📦 部署 (Linux)

本项目包含标准的 Systemd 服务配置文件。

1. **修改路径**
   编辑 `rainie-station.service`，确保 `WorkingDirectory` 和 `ExecStart` 指向你的实际路径（例如 `/opt/rainie-station`）。

2. **安装服务**
   ```bash
   sudo cp rainie-station.service /etc/systemd/system/
   sudo systemctl daemon-reload
   sudo systemctl enable rainie-station
   sudo systemctl start rainie-station
   ```

3. **查看状态**
   ```bash
   sudo systemctl status rainie-station
   ```

## 📂 目录结构

```
rainie-station/
├── app.py              # 应用程序入口
├── requirements.txt    # 项目依赖
├── rainie-station.service # Systemd 服务配置
├── db/
│   └── schema.sql      # 数据库结构定义
└── static/             # 静态资源
    ├── css/            # 样式文件
    ├── js/             # 脚本文件
    └── img/            # 图片资源
```

## 📄 License

MIT
