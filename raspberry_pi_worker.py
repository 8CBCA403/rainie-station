import time
import requests
import logging
import schedule
from scrape_selenium import scrape_music_index

# === 配置 ===
SERVER_API_URL = "http://YOUR_SERVER_IP:8000/api/update_song_stats" # 请替换为云服务器的真实IP或域名
SONG_LIST = [
    "004XNJ8Y2iD3VL", # 匿名的好友
    "001TyX4Q2ZUGF9", # 带我走
    "003Gg0kg2QfhvO", # 雨爱
    "000bRaAs1YNv8J", # 暧昧
    "000rh0dE2TyUic", # 青春住了谁
    "000uID4Z47cx9h", # 像是一颗星星
    "001T4Gro34vG3h", # 年轮说
    "000MhuIp3fdRDa", # 仰望
    "000Y5Eqb3ZEdBk", # 理想情人
    "000sdWcp39wpun", # 失忆的金鱼
]

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger("worker")

def job():
    logger.info("开始新一轮数据采集任务...")
    
    for mid in SONG_LIST:
        try:
            logger.info(f"正在爬取: {mid}")
            
            # 1. 爬取数据 (调用 scrape_selenium.py)
            # 注意：树莓派上也需要安装 selenium, chrome, chromedriver
            data = scrape_music_index(mid)
            
            if data and "error" not in data:
                logger.info(f"爬取成功，正在推送到服务器...")
                
                # 2. 推送到云服务器
                payload = {
                    "mid": mid,
                    "data": data
                }
                try:
                    resp = requests.post(SERVER_API_URL, json=payload, timeout=10)
                    if resp.status_code == 200:
                        logger.info(f"推送成功: {mid}")
                    else:
                        logger.error(f"推送失败: {resp.status_code} - {resp.text}")
                except Exception as e:
                    logger.error(f"网络请求异常: {e}")
            else:
                logger.error(f"爬取失败: {mid} - {data.get('error')}")
            
            # 礼貌性延迟，防止请求过快被封
            time.sleep(5) 
            
        except Exception as e:
            logger.error(f"任务异常: {e}")

    logger.info("本轮任务结束，等待下一次调度...")

if __name__ == "__main__":
    logger.info("树莓派采集节点已启动")
    
    # 立即运行一次
    job()
    
    # 每天凌晨 2 点运行一次
    schedule.every().day.at("02:00").do(job)
    
    while True:
        schedule.run_pending()
        time.sleep(60)
