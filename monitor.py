# -*- coding: utf-8 -*-
"""
学院通知监控脚本
================
定时抓取学院通知公告页，发现新通知后通过 Server酱（ServerChan）推送到微信。

用法：
    python monitor.py             # 抓取、对比、推送（状态文件不存在时自动建立基线）
    python monitor.py --init      # 仅建立基线（记录当前全部通知），不推送

环境变量：
    SERVERCHAN_SCKEY   Server酱的 SendKey（https://sct.ftqq.com 扫码绑定微信后获取）。
                       未配置时只打印新通知清单，不推送、不更新状态。
    NOTICE_URLS        要监控的页面 URL，多个用英文逗号分隔。默认监控"党团之窗"。

依赖：pip install -r requirements.txt
"""
import json
import os
import sys
import time
import urllib.parse
from datetime import datetime

import requests
from bs4 import BeautifulSoup

# 学校站点 HTTPS 证书链不全，监控场景放行证书校验并关闭告警
import urllib3
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
STATE_FILE = os.path.join(BASE_DIR, "state.json")
DEFAULT_URL = "https://xxdt.bjfu.edu.cn/dtzc/index.html"
USER_AGENT = ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
              "(KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36")


def log(msg: str) -> None:
    """带时间戳的日志输出。"""
    print(f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] {msg}", flush=True)


def fetch(url: str, retries: int = 3):
    """抓取页面文本，失败自动重试。"""
    for attempt in range(1, retries + 1):
        try:
            resp = requests.get(
                url,
                headers={"User-Agent": USER_AGENT},
                timeout=20,
                verify=False,
            )
            resp.raise_for_status()
            resp.encoding = resp.apparent_encoding or "utf-8"
            return resp.text
        except Exception as exc:  # 网络错误、超时、HTTP 状态码异常
            log(f"抓取失败（第 {attempt}/{retries} 次）：{exc}")
            time.sleep(2 * attempt)
    return None


def parse_notices(html: str, base_url: str):
    """从通知列表页解析出通知列表（标题、链接、日期）。"""
    soup = BeautifulSoup(html, "html.parser")
    items = soup.select(".list_content li")
    if not items:
        raise ValueError("未解析到通知列表（.list_content li 为空），页面结构可能已变化")

    notices = []
    for li in items:
        link = li.select_one("a[href]")
        if link is None:
            continue
        title = (link.get("title") or link.get_text(" ", strip=True)).strip()
        if not title:
            continue
        href = link["href"]
        url = urllib.parse.urljoin(base_url, href)
        date_div = li.select_one(".list_date")
        date = date_div.get_text(strip=True) if date_div else ""
        notices.append({"title": title, "url": url, "date": date})
    return notices


def load_state():
    """读取已推送通知的状态文件。"""
    if os.path.exists(STATE_FILE):
        with open(STATE_FILE, "r", encoding="utf-8") as fh:
            return json.load(fh)
    return {"seen": []}


def save_state(state) -> None:
    """保存状态文件（UTF-8）。"""
    with open(STATE_FILE, "w", encoding="utf-8") as fh:
        json.dump(state, fh, ensure_ascii=False, indent=2)


def send_wechat(sckey: str, title: str, content: str):
    """通过 Server酱接口推送微信消息，返回 (是否成功, 失败原因)。"""
    url = f"https://sctapi.ftqq.com/{sckey}.send"
    try:
        resp = requests.post(
            url,
            data={"title": title[:255], "desp": content},
            timeout=15,
            verify=False,
        )
        if resp.status_code != 200:
            return False, f"HTTP {resp.status_code}: {resp.text[:200]}"
        data = resp.json()
        if data.get("code") == 0:
            return True, ""
        return False, f"接口返回 code={data.get('code')}: {data.get('message', '')}"
    except Exception as exc:
        return False, str(exc)


def main() -> int:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")

    init_mode = "--init" in sys.argv
    sckey = os.environ.get("SERVERCHAN_SCKEY", "").strip()
    urls = [u.strip() for u in os.environ.get("NOTICE_URLS", DEFAULT_URL).split(",") if u.strip()]

    state = load_state()
    seen = set(state.get("seen", []))

    new_notices = []
    for url in urls:
        log(f"抓取：{url}")
        html = fetch(url)
        if html is None:
            log(f"跳过 {url}（多次抓取失败，请检查网络）")
            continue
        try:
            notices = parse_notices(html, url)
        except ValueError as exc:
            log(f"!! {exc}，跳过 {url}")
            continue
        log(f"解析到 {len(notices)} 条通知")
        for notice in notices:
            if notice["url"] not in seen:  # 详情页 URL 唯一，作为去重指纹
                new_notices.append(notice)

    # 首次运行（无状态文件或 --init）：建立基线，不推送历史通知
    if init_mode or not state.get("seen"):
        for notice in new_notices:
            seen.add(notice["url"])
        state["seen"] = sorted(seen)
        save_state(state)
        log(f"初始化完成：已记录 {len(state['seen'])} 条通知作为基线，之后的新通知才会推送")
        return 0

    if not new_notices:
        log("没有新通知")
        return 0

    log(f"发现 {len(new_notices)} 条新通知")
    if not sckey:
        log("未配置 SERVERCHAN_SCKEY：以下通知未推送、未记入状态，配置后重跑会补推：")
        for notice in new_notices:
            log(f"  · {notice['date']} {notice['title']} {notice['url']}")
        return 0

    pushed, failed = 0, []
    for notice in new_notices:
        content = f"**{notice['title']}**\n\n发布日期：{notice['date']}\n\n[查看详情]({notice['url']})"
        ok, reason = send_wechat(sckey, f"【学院通知】{notice['title'][:40]}", content)
        if ok:
            pushed += 1
            seen.add(notice["url"])
            log(f"已推送：{notice['title']}")
            time.sleep(1)  # 避免触发接口限流
        else:
            failed.append(notice)
            log(f"推送失败：{notice['title']} 原因：{reason}")

    if pushed:
        state["seen"] = sorted(seen)
        save_state(state)
    log(f"本轮结束：成功推送 {pushed} 条，失败 {len(failed)} 条（失败项下次运行会自动补推）")
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
