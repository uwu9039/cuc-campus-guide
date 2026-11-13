"""用登录态浏览器解析 fileview 页里的真实文件地址（现在 fileview 要登录，裸 HTTP 会跳 SSO）。

输出：_wendao_resolved.json = {fileId: {url, name, ok, note}}
用法：python tools/wendao_resolve_urls.py [fileIds.txt]
"""
from __future__ import annotations

import json
import re
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import cdp  # noqa: E402

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / "_wendao_resolved.json"
LINK = re.compile(r"fileId=([0-9a-f]{32})")

JS = r"""
(async () => {
  const fid = "__FID__";
  const r = await fetch("https://aihub.cuc.edu.cn/doc/view/fileview?fileId=" + fid, {credentials: "include"});
  const t = await r.text();
  const m = t.match(/var\s+url\s*=\s*'([^']+)'/);
  return JSON.stringify({status: r.status, url: m ? m[1] : "", len: t.length,
                         title: (t.match(/<title>([^<]*)<\/title>/) || [])[1] || ""});
})()
"""


def main() -> None:
    fids: list[str] = []
    if len(sys.argv) > 1:
        txt = Path(sys.argv[1]).read_text(encoding="utf-8")
        fids = sorted(set(LINK.findall(txt) or re.findall(r"[0-9a-f]{32}", txt)))
    else:
        idx = json.loads((ROOT / "sources" / "wendao" / "index.json").read_text(encoding="utf-8"))
        seen = set()
        for p in (ROOT / "aia-runs").glob("wendao_bs_v2_*.jsonl"):
            for line in p.read_text(encoding="utf-8").splitlines():
                for m in LINK.finditer(line):
                    seen.add(m.group(1))
        fids = [f for f in sorted(seen) if f not in idx]
    print("待解析", len(fids), flush=True)

    tid = cdp.new("https://aihub.cuc.edu.cn/", wait=6)
    for _ in range(10):
        if cdp.ev(tid, "String(!!localStorage.getItem('token'))") == "true":
            break
        time.sleep(3)

    out = {}
    for i, fid in enumerate(fids, 1):
        try:
            raw = cdp.ev(tid, JS.replace("__FID__", fid))
            d = json.loads(raw)
        except Exception as e:  # noqa: BLE001
            d = {"status": 0, "url": "", "note": str(e)[:120]}
        out[fid] = d
        print(f"[{i}/{len(fids)}] {fid[:8]} status={d.get('status')} url={'有' if d.get('url') else '无'}", flush=True)
        time.sleep(0.2)
    OUT.write_text(json.dumps(out, ensure_ascii=False, indent=1), encoding="utf-8")
    cdp.close(tid)
    print("saved", OUT, "成功", sum(1 for v in out.values() if v.get("url")))


if __name__ == "__main__":
    main()
