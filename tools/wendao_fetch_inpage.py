"""在登录态页面里取文件字节（debot 文档要 cookie），base64 分块传回，落盘。

用法：python tools/wendao_fetch_inpage.py
依赖 _wendao_resolved.json（同目录脚本生成）。
"""
from __future__ import annotations

import base64
import hashlib
import json
import re
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import cdp  # noqa: E402

ROOT = Path(__file__).resolve().parent.parent
WD = ROOT / "sources" / "wendao"
INDEX = WD / "index.json"
RESOLVED = ROOT / "_wendao_resolved.json"
CHUNK = 400_000

START_JS = r"""
(() => {
  window.__b64 = ""; window.__wdone = false; window.__werr = ""; window.__ct = "";
  const u = __URL__;
  fetch(u, {credentials: "include"}).then(async (r) => {
    window.__ct = r.headers.get("content-type") || "";
    if (!r.ok) { window.__werr = "HTTP " + r.status; window.__wdone = true; return; }
    const buf = new Uint8Array(await r.arrayBuffer());
    let s = ""; const step = 0x8000;
    for (let i = 0; i < buf.length; i += step) {
      s += String.fromCharCode.apply(null, buf.subarray(i, i + step));
    }
    window.__b64 = btoa(s);
    window.__wdone = true;
  }).catch(e => { window.__werr = String(e); window.__wdone = true; });
  return "go";
})()
"""


def clean_title(t: str) -> str:
    t = re.sub(r"\s+", " ", t).strip()
    return t[:120] or "未命名"


def main() -> None:
    resolved = json.loads(RESOLVED.read_text(encoding="utf-8"))
    index = json.loads(INDEX.read_text(encoding="utf-8"))
    titles: dict[str, str] = {}
    link = re.compile(r"\[([^\]]{2,300}?)\]\(https://aihub\.cuc\.edu\.cn/doc/view/fileview\?fileId=([0-9a-f]{32})")
    for p in (ROOT / "aia-runs").glob("wendao_bs_v2_*.jsonl"):
        for line in p.read_text(encoding="utf-8").splitlines():
            try:
                rec = json.loads(line)
            except Exception:  # noqa: BLE001
                continue
            for m in link.finditer(rec.get("a") or ""):
                fid, t = m.group(2), re.sub(r"\s+", " ", m.group(1)).strip()
                if fid not in titles or len(t) < len(titles[fid]):
                    titles[fid] = t

    tid = cdp.new("https://aihub.cuc.edu.cn/", wait=6)
    for _ in range(10):
        if cdp.ev(tid, "String(!!localStorage.getItem('token'))") == "true":
            break
        time.sleep(3)

    ok = fail = 0
    for i, (fid, rec) in enumerate(sorted(resolved.items()), 1):
        url = rec.get("url") or ""
        if not url:
            print(f"[{i}] ✗ 无地址 {fid[:8]}")
            fail += 1
            continue
        old = index.get(fid)
        if old and old.get("path") and (ROOT / old["path"]).exists() and old.get("bytes", 0) > 20_000:
            print(f"[{i}] 跳过（已有）{fid[:8]}")
            continue
        if url.startswith("//"):
            url = "https:" + url
        try:
            cdp.ev(tid, START_JS.replace("__URL__", json.dumps(url, ensure_ascii=False)), timeout=30)
            done = False
            miss = 0
            for _ in range(180):
                st = cdp.ev(tid, "String(window.__wdone)", timeout=20).strip()
                if st == "true":
                    done = True
                    break
                if st == "undefined":
                    miss += 1
                    if miss >= 3:
                        raise RuntimeError("页面上下文被重置")
                time.sleep(1)
            if not done:
                raise RuntimeError("取文件超时")
            ct = cdp.ev(tid, "String(window.__ct)", timeout=20)
            err = cdp.ev(tid, "String(window.__werr)", timeout=20)
            if err or "html" in ct:
                print(f"[{i}] ✗ {fid[:8]} ct={ct[:30]} err={err[:60]}", flush=True)
                fail += 1
                continue
            total = int(cdp.ev(tid, "String(window.__b64.length)", timeout=20) or 0)
            parts = []
            pos = 0
            while pos < total:
                seg = cdp.ev(tid, f"window.__b64.slice({pos},{pos + CHUNK})", timeout=60)
                parts.append(seg)
                pos += CHUNK
            b64 = "".join(parts)
            cdp.ev(tid, "window.__b64=''", timeout=20)
            data = base64.b64decode(b64)
        except Exception as e:  # noqa: BLE001
            print(f"[{i}] ✗ {fid[:8]} 取回失败：{e}", flush=True)
            fail += 1
            try:
                tid = cdp.new("https://aihub.cuc.edu.cn/", wait=6)
                for _ in range(10):
                    if cdp.ev(tid, "String(!!localStorage.getItem('token'))", timeout=20) == "true":
                        break
                    time.sleep(3)
            except Exception as e2:  # noqa: BLE001
                print("    换标签页失败", e2, flush=True)
            continue
        mime = "pdf" if data[:4] == b"%PDF" else ("zip" if data[:2] == b"PK" else "bin")
        if mime == "bin" and len(data) < 5000:
            print(f"[{i}] ✗ {fid[:8]} 内容可疑 {len(data)}B")
            fail += 1
            continue
        name = re.sub(r'[\\/:*?"<>|]', "_", (rec.get("url") or "").rsplit("/", 1)[-1])
        name = re.sub(r"\.(pdf|docx?|xlsx?)$", "", name, flags=re.I) or fid[:8]
        ext = {"pdf": ".pdf", "zip": ".zip", "bin": ".bin"}[mime]
        dest = WD / f"{fid[:8]}_{name[:80]}{ext}"
        dest.write_bytes(data)
        index[fid] = {
            "id": fid, "title": clean_title(titles.get(fid, name)), "url": url,
            "path": str(dest.relative_to(ROOT)), "name": name + ext,
            "bytes": len(data), "sha256": hashlib.sha256(data).hexdigest(),
            "kind": mime, "source": "wendao-sse-20261111",
            "fetched_at": time.strftime("%Y-%m-%dT%H:%M:%S"),
        }
        INDEX.write_text(json.dumps(index, ensure_ascii=False, indent=2), encoding="utf-8")
        ok += 1
        print(f"[{i}] 收 {len(data)//1024:>6} KB  {dest.name[:60]}")
    cdp.close(tid)
    print(f"\n新增 {ok}，失败 {fail}，index {len(index)}")


if __name__ == "__main__":
    main()
