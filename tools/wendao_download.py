"""下载「问道中传」引用文件：解析 fileview 页里的真实文件地址，直接落盘。

- 输入：kb-catalog.json + kb-catalog-new.json（可再传别的目录）
- 输出：sources/wendao/<fileId 前8位>_<文件名> + index.json
- 只下载公开可访问的原文；不携带任何登录凭证
"""
from __future__ import annotations

import base64
import hashlib
import json
import re
import sys
import time
import urllib.parse
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / "sources" / "wendao"
UA = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/141.0.0.0 Safari/537.36"
VIEW = "https://aihub.cuc.edu.cn/doc/view/fileview?fileId={}"
URL_RE = re.compile(r"var\s+url\s*=\s*'([^']+)'")
INDEX = OUT / "index.json"


def get(url: str, timeout: int = 60) -> bytes:
    req = urllib.request.Request(url, headers={"User-Agent": UA})
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return r.read()


def resolve(file_id: str) -> tuple[str, str]:
    html = get(VIEW.format(file_id)).decode("utf-8", "ignore")
    m = URL_RE.search(html)
    if not m:
        raise RuntimeError("未找到文件地址")
    url = m.group(1)
    if "getCorsFile" in url:
        q = urllib.parse.urlparse(url).query
        b64 = urllib.parse.parse_qs(q).get("urlPath", [""])[0]
        url = base64.b64decode(b64).decode("utf-8")
    if url.startswith("//"):
        url = "https:" + url
    elif url.startswith("/"):
        url = "https://aihub.cuc.edu.cn" + url
    url = urllib.parse.quote(url, safe=":/?&=%#")
    return url, os_basename(url)


def os_basename(url: str) -> str:
    name = urllib.parse.unquote(urllib.parse.urlparse(url).path.rsplit("/", 1)[-1])
    name = re.sub(r'[\\/:*?"<>|]', "_", name).strip()
    return name or "file.bin"


def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    index: dict[str, dict] = {}
    if INDEX.exists():
        index = json.loads(INDEX.read_text(encoding="utf-8"))

    catalogs = [ROOT / "kb-catalog.json", ROOT / "kb-catalog-new.json", *map(Path, sys.argv[1:])]
    docs: dict[str, str] = {}
    for p in catalogs:
        if not p.exists():
            continue
        for d in json.loads(p.read_text(encoding="utf-8")):
            docs.setdefault(d["id"], d.get("title", ""))

    print(f"待处理 {len(docs)} 份，已有 {len(index)} 份")
    for i, (fid, title) in enumerate(docs.items(), 1):
        rec = index.get(fid)
        if rec and rec.get("path") and (ROOT / rec["path"]).exists():
            print(f"[{i}/{len(docs)}] 跳过 {title[:40]}")
            continue
        try:
            url, name = resolve(fid)
            data = get(url, timeout=120)
            if len(data) < 200:
                raise RuntimeError(f"文件过小 {len(data)}")
            mime = "pdf" if data[:4] == b"%PDF" else ("zip" if data[:2] == b"PK" else "bin")
            ext = Path(name).suffix.lower()
            if mime == "bin" and ext in {".docx", ".xlsx", ".pptx"}:
                mime = "zip"
            dest = OUT / f"{fid[:8]}_{name}"
            dest.write_bytes(data)
            index[fid] = {
                "id": fid, "title": title, "url": url, "path": str(dest.relative_to(ROOT)),
                "name": name, "bytes": len(data), "sha256": hashlib.sha256(data).hexdigest(),
                "kind": mime, "fetched_at": time.strftime("%Y-%m-%dT%H:%M:%S"),
            }
            print(f"[{i}/{len(docs)}] 收 {len(data)//1024:>6} KB  {name[:60]}")
        except Exception as e:  # noqa: BLE001
            index.setdefault(fid, {"id": fid, "title": title})
            index[fid]["error"] = str(e)[:200]
            print(f"[{i}/{len(docs)}] ✗ {title[:40]}：{e}")
        INDEX.write_text(json.dumps(index, ensure_ascii=False, indent=2), encoding="utf-8")
        time.sleep(0.3)

    ok = sum(1 for r in index.values() if r.get("path"))
    print(f"\n完成：成功 {ok} / {len(index)}")


if __name__ == "__main__":
    main()
