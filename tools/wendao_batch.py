"""一次性批量问「问道中传」：一个标签页跑完全部问题，结果增量写 JSONL，最后关标签页。

用法（必须在同一次 bash 调用里先跑 check-deps.mjs，让 proxy 活着）：
    python tools/wendao_batch.py <outfile.jsonl> [questions.txt]
"""
from __future__ import annotations

import json
import sys
import time
import uuid
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import cdp  # noqa: E402

ROOT = Path(__file__).resolve().parent.parent

ASK_JS = r"""
(() => {
  if (window.__wbusy) return "busy";
  window.__wans = ""; window.__wdone = false; window.__wbusy = true; window.__werr = "";
  const body = __BODY__;
  fetch("https://aihub.cuc.edu.cn/console/chat/sse", {
    method: "POST",
    headers: {"content-type": "application/json", "accept": "text/event-stream",
              "sid": localStorage.getItem("sid"),
              "Authorization": "Bearer " + (localStorage.getItem("token") || "")},
    credentials: "include",
    body: JSON.stringify(body)
  }).then(async (r) => {
    if (!r.ok) { window.__werr = "HTTP " + r.status; window.__wdone = true; window.__wbusy = false; return; }
    const rd = r.body.getReader(); const dec = new TextDecoder("utf-8"); let buf = "";
    while (true) {
      const {done, value} = await rd.read();
      if (done) break;
      buf += dec.decode(value, {stream: true});
      let i;
      while ((i = buf.indexOf("\n\n")) >= 0) {
        const chunk = buf.slice(0, i); buf = buf.slice(i + 2);
        const line = chunk.split("\n").find(l => l.startsWith("data:"));
        if (!line) continue;
        try {
          const o = JSON.parse(line.slice(5));
          if (o.data && o.data.length) { for (const d of o.data) { if (d && d.msg) window.__wans += d.msg; } }
          if (o.msg) window.__wans += o.msg;
          if (o.stop === true) window.__wdone = true;
        } catch (e) {}
      }
    }
    window.__wdone = true; window.__wbusy = false;
  }).catch(e => { window.__werr = String(e); window.__wdone = true; window.__wbusy = false; });
  return "started";
})()
"""

LINKS_JS = r"""
JSON.stringify([...document.querySelectorAll('a[href*="fileview"]')]
  .slice(__N__).map(a => ({text: (a.innerText || '').trim().replace(/\s+/g, ' ').slice(0, 160), href: a.href})))
"""


def main() -> None:
    out = Path(sys.argv[1] if len(sys.argv) > 1 else "aia-runs/wendao_bs.jsonl")
    qfile = Path(sys.argv[2]) if len(sys.argv) > 2 else ROOT / "tools" / "wendao_bs_questions.txt"
    out.parent.mkdir(parents=True, exist_ok=True)

    cfg = json.loads((ROOT / "aia-api.json").read_text(encoding="utf-8"))
    qs = [l.strip() for l in qfile.read_text(encoding="utf-8").splitlines() if l.strip() and not l.startswith("#")]
    print(f"问题数 {len(qs)}，输出 {out}", flush=True)

    tid = cdp.new("https://aihub.cuc.edu.cn/", wait=8)
    print("tid", tid, flush=True)
    has_token = "false"
    for _ in range(12):
        url = cdp.ev(tid, "location.href")
        title = cdp.ev(tid, "document.title")
        has_token = cdp.ev(tid, "String(!!localStorage.getItem('token'))")
        print("URL:", url, "| TITLE:", title, "| token:", has_token, flush=True)
        if has_token == "true":
            break
        if "login" in (url or "") or "auth" in (url or ""):
            break
        time.sleep(3)
    if has_token != "true":
        print("--- localStorage keys:", cdp.ev(tid, "JSON.stringify(Object.keys(localStorage))"), flush=True)
        print("--- cookie names:", cdp.ev(tid, "JSON.stringify(document.cookie.split('; ').map(x=>x.split('=')[0]))"), flush=True)
        print("--- body head:", cdp.ev(tid, "document.body.innerText").strip()[:400], flush=True)
    if has_token != "true":
        print("!! 未登录，放弃", flush=True)
        cdp.close(tid)
        return

    done_q = set()
    if out.exists():
        for line in out.read_text(encoding="utf-8").splitlines():
            try:
                done_q.add(json.loads(line)["q"])
            except Exception:  # noqa: BLE001
                pass
        print(f"已答 {len(done_q)} 题，跳过", flush=True)

    with out.open("a", encoding="utf-8") as fh:
        for i, q in enumerate(qs, 1):
            if q in done_q:
                continue
            t0 = time.time()
            body = dict(cfg)
            body.update({"content": q, "requestId": str(uuid.uuid4()),
                         "startTime": int(time.time() * 1000), "newRequest": True})
            n0 = cdp.ev(tid, "String(document.querySelectorAll('a[href*=\"fileview\"]').length)")
            cdp.ev(tid, ASK_JS.replace("__BODY__", json.dumps(body, ensure_ascii=False)))
            ans, err = "", ""
            deadline = time.time() + 150
            while time.time() < deadline:
                time.sleep(2)
                if cdp.ev(tid, "String(window.__wdone)") == "true":
                    break
            ans = cdp.ev(tid, "String(window.__wans)")
            err = cdp.ev(tid, "String(window.__werr)")
            try:
                links = json.loads(cdp.ev(tid, LINKS_JS.replace("__N__", n0 or "0")))
            except Exception:  # noqa: BLE001
                links = []
            rec = {"q": q, "i": i, "secs": round(time.time() - t0, 1), "chars": len(ans),
                   "a": ans, "err": err, "links": links,
                   "t": time.strftime("%Y-%m-%dT%H:%M:%S")}
            fh.write(json.dumps(rec, ensure_ascii=False) + "\n")
            fh.flush()
            print(f"[{i}/{len(qs)}] {q} → {len(ans)}字 / {len(links)}链接 / {rec['secs']}s {err}", flush=True)
            time.sleep(1)

    cdp.close(tid)
    print("done, tab closed", flush=True)


if __name__ == "__main__":
    main()
