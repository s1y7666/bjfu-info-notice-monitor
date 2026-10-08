# -*- coding: utf-8 -*-
"""抓取学院通知页，探测编码并保存，供人工分析页面结构。"""
import urllib.request
import ssl
import sys

URL = "https://xxdt.bjfu.edu.cn/dtzc/index.html"
OUT_HTML = r"D:\SuperFruit\学院通知监控\_work\page.html"
OUT_TXT = r"D:\SuperFruit\学院通知监控\_work\page.txt"

ctx = ssl.create_default_context()
ctx.check_hostname = False
ctx.verify_mode = ssl.CERT_NONE  # 高校站点证书偶发异常，探测阶段放行

req = urllib.request.Request(URL, headers={"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/120 Safari/537.36"})
resp = urllib.request.urlopen(req, timeout=25, context=ctx)
data = resp.read()
print("HTTP", resp.status)
print("Content-Type:", resp.headers.get("Content-Type"))
print("bytes:", len(data))

# 先按 header 里的 charset 尝试，再按常见编码尝试
text = None
charset = resp.headers.get_content_charset()
for enc in ([charset] if charset else []) + ["utf-8", "gbk", "gb2312", "big5"]:
    if not enc:
        continue
    try:
        text = data.decode(enc)
        print("decoded with:", enc)
        break
    except (UnicodeDecodeError, LookupError):
        continue
if text is None:
    print("!! cannot decode, save raw only")
    text = data.decode("utf-8", errors="replace")

with open(OUT_HTML, "wb") as f:
    f.write(data)
with open(OUT_TXT, "w", encoding="utf-8") as f:
    f.write(text)
print("saved:", OUT_HTML, OUT_TXT)
print("text chars:", len(text))
