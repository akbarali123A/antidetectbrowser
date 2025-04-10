import asyncio
import json
import random
import time
from pathlib import Path
from timezonefinder import TimezoneFinder
from fake_useragent import UserAgent
from playwright.async_api import async_playwright
import requests

# Load user inputs
with open("input.json", "r") as f:
    config = json.load(f)

proxies = config["proxyList"].splitlines()
urls = config["urlList"].splitlines()
wait_min = config["waitFrom"]
wait_max = config["waitTo"]
threads = config["threads"]
click_enabled = config["autoClicker"]

ua = UserAgent()
tf = TimezoneFinder()

# IP checker
def check_proxy(ip_port):
    try:
        proxies = {
            "http": f"http://{ip_port}",
            "https": f"http://{ip_port}"
        }
        r = requests.get("http://ip-api.com/json", proxies=proxies, timeout=2)
        if r.status_code == 200 and r.elapsed.total_seconds() < 0.5:
            return r.json()
    except:
        return None
    return None

# Human behavior simulation
async def simulate_behavior(page):
    for _ in range(random.randint(1, 3)):
        await page.mouse.move(random.randint(0, 800), random.randint(0, 600))
        await page.mouse.down()
        await page.mouse.up()
        await page.keyboard.press("ArrowDown")
        await asyncio.sleep(random.uniform(0.5, 1.5))

    # Auto scroll
    for _ in range(random.randint(2, 6)):
        direction = random.choice(["down", "up"])
        await page.evaluate(f"window.scrollBy(0, {'200' if direction == 'down' else '-200'})")
        await asyncio.sleep(random.uniform(1, 2))

# Click random links
async def auto_click_links(page):
    links = await page.query_selector_all("a[href]")
    if links:
        num_clicks = random.randint(1, min(3, len(links)))
        chosen = random.sample(links, num_clicks)
        for link in chosen:
            try:
                await link.click()
                await asyncio.sleep(random.randint(20, 60))
            except:
                continue

# Handle one tab/session
async def handle_session(proxy, url):
    try:
        location = check_proxy(proxy)
        if not location:
            print(f"Skipping slow/bad proxy: {proxy}")
            return

        lat, lon = location["lat"], location["lon"]
        tz = tf.timezone_at(lat=lat, lng=lon)

        user_agent = ua.random
        wait_time = random.randint(wait_min, wait_max)

        print(f"[{proxy}] Opening {url} with wait {wait_time}s")

        async with async_playwright() as p:
            browser = await p.chromium.launch(proxy={"server": f"http://{proxy}"})
            context = await browser.new_context(
                user_agent=user_agent,
                timezone_id=tz,
                locale="en-US",
                viewport={"width": 1280, "height": 720}
            )
            page = await context.new_page()
            await page.goto(url, timeout=60000)
            await page.wait_for_timeout(2000)

            await simulate_behavior(page)
            if click_enabled:
                await auto_click_links(page)

            await page.wait_for_timeout(wait_time * 1000)

            await context.clear_cookies()
            await browser.close()
    except Exception as e:
        print(f"[{proxy}] Error: {e}")

# Master runner
async def main():
    tasks = []
    for i in range(min(len(urls), len(proxies))):
        task = handle_session(proxies[i], urls[i])
        tasks.append(task)
        if len(tasks) >= threads:
            await asyncio.gather(*tasks)
            tasks = []

    if tasks:
        await asyncio.gather(*tasks)

if __name__ == "__main__":
    asyncio.run(main())
