"""抓取中国传媒大学图书馆门户（ilib）各公开栏目的正文。

门户是 SPA，正文来自公开接口：
  /engine2/data/api-v2/<publicId>/get-classify?ac=true
先访问首页拿会话 Cookie，再逐栏抓取。只抓公开栏目，不登录。

产物：
  sources/ilib/<publicId>.json       接口原始返回
  sources/ilib-text/<label>-<publicId>.txt  正文纯文本
  sources/ilib-index.json            url / 标题 / 字数 / 抓取时间
"""
from __future__ import annotations

import hashlib
import html
import json
import re
import time
import urllib.request
import http.cookiejar
from datetime import datetime, timedelta, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SRC = ROOT / "sources"
OUT_JSON = SRC / "ilib"
OUT_TEXT = SRC / "ilib-text"
NAV = ROOT / "_ilib_nav.json"
UA = ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
      "(KHTML, like Gecko) Chrome/141.0.0.0 Safari/537.36")
TZ = timezone(timedelta(hours=8))
BASE = "https://ilib.cuc.edu.cn"


def clean_text(fragment: str) -> str:
    s = fragment
    s = re.sub(r"(?is)<(script|style).*?</\1>", " ", s)
    s = re.sub(r"(?i)<br\s*/?>", "\n", s)
    s = re.sub(r"(?i)</(p|div|li|tr|h[1-6]|table|section|article|blockquote)>", "\n", s)
    s = re.sub(r"(?i)</t[dh]>", " | ", s)
    s = re.sub(r"(?i)<img[^>]*?(?:src|data-src)=\"([^\"]+)\"[^>]*>", r" [图] \1 ", s)
    s = re.sub(r"(?s)<[^>]+>", "", s)
    s = html.unescape(s)
    s = s.replace("\u00a0", " ").replace("\u3000", " ")
    lines = []
    for line in s.split("\n"):
        line = re.sub(r"[ \t]+", " ", line).strip()
        line = re.sub(r"^[| ]+|[| ]+$", "", line)
        if line:
            lines.append(line)
    return "\n".join(lines)


def load_opener():
    cj = http.cookiejar.CookieJar()
    op = urllib.request.build_opener(urllib.request.HTTPCookieProcessor(cj))
    op.addheaders = [("User-Agent", UA), ("Accept-Language", "zh-CN,zh;q=0.9")]
    op.open(BASE + "/", timeout=30).read()
    return op


def main() -> None:
    navs = json.loads(NAV.read_text(encoding="utf-8"))
    OUT_JSON.mkdir(parents=True, exist_ok=True)
    OUT_TEXT.mkdir(parents=True, exist_ok=True)
    index_path = SRC / "ilib-index.json"
    index = json.loads(index_path.read_text(encoding="utf-8")) if index_path.exists() else {}
    op = load_opener()

    for n, item in enumerate(navs):
        pid = item["publicId"]
        label = item["label"]
        api = f"{BASE}/engine2/data/api-v2/{pid}/get-classify?ac=true"
        req = urllib.request.Request(
            api,
            headers={"Referer": BASE + "/", "Accept": "application/json, text/plain, */*"},
        )
        try:
            raw = op.open(req, timeout=30).read()
            payload = json.loads(raw)
        except Exception as e:  # noqa: BLE001
            print(f"[失败] {label} {e}")
            continue
        data = payload.get("data") or {}
        intro = data.get("introduction") or ""
        if len(intro) < 20:
            print(f"[空]   {label} (showStyle={data.get('showStyle')})")
            time.sleep(0.15)
            continue

        (OUT_JSON / f"{pid}.json").write_bytes(raw)
        text = clean_text(intro)
        title = data.get("name") or label
        header = (
            f"中国传媒大学图书馆·{title}\n"
            f"来源：{BASE}/  （栏目：{title}）\n"
            f"接口：{api}\n"
            f"发布时间：{data.get('insertTime') or ''}\n\n"
        )
        safe = re.sub(r"[^\w\u4e00-\u9fff]+", "_", label)[:40]
        text_path = OUT_TEXT / f"{safe}-{pid}.txt"
        text_path.write_text(header + text + "\n", encoding="utf-8", newline="\n")
        index[pid] = {
            "url": api,
            "title": f"中国传媒大学图书馆·{title}",
            "label": label,
            "chars": len(text),
            "sha256": hashlib.sha256(text.encode("utf-8")).hexdigest()[:16],
            "fetched_at": datetime.now(TZ).isoformat(timespec="seconds"),
            "kind": "ilib",
        }
        print(f"[ok]   {label:<12} {len(text):>6} 字")
        time.sleep(0.2)

    index_path.write_text(json.dumps(index, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"\n共 {len(index)} 个栏目，正文存于 sources/ilib-text/")


if __name__ == "__main__":
    main()
