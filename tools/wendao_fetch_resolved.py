"""按 _wendao_resolved.json 的真实地址下载文件，落 sources/wendao 并写回 index.json。

用法：python tools/wendao_fetch_resolved.py [--cookie "..."]
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
WD = ROOT / "sources" / "wendao"
INDEX = WD / "index.json"
RESOLVED = ROOT / "_wendao_resolved.json"
UA = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/141.0.0.0 Safari/537.36"
LINK = re.compile(r"\[([^\]]{2,300}?)\]\((https://aihub\.cuc\.edu\.cn/doc/view/fileview\?fileId=([0-9a-f]{32})[^)]*)\)")


def clean(t: str) -> str:
    return re.sub(r"\s+", " ", t).strip()


def norm_url(u: str) -> str:
    if "getCorsFile" in u:
        q = urllib.parse.urlparse(u).query
        b64 = urllib.parse.parse_qs(q).get("urlPath", [""])[0]
        if b64:
            u = base64.b64decode(b64).decode("utf-8")
    if u.startswith("//"):
        u = "https:" + u
    elif u.startswith("/"):
        u = "https://aihub.cuc.edu.cn" + u
    return urllib.parse.quote(u, safe=":/?&=%#")


def basename(u: str) -> str:
    name = urllib.parse.unquote(urllib.parse.urlparse(u).path.rsplit("/", 1)[-1])
    name = re.sub(r'[\\/:*?"<>|]', "_", name).strip()
    return name or "file.bin"


def main() -> None:
    cookie = ""
    if "--cookie" in sys.argv:
        cookie = sys.argv[sys.argv.index("--cookie") + 1]
    resolved = json.loads(RESOLVED.read_text(encoding="utf-8"))
    index = json.loads(INDEX.read_text(encoding="utf-8"))

    # 标题：从回答里取同一 fileId 的最短标题
    titles: dict[str, str] = {}
    for p in (ROOT / "aia-runs").glob("wendao_bs_v2_*.jsonl"):
        for line in p.read_text(encoding="utf-8").splitlines():
            try:
                rec = json.loads(line)
            except Exception:  # noqa: BLE001
                continue
            for m in LINK.finditer(rec.get("a") or ""):
                fid, t = m.group(3), clean(m.group(1))
                if fid not in titles or len(t) < len(titles[fid]):
                    titles[fid] = t

    ok = fail = 0
    for i, (fid, rec) in enumerate(sorted(resolved.items()), 1):
        if not rec.get("url"):
            print(f"[{i}] ✗ 无地址 {fid[:8]}")
            fail += 1
            continue
        old = index.get(fid)
        if old and old.get("path") and (ROOT / old["path"]).exists():
            print(f"[{i}] 跳过（已有）{fid[:8]}")
            continue
        url = norm_url(rec["url"])
        name = basename(url)
        try:
            hdr = {"User-Agent": UA}
            if cookie:
                hdr["Cookie"] = cookie
            data = urllib.request.urlopen(urllib.request.Request(url, headers=hdr), timeout=180).read()
            if len(data) < 200:
                raise RuntimeError(f"文件过小 {len(data)}")
            mime = "pdf" if data[:4] == b"%PDF" else ("zip" if data[:2] == b"PK" else "bin")
            dest = WD / f"{fid[:8]}_{name}"
            dest.write_bytes(data)
            index[fid] = {
                "id": fid, "title": titles.get(fid) or name, "url": url,
                "path": str(dest.relative_to(ROOT)), "name": name,
                "bytes": len(data), "sha256": hashlib.sha256(data).hexdigest(),
                "kind": mime, "source": "wendao-sse-20261111",
                "fetched_at": time.strftime("%Y-%m-%dT%H:%M:%S"),
            }
            ok += 1
            print(f"[{i}] 收 {len(data)//1024:>6} KB  {name[:60]}")
        except Exception as e:  # noqa: BLE001
            index.setdefault(fid, {"id": fid, "title": titles.get(fid, "")})
            index[fid]["error"] = str(e)[:200]
            fail += 1
            print(f"[{i}] ✗ {fid[:8]} {names()}：{e}")
        INDEX.write_text(json.dumps(index, ensure_ascii=False, indent=2), encoding="utf-8")
        time.sleep(0.2)
    print(f"\n新增 {ok} 份，失败 {fail} 份，index 共 {len(index)}")


def names() -> str:
    return ""


if __name__ == "__main__":
    main()
