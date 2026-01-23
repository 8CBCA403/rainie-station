import time
import requests
import logging
import schedule
import json
import urllib.request
import urllib.parse
from scrape_selenium import scrape_music_index

# === 配置 ===
SERVER_API_URL = "http://100.65.184.87:8000/api/update_song_stats"

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger("worker")

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
            # 解析 song list
            # 结构通常是 data -> data -> song -> list
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

def job():
    logger.info("开始新一轮数据采集任务...")
    
    # 动态获取歌曲列表
    song_list = fetch_song_list(count=30) # 默认30首
    
    if not song_list:
        logger.warning("未能获取到歌曲列表，跳过本次任务")
        return

    for mid in song_list:
        try:
            logger.info(f"正在爬取: {mid}")
            
            # 1. 爬取数据
            data = scrape_music_index(mid)
            
            if data and "error" not in data:
                logger.info(f"爬取成功，正在推送到服务器...")
                
                # 2. 推送到云服务器
                payload = {
                    "mid": mid,
                    "data": data
                }
                # 安全头
                headers = {
                    "Authorization": "Bearer rainie-forever-2026",
                    "Content-Type": "application/json"
                }
                try:
                    resp = requests.post(SERVER_API_URL, json=payload, headers=headers, timeout=10)
                    if resp.status_code == 200:
                        logger.info(f"推送成功: {mid}")
                    else:
                        logger.error(f"推送失败: {resp.status_code} - {resp.text}")
                except Exception as e:
                    logger.error(f"网络请求异常: {e}")
            else:
                logger.error(f"爬取失败: {mid} - {data.get('error')}")
            
            # 礼貌性延迟
            time.sleep(5) 
            
        except Exception as e:
            logger.error(f"任务异常: {e}")

    logger.info("本轮任务结束，等待下一次调度...")

if __name__ == "__main__":
    logger.info("树莓派采集节点已启动")
    
    # 立即运行一次
    job()
    
    # 每天凌晨 3 点和下午 3 点运行
    schedule.every().day.at("03:00").do(job)
    schedule.every().day.at("15:00").do(job)
    
    while True:
        schedule.run_pending()
        time.sleep(60)
