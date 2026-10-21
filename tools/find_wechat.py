"""发现公众号文章链接（百度 site: 检索），输出候选 URL 列表。

只做发现，不做采信：抓回来之后还要用 crawl_wechat.py 看公众号名，
非官方账号（非学校/学院/部门）一律丢弃。

用法：
    python tools/find_wechat.py 免测 选课 校园卡
    python tools/find_wechat.py 免测 --out urls.txt
"""
from __future__ import annotations

import html
import re
import sys
import time
import urllib.parse
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
UA = ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
      "(KHTML, like Gecko) Chrome/141.0.0.0 Safari/537.36")
BASE = "中国传媒大学"


def baidu(query: str) -> str:
    url = "https://www.baidu.com/s?wd=" + urllib.parse.quote(query)
    req = urllib.request.Request(url, headers={"User-Agent": UA, "Accept-Language": "zh-CN,zh;q=0.9"})
    with urllib.request.urlopen(req, timeout=20) as r:
        return r.read().decode("utf-8", "ignore")


def extract(html_text: str) -> list[str]:
    out = []
    for m in re.finditer(r"https?://mp\.weixin\.qq\.com/s\?[^\s\"'<>]+", html_text):
        u = html.unescape(m.group(0)).replace("&amp;", "&")
        u = u.split("#")[0]
        if "__biz" in u and u not in out:
            out.append(u)
    return out


def main() -> None:
    args = [a for a in sys.argv[1:] if not a.startswith("--")]
    out_path = Path(sys.argv[sys.argv.index("--out") + 1]) if "--out" in sys.argv else None
    keywords = args or ["免测", "选课", "校园卡"]

    found: list[str] = []
    for kw in keywords:
        q = f"{BASE} {kw} site:mp.weixin.qq.com"
        try:
            urls = extract(baidu(q))
        except Exception as e:  # noqa: BLE001
            print(f"[失败] {kw}: {e}")
            continue
        print(f"[{kw}] 找到 {len(urls)} 条候选")
        for u in urls:
            if u not in found:
                found.append(u)
        time.sleep(1.2)

    if out_path:
        out_path.write_text("\n".join(found), encoding="utf-8")
        print(f"\n写入 {out_path}（{len(found)} 条）")
    else:
        print("\n".join(found))


if __name__ == "__main__":
    main()
