"""把库里所有网页逐页点开，收走页面上挂的每一个附件。

用法：
    python tools/fetch_all_attachments_20261030.py --limit 20     # 先试跑
    python tools/fetch_all_attachments_20261030.py                # 全量
    python tools/fetch_all_attachments_20261030.py --resume       # 断点续跑

产物：
    sources/attachments/files/<sha8>-<原文件名>   附件原件
    sources/attachments-index.json              清单（url/来源页/大小/sha/状态）
"""
from __future__ import annotations

import argparse
import hashlib
import json
import re
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
from datetime import datetime, timedelta, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SRC = ROOT / "sources"
OUT = SRC / "attachments" / "files"
IDX = SRC / "attachments-index.json"
PAGES_IDX = SRC / "attachments-pages.json"
LOG = ROOT / "_attachments_crawl.log"

UA = ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
      "(KHTML, like Gecko) Chrome/141.0.0.0 Safari/537.36")
TZ = timezone(timedelta(hours=8))
ATT_EXT = r"(?:pdf|docx?|xlsx?|pptx?|wps|et|ofd|zip|rar|7z|csv|txt)"
ATT_RE = re.compile(r"\.(" + ATT_EXT + r")(?:[?#].*)?$", re.I)
ATT_QS = re.compile(r"[?&](?:file|filename|attach|download)[^=]*=.*\." + ATT_EXT, re.I)
MAX_HTML = 6 * 1024 * 1024
MAX_FILE = 120 * 1024 * 1024


def log(msg: str) -> None:
    line = f"{datetime.now(TZ):%H:%M:%S} {msg}"
    print(line, flush=True)
    with LOG.open("a", encoding="utf-8") as f:
        f.write(line + "\n")


def get(url: str, referer: str = "", limit: int = 0, timeout: int = 30) -> tuple[bytes, str, dict]:
    headers = {"User-Agent": UA, "Accept": "*/*"}
    if referer:
        headers["Referer"] = referer
    req = urllib.request.Request(url, headers=headers)
    with urllib.request.urlopen(req, timeout=timeout) as r:
        raw = r.read(limit) if limit else r.read()
        return raw, r.headers.get("content-type", ""), dict(r.headers)


def decode(raw: bytes, ctype: str) -> str:
    m = re.search(r"charset=([\w-]+)", ctype or "", re.I)
    candidates = [m.group(1) if m else "", "utf-8", "gb18030", "big5"]
    for enc in candidates:
        if not enc:
            continue
        try:
            return raw.decode(enc)
        except (UnicodeDecodeError, LookupError):
            continue
    return raw.decode("utf-8", "ignore")


def links(html: str, base: str) -> list[tuple[str, str]]:
    out: list[tuple[str, str]] = []
    try:
        from lxml import html as LH

        doc = LH.fromstring(html)
        for a in doc.xpath("//a[@href]"):
            href = (a.get("href") or "").strip()
            if not href or href.startswith(("javascript:", "mailto:", "#")):
                continue
            text = " ".join((a.text_content() or "").split())[:120]
            out.append((urllib.parse.urljoin(base, href), text))
        for node, attr in (("//iframe[@src]", "src"), ("//embed[@src]", "src"),
                           ("//object[@data]", "data")):
            for el in doc.xpath(node):
                src = (el.get(attr) or "").strip()
                if src:
                    out.append((urllib.parse.urljoin(base, src), ""))
    except Exception:
        for href, text in re.findall(r'<a[^>]+href="([^"]+)"[^>]*>(.*?)</a>', html, re.S | re.I):
            out.append((urllib.parse.urljoin(base, href), re.sub(r"<[^>]+>", "", text)[:120]))
    return out


def is_attachment(url: str) -> bool:
    path = urllib.parse.urlparse(url).path
    return bool(ATT_RE.search(path) or ATT_QS.search(url))


def safe_name(name: str, url: str) -> str:
    ext = (ATT_RE.search(urllib.parse.urlparse(url).path) or [None, "bin"])[1].lower()
    stem = urllib.parse.unquote(Path(urllib.parse.urlparse(url).path).stem)
    text = re.sub(r"[\\/:*?\"<>|\r\n\t]", "_", name or "").strip(" .")
    # 官网附件常是 UUID 文件名；链接文字才是人看得懂的名字
    if 4 <= len(text) <= 80 and not re.fullmatch(r"[\w\-]+", text):
        stem = text
    if not stem or re.fullmatch(r"[0-9a-f\-]{16,}", stem):
        stem = urllib.parse.unquote(Path(urllib.parse.urlparse(url).path).stem) or "file"
    stem = re.sub(r"[\\/:*?\"<>|\r\n\t]", "_", stem).strip(" .")[:80]
    return f"{stem}.{ext}"


