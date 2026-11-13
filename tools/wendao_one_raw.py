"""问一个问题，把 SSE 原始事件全量落盘（含参考文件的元数据），并可抓某个 fileId 的 fileview 页。"""
from __future__ import annotations

import json
import sys
import time
import uuid
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import cdp  # noqa: E402

ROOT = Path(__file__).resolve().parent.parent

RAW_JS = r"""
(() => {
  window.__evs = []; window.__wdone2 = false; window.__wbusy2 = true;
  const body = __BODY__;
  fetch("https://aihub.cuc.edu.cn/console/chat/sse", {
    method: "POST",
    headers: {"content-type": "application/json", "accept": "text/event-stream",
              "sid": localStorage.getItem("sid"),
              "Authorization": "Bearer " + (localStorage.getItem("token") || "")},
    credentials: "include", body: JSON.stringify(body)
  }).then(async (r) => {
    window.__status = r.status;
    if (!r.ok) { window.__wdone2 = true; return; }
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
        window.__evs.push(line.slice(5));
        try { const o = JSON.parse(line.slice(5)); if (o.stop === true) window.__wdone2 = true; } catch (e) {}
      }
    }
    window.__wdone2 = true; window.__wbusy2 = false;
  }).catch(e => { window.__err2 = String(e); window.__wdone2 = true; });
  return "go";
})()
"""


def main() -> None:
    q = sys.argv[1]
    out = Path(sys.argv[2]) if len(sys.argv) > 2 else ROOT / "aia-runs" / "wendao_raw_one.json"
    cfg = json.loads((ROOT / "aia-api.json").read_text(encoding="utf-8"))
    tid = cdp.new("https://aihub.cuc.edu.cn/", wait=8)
    for _ in range(10):
        if cdp.ev(tid, "String(!!localStorage.getItem('token'))") == "true":
            break
        time.sleep(3)
    body = dict(cfg)
    body.update({"content": q, "requestId": str(uuid.uuid4()),
                 "startTime": int(time.time() * 1000), "newRequest": True})
    cdp.ev(tid, RAW_JS.replace("__BODY__", json.dumps(body, ensure_ascii=False)))
    for _ in range(90):
        time.sleep(2)
        if cdp.ev(tid, "String(window.__wdone2)") == "true":
            break
    evs = json.loads(cdp.ev(tid, "JSON.stringify(window.__evs)"))
    print("events", len(evs), "status", cdp.ev(tid, "String(window.__status)"))
    out.write_text(json.dumps(evs, ensure_ascii=False, indent=1), encoding="utf-8")
    print("saved", out)
    cdp.close(tid)


if __name__ == "__main__":
    main()
