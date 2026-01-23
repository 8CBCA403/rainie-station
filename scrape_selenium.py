from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from bs4 import BeautifulSoup
import time
import re
import logging
import traceback

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler("server.log", encoding='utf-8'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

def scrape_music_index(song_mid):
    """
    使用 Selenium 渲染 H5 页面并抓取数据
    """
    driver = None
    try:
        logger.info(f"开始抓取任务: mid={song_mid}")
        
        # 构造目标 URL
        # 关键修改：移除 openinqqmusic=1 参数，防止自动跳转到下载页
        # 改为 openinqqmusic=0 试试，或者直接不带
        url = f"https://y.qq.com/m/client/music_index/index.html?ADTAG=cbshare&channelId=10036163&mid={song_mid}&type={song_mid}"
        
        # print(f"正在启动浏览器抓取: {url}")
        
        # 配置无头浏览器模式 (Headless)
        chrome_options = Options()
        
        # === 关键设置：开启无头模式 (不弹框) ===
        # chrome_options.add_argument("--headless=new") 
        # PC端调试时可以注释掉上面这行，看到浏览器界面
        # 但服务器端必须开启，否则报错
        # 为了调试，暂时开启，但注意服务器可能没有GUI
        chrome_options.add_argument("--headless=new") 
        
        # === 优化加载策略 ===
        # eager: DOMContentLoaded 触发即返回，不等图片和样式表
        chrome_options.page_load_strategy = 'eager'
        
        # 其他必要的稳定性参数
        chrome_options.add_argument("--disable-gpu")
        chrome_options.add_argument("--no-sandbox")
        chrome_options.add_argument("--disable-dev-shm-usage") # 关键：防止内存不足导致的崩溃
        chrome_options.add_argument("--disable-extensions")
        chrome_options.add_argument("--disable-infobars")
        chrome_options.add_argument("--window-size=1920,1080") # PC端分辨率
        
        # 禁用图片加载（加速）
        prefs = {"profile.managed_default_content_settings.images": 2}
        chrome_options.add_experimental_option("prefs", prefs)

        # 隐藏自动化控制特征 (防止被识别为爬虫)
        chrome_options.add_argument("--disable-blink-features=AutomationControlled")
        chrome_options.add_experimental_option("excludeSwitches", ["enable-automation"])
        chrome_options.add_experimental_option('useAutomationExtension', False)
        
        # PC端 User-Agent (伪装成普通电脑浏览器)
        chrome_options.add_argument("user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36")
        
        driver = webdriver.Chrome(options=chrome_options)
        
        # 启用 CDP 命令，模拟触摸支持 (即使是 PC UA，有时也需要)
        driver.execute_cdp_cmd("Emulation.setTouchEmulationEnabled", {
            "enabled": True,
            "configuration": "mobile"
        })
        
        # 关键：注入 JS 欺骗 navigator.webdriver
        driver.execute_cdp_cmd("Page.addScriptToEvaluateOnNewDocument", {
            "source": """
                Object.defineProperty(navigator, 'webdriver', {
                    get: () => undefined
                });
                // 模拟 Touch 事件支持
                Object.defineProperty(navigator, 'maxTouchPoints', {
                    get: () => 5
                });
            """
        })
        
        # 核心：注入 Cookie
        # 访问任意一个 QQ 音乐域名下的页面来设置 Cookie
        driver.get("https://y.qq.com")
        
        # 这里需要填入您真实的 Cookie 字符串
        # 格式：name=value; name2=value2
        # 请替换下面的 YOUR_COOKIE_STRING
        cookie_str = "pgv_pvid=9888223789; fqm_pvqid=aa73bd2d-8891-4459-9991-d3fd1dd14a0c; ts_uid=6903786015; RK=qW/MksAPSL; ptcz=365fccecb0300eae1976f99dc784fa5df954e11503db1e1eb8e097bf91643341; music_ignore_pskey=202306271436Hn@vBj; psrf_access_token_expiresAt=1774327054; wxrefresh_token=; qqmusic_key=Q_H_L_63k3NbttD0oEr3n34KYVsXLRC2lHda3QHt3Lz6JinAtEosLMwcXlanBchImQmMKBcJ2ZlIVPykeEMtW2ZI9vK9idq; psrf_musickey_createtime=1769143054; uin=198646534; psrf_qqopenid=0170E97BDEEEA9B2D171400B3A80A8BE; euin=oKEF7wvs7KoP; qm_keyst=Q_H_L_63k3NbttD0oEr3n34KYVsXLRC2lHda3QHt3Lz6JinAtEosLMwcXlanBchImQmMKBcJ2ZlIVPykeEMtW2ZI9vK9idq; psrf_qqrefresh_token=4ED43700E5CBFD5D077A52CEF4B522E4; wxopenid=; tmeLoginType=2; wxunionid=; psrf_qqaccess_token=45CE3D2302D87320F2FC3DA053B7C046; psrf_qqunionid=8CA39F052C98785246391F8889CA98A0; ts_refer=ADTAGcbshare; fqm_sessionid=aae29a5f-11ee-42cc-a309-53a546ccabea; pgv_info=ssid=s8560956036; ts_last=y.qq.com/m/client/music_index/index.html"
        
        for item in cookie_str.split('; '):
            if '=' in item:
                name, value = item.split('=', 1)
                driver.add_cookie({'name': name, 'value': value, 'domain': '.qq.com'})
        
        logger.info("Cookie 注入完成")

        # 设置页面加载超时 (防止网络卡死)
        driver.set_page_load_timeout(30)
        
        logger.info("浏览器已启动，正在加载页面...")
        try:
            driver.get(url)
        except Exception as e:
            logger.warning(f"页面加载超时或不完整 (eager mode): {e}")
        
        logger.info(f"页面加载阶段结束，当前标题: {driver.title}")
        
        # === 调试：打印页面源码的前 1000 个字符 ===
        # 这样我们就能知道到底跳到了什么页面（是验证码？是404？还是App下载页？）
        logger.info(f"页面源码预览: {driver.page_source[:1000]}")
        
        logger.info("等待关键元素渲染...")
        WebDriverWait(driver, 20).until(
            EC.presence_of_element_located((By.CLASS_NAME, "base_data"))
        )
        logger.info("关键元素已出现")
        
        # 给一点额外的缓冲时间让数字跳动动画结束
        time.sleep(2)
        
        # 获取渲染后的 HTML
        html = driver.page_source
        soup = BeautifulSoup(html, 'html.parser')
        
        # --- 解析数据 ---
        result = {}
        
        # 1. 实时数据 (指数、排名)
        # 结构: <div class="base_data_item" role="text" aria-label="实时音乐指数为303">...</div>
        index_node = soup.find(attrs={"aria-label": re.compile(r"实时音乐指数")})
        if index_node:
            text = index_node.get("aria-label")
            result['music_index'] = re.search(r"[\d,]+", text).group(0)
            
        rank_node = soup.find(attrs={"aria-label": re.compile(r"全站排名")})
        if rank_node:
            text = rank_node.get("aria-label")
            result['global_rank'] = re.search(r"[\d]+", text).group(0)
            
        # 1.5 最近更新时间
        update_time_node = soup.find(string=re.compile(r"最近更新"))
        if update_time_node:
            result['update_time'] = update_time_node.strip()

        # 2. 详细对比数据 (昨日指数、较前一天等)
        try:
             # 找到包含详细数据的容器
             mini_data_container = soup.find(class_=re.compile("base_mini_data"))
             
             if mini_data_container:
                 # 截图显示这是平铺的4个 item
                 # Item 0: 昨日指数
                 # Item 1: 指数涨跌
                 # Item 2: 昨日排名
                 # Item 3: 排名涨跌
                 items = mini_data_container.find_all(class_=re.compile("base_mini_data__item"))
                 
                 for i, item in enumerate(items):
                     label = item.get("aria-label", "")
                     # 提取数值部分 (去掉中文前缀)
                     # 比如 "昨日指数296,407" -> "296,407"
                     # "较前一天下降1.23%" -> "下降1.23%"
                     
                     if "昨日指数" in label:
                         result['yesterday_index'] = re.sub(r"昨日指数", "", label)
                     elif "昨日排名" in label:
                         result['yesterday_rank'] = re.sub(r"昨日排名", "", label)
                     elif "较前一天" in label:
                         change_val = re.sub(r"较前一天", "", label)
                         # 根据索引判断归属
                         if i == 1: # 紧跟在指数后面
                             result['index_change'] = change_val
                         elif i >= 3: # 紧跟在排名后面
                             result['rank_change'] = change_val

        except Exception as e:
            print(f"解析详细数据失败: {e}")

        # 3. 正在听人数
        listening_node = soup.find(string=re.compile(r"人正在听"))
        if listening_node:
            result['listening_count'] = re.search(r"[\d,]+", listening_node).group(0)

        # 4. 歌曲成就 (解析列表)
        achievements = []
        try:
            # 查找所有 history_item 类的元素
            ach_items = soup.find_all(class_=re.compile("history_item"))
            for item in ach_items:
                # 跳过没有内容的项
                if not item.get_text(strip=True):
                    continue
                    
                # 尝试从 aria-label 获取完整文本 (截图显示 aria-label 包含了所有信息)
                # 例如: aria-label="热歌榜 当前排名10 历史在榜1048期 最高排名4"
                # 但日期可能在子元素里
                
                date_node = item.find(class_=re.compile("history_item_time"))
                content_node = item.find(class_=re.compile("history_item_cont")) or \
                               item.find(class_=re.compile("history_item_colum")) # 截图里有 history_item_colum
                
                date_text = date_node.get_text(strip=True) if date_node else ""
                content_text = content_node.get_text(strip=True) if content_node else ""
                
                # 如果找不到具体节点，尝试用 aria-label
                if not content_text:
                    content_text = item.get("aria-label", "")
                
                if content_text:
                    # 组合成前端需要的格式: "YYYY/MM/DD 内容"
                    if date_text and not content_text.startswith(date_text):
                        achievements.append(f"{date_text} {content_text}")
                    else:
                        achievements.append(content_text)
                        
        except Exception as e:
            print(f"解析成就失败: {e}")
        
        result['achievements'] = achievements[:10] # 取前10条

        # 5. [核心] 截图图表
        # 找到图表区域 (通常包含 canvas)
        try:
            # 1. 显式等待 Canvas 出现
            # canvas 是图表的核心，必须等它画出来
            WebDriverWait(driver, 10).until(
                EC.presence_of_element_located((By.TAG_NAME, "canvas"))
            )
            canvas = driver.find_element(By.TAG_NAME, "canvas")
            
            # 2. 滚动到 Canvas 可见区域 (防止懒加载不渲染)
            driver.execute_script("arguments[0].scrollIntoView({block: 'center'});", canvas)
            time.sleep(1) # 等待滚动和渲染
            
            # 3. 找到包含标题和图表的容器
            # 结构: section.mod_box > div.box_cont > ... > canvas
            # 我们尝试截取 div.box_cont 或者 section.mod_box
            chart_container = canvas.find_element(By.XPATH, "./ancestor::section[contains(@class, 'mod_box')]")
            
            # 4. 截图
            screenshot_b64 = chart_container.screenshot_as_base64
            result['chart_image'] = f"data:image/png;base64,{screenshot_b64}"
            
        except Exception as e:
            print(f"图表截图失败: {e}")

        return result

    except Exception as e:
        logger.error(f"Selenium 抓取失败: {e}")
        logger.error(traceback.format_exc())
        return {"error": str(e)}
    finally:
        if driver:
            try:
                driver.quit()
                logger.info("浏览器已关闭")
            except Exception as e:
                logger.error(f"关闭浏览器失败: {e}")

if __name__ == "__main__":
    # 测试: 匿名的好友
    mid = "004XNJ8Y2iD3VL"
    scrape_music_index(mid)