def load_pages() -> dict[str, dict]:
    pages: dict[str, dict] = {}
    for f in sorted(SRC.glob("*-index.json")):
        if f.name == "attachments-index.json" or f.name in ("clause-coverage.json",):
            continue
        try:
            data = json.loads(f.read_text(encoding="utf-8"))
        except Exception:
            continue
        if not isinstance(data, dict):
            continue
        for slug, meta in data.items():
            if not isinstance(meta, dict):
                continue
            url = (meta.get("url") or "").split("#")[0]
            if not url.startswith("http"):
                continue
            if url in pages:
                continue
            pages[url] = {
                "slug": slug,
                "title": meta.get("title") or "",
                "kind": meta.get("kind") or "",
                "index": f.name,
            }
    return pages


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--limit", type=int, default=0)
    ap.add_argument("--resume", action="store_true")
    ap.add_argument("--hosts", default="")
    args = ap.parse_args()

    OUT.mkdir(parents=True, exist_ok=True)
    manifest: dict[str, dict] = {}
    if IDX.exists():
        try:
            manifest = json.loads(IDX.read_text(encoding="utf-8"))
        except Exception:
            manifest = {}
    page_log: dict[str, dict] = {}
    if PAGES_IDX.exists():
        try:
            page_log = json.loads(PAGES_IDX.read_text(encoding="utf-8"))
        except Exception:
            page_log = {}
    seen_sha = {v.get("sha256"): k for k, v in manifest.items() if v.get("sha256")}
    seen_url = {v.get("url"): k for k, v in manifest.items()}

    pages = load_pages()
    if args.hosts:
        want = {h.strip() for h in args.hosts.split(",") if h.strip()}
        pages = {u: m for u, m in pages.items() if urllib.parse.urlparse(u).netloc in want}
    todo = [(u, m) for u, m in pages.items()
            if not (args.resume and page_log.get(u, {}).get("status") == "done")]
    if args.limit:
        todo = todo[: args.limit]
    log(f"页面 {len(pages)} 个，待抓 {len(todo)} 个；已有附件 {len(manifest)} 个")

    n_new = n_fail = n_page_err = 0
    for i, (url, meta) in enumerate(todo, 1):
        try:
            raw, ctype, _ = get(url, limit=MAX_HTML)
            if "html" not in (ctype or "").lower() and "xml" not in (ctype or "").lower():
                if is_attachment(url):
                    pass  # 页面本身是附件：下面直接下
                else:
                    log(f"[跳过] 非网页 {ctype} {url[:90]}")
                    continue
            html = decode(raw, ctype)
            found = [(u, t) for u, t in links(html, url) if is_attachment(u)]
        except Exception as e:  # noqa: BLE001
            n_page_err += 1
            page_log[url] = {"status": "error", "n": 0, "error": f"{type(e).__name__}: {e}"[:160],
                             "at": datetime.now(TZ).isoformat(timespec="seconds")}
            log(f"[取页失败] {url[:90]} {type(e).__name__} {e}")
            continue

        # 页面本身就是附件时，把自己也当附件收
        if is_attachment(url):
            found.append((url, meta.get("title", "")))

        uniq: list[tuple[str, str]] = []
        seen = set()
        for u, t in found:
            u = u.split("#")[0]
            if u in seen:
                continue
            seen.add(u)
            uniq.append((u, t))
        if not uniq:
            page_log[url] = {"status": "done", "n": 0,
                             "at": datetime.now(TZ).isoformat(timespec="seconds")}
            log(f"[{i}/{len(todo)}] 0 附件 {url[:80]}")
            continue
        log(f"[{i}/{len(todo)}] {len(uniq)} 个附件 ← {url[:80]}")

        for att_url, text in uniq:
            if att_url in seen_url:
                log(f"    = 已收 {att_url[:80]}")
                continue
            name = safe_name(text, att_url)
            try:
                body, ctype, hdrs = get(att_url, referer=url, timeout=90)
            except Exception as e:  # noqa: BLE001
                n_fail += 1
                log(f"    ✗ 下载失败 {name[:40]} {type(e).__name__} {e}")
                continue
            if not body:
                n_fail += 1
                continue
            if len(body) > MAX_FILE:
                n_fail += 1
                log(f"    ✗ 过大 {len(body)//1048576}MB {name[:40]}")
                continue
            cd = hdrs.get("content-disposition", "")
            m = re.search(r"filename\*?=(?:UTF-8''|[\"']?)([^\"';]+)", cd, re.I)
            if m:
                name = safe_name(urllib.parse.unquote(m.group(1)), att_url)
            sha = hashlib.sha256(body).hexdigest()
            if sha in seen_sha:
                manifest[att_url] = {
                    "url": att_url, "page_url": url, "page_slug": meta["slug"],
                    "page_title": meta["title"], "name": name, "ext": Path(name).suffix.lower().lstrip("."),
                    "bytes": len(body), "sha256": sha, "saved": manifest[seen_sha[sha]].get("saved", ""),
                    "fetched_at": datetime.now(TZ).isoformat(timespec="seconds"),
                    "status": "duplicate",
                }
                seen_url[att_url] = att_url
                log(f"    = 同文件重复 {name[:50]}")
                continue
            saved = OUT / f"{sha[:8]}-{name}"
            saved.write_bytes(body)
            manifest[att_url] = {
                "url": att_url, "page_url": url, "page_slug": meta["slug"],
                "page_title": meta["title"], "name": name, "ext": Path(name).suffix.lower().lstrip("."),
                "bytes": len(body), "sha256": sha,
                "saved": str(saved.relative_to(ROOT)).replace("\\", "/"),
                "fetched_at": datetime.now(TZ).isoformat(timespec="seconds"),
                "status": "ok",
            }
            seen_sha[sha] = att_url
            seen_url[att_url] = att_url
            n_new += 1
            log(f"    [收] {len(body)//1024:>6}KB {name[:60]}")
        page_log[url] = {"status": "done", "n": len(uniq),
                         "at": datetime.now(TZ).isoformat(timespec="seconds")}
        if i % 10 == 0:
            IDX.write_text(json.dumps(manifest, ensure_ascii=False, indent=1), encoding="utf-8")
            PAGES_IDX.write_text(json.dumps(page_log, ensure_ascii=False, indent=1), encoding="utf-8")
        time.sleep(0.15)

    IDX.write_text(json.dumps(manifest, ensure_ascii=False, indent=1), encoding="utf-8")
    PAGES_IDX.write_text(json.dumps(page_log, ensure_ascii=False, indent=1), encoding="utf-8")
    log(f"完成：新增 {n_new}，失败 {n_fail}，取页失败 {n_page_err}，清单 {len(manifest)}")


if __name__ == "__main__":
    sys.exit(main())
