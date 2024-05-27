# -*- coding: UTF-8 -*-

import asyncio
import os
import random
import threading
import json

import requests
from bs4 import BeautifulSoup
from pyppeteer import launch
from collections import deque
import time
from datetime import datetime

BASE_PATH = os.path.dirname(os.path.abspath(__file__))
USER_AGENT = "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36"

DEFAULT_DOWNLOAD_HOST = 'https://npm.taobao.org/mirrors'
os.environ["PYPPETEER_DOWNLOAD_HOST"] = DEFAULT_DOWNLOAD_HOST

# 设置需要访问网站
website = "http://www.halo.com:8088"
res = requests.get(website)
soup = BeautifulSoup(res.text, "html.parser")

def contains_keywords(href):
    return href and any(
        keyword in href for keyword in ["archives", "tags", "categories", "authors", "about", "console"])


all_links = {link['href'] for link in soup.find_all("a", href=contains_keywords)}

# 打乱链接列表，以模拟随机访问不同的页面
unique_links = list(all_links)
random.shuffle(unique_links)

def print_log(thread_id, str):
    print(f"threading [{thread_id}], {str}")

async def main(thread_id, all_ips):
    # 启动浏览器
    options = {
        'handleSIGINT': False,
        'handleSIGTERM': False,
        'handleSIGHUP': False,
        'args': ['--no-sandbox']
    }
    browser = await launch(options=options, headless=True)

    # 初始化滑动窗口和时间戳
    window = deque([0] * 60)
    start_time = time.time()
    counter = 0

    headers = {
        # 'User-Agent': 'python',
        'X-Forwarded-For': all_ips[random.randint(0, len(all_ips)-1)]
    }

    # 依次访问链接
    for link in unique_links:
        try:
            # 判断是否在晚上10点到早上7点之间
            current_hour = datetime.now().hour
            if 22 <= current_hour or current_hour < 7:
                # 在晚上10点到早上7点之间，设置较长的随机延迟
                delay = random.uniform(60, 120)  # 设置延迟时间范围为1到2分钟之间的随机数
            else:
                # 在其他时间段，设置较短的随机延迟
                delay = random.uniform(5, 15)  # 设置延迟时间范围为2到5秒之间的随机数
            print_log(thread_id, f"delay: {delay} s")

            await asyncio.sleep(delay)

            # 打开新的页面
            url = f'{website + link}'
            page = await browser.newPage()
            print_log(thread_id, f'url: {url}, x-forwarded-for: {headers["X-Forwarded-For"]}')

            await page.setExtraHTTPHeaders(headers)
            await page.setUserAgent(USER_AGENT)

            # 访问网页
            await page.goto(url)
            # 等待页面加载完成
            await page.waitForSelector('a')
            # 获取页面内容
            content = await page.content()
            # print_log(thread_id, content)
            # 关闭当前页面
            await page.close()

            # 计算当前时间在滑动窗口中的索引，并更新滑动窗口
            current_time = time.time()
            index = int(current_time - start_time) % 60
            window[index] += 1
            counter += 1

            # 判断过去一分钟内的访问次数是否超过6次
            if sum(window) > 6:
                # 超过6次，增加较长的随机延迟
                additional_delay = random.uniform(60, 120)  # 设置延迟时间范围为1到2分钟之间的随机数
                print_log(thread_id, f"additional_delay: {additional_delay} s")
                await asyncio.sleep(additional_delay)

            # 判断是否已经访问了一定次数，如果是，则休眠一分钟重置计数器
            if counter >= 20:
                print_log(thread_id, "达到20次访问，休眠一分钟")
                await asyncio.sleep(60)
                counter = 0

        except Exception as e:
            # 处理访问异常，例如网络连接问题、页面加载超时等
            print_log(thread_id, f"访问页面出现异常: {e}")

    # 关闭浏览器
    await browser.close()

def run_crawl_websit(thread_id, all_ips):
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    while True:
        loop.run_until_complete(main(thread_id, all_ips))

def load_proxy_ip():
    all_ips = []
    with open("ip_list.json", "r") as file:
        ip_list = file.read()
        all_ips = json.loads(ip_list)["ip_list"]

    return all_ips

if __name__ == "__main__":
    all_ips = load_proxy_ip()
    print(len(all_ips))
    threads = []
    for i in range(1):
        thread = threading.Thread(target=run_crawl_websit, args=(i,all_ips,))
        threads.append(thread)
        thread.start()

    for thread in threads:
        thread.join()

    print("all thread done")

