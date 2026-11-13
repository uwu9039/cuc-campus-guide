"""问道批量提问（健壮版）：每 8 题换一个标签页，卡住 70 秒判失败并重试一次。

- 断点续跑：已答（chars>200）的题跳过
- 失败记录也落盘，下次会重问
用法：python tools/wendao_batch2.py <out.jsonl> <questions.txt>
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
RECYCLE = 8
STALL = 70
TRIES = 2

ASK_JS = r"""
(() => {
  window.__wans = ""; window.__wdone = false; window.__werr = "";
  const body = __BODY__;
  try {
    fetch("https://aihub.cuc.edu.cn/console/chat/sse", {
      method: "POST",
      headers: {"content-type": "application/json", "accept": "text/event-stream",
                "sid": localStorage.getItem("sid"),
                "Authorization": "Bearer " + (localStorage.getItem("token") || "")},
      credentials: "include", body: JSON.stringify(body)
    }).then(async (r) => {
      window.__status = r.status;
      if (!r.ok) { window.__werr = "HTTP " + r.status; window.__wdone = true; return; }
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
      window.__wdone = true;
    }).catch(e => { window.__werr = String(e); window.__wdone = true; });
  } catch (e) { window.__werr = String(e); window.__wdone = true; }
  return "go";
})()
"""


class Tab:
    def __init__(self) -> None:
        self.tid = None
        self.open()

    def open(self) -> None:
        self.close()
        self.tid = cdp.new("https://aihub.cuc.edu.cn/", wait=6)
        for _ in range(10):
            if cdp.ev(self.tid, "String(!!localStorage.getItem('token'))") == "true":
                return
            time.sleep(3)

    def close(self) -> None:
        if self.tid:
            try:
                cdp.close(self.tid)
            except Exception:  # noqa: BLE001
                pass
            self.tid = None


def ask_tab(tab: Tab, cfg: dict, q: str) -> tuple[str, str]:
    body = dict(cfg)
    body.update({"content": q, "requestId": str(uuid.uuid4()),
                 "startTime": int(time.time() * 1000), "newRequest": True})
    cdp.ev(tab.tid, ASK_JS.replace("__BODY__", json.dumps(body, ensure_ascii=False)))
    deadline = time.time() + STALL
    while time.time() < deadline:
        time.sleep(2)
        if cdp.ev(tab.tid, "String(window.__wdone)") == "true":
            break
    return cdp.ev(tab.tid, "String(window.__wans)"), cdp.ev(tab.tid, "String(window.__werr)")


def main() -> None:
    out = Path(sys.argv[1])
    qfile = Path(sys.argv[2])
    cfg = json.loads((ROOT / "aia-api.json").read_text(encoding="utf-8"))
    qs = [l.strip() for l in qfile.read_text(encoding="utf-8").splitlines()
          if l.strip() and not l.startswith("#")]

    done = set()
    if out.exists():
        for line in out.read_text(encoding="utf-8").splitlines():
            try:
                r = json.loads(line)
                if r.get("chars", 0) > 200:
                    done.add(r["q"])
            except Exception:  # noqa: BLE001
                pass
    todo = [q for q in qs if q not in done]
    print(f"总 {len(qs)} 题，已完成 {len(done)}，本次待问 {len(todo)}", flush=True)

    tab = Tab()
    with out.open("a", encoding="utf-8") as fh:
        for n, q in enumerate(todo, 1):
            if n > 1 and (n - 1) % RECYCLE == 0:
                tab.open()
            ans, err, tries = "", "", 0
            t0 = time.time()
            while tries < TRIES:
                tries += 1
                try:
                    ans, err = ask_tab(tab, cfg, q)
                except Exception as e:  # noqa: BLE001
                    ans, err = "", f"proxy:{e}"
                if len(ans) > 200:
                    break
                print(f"    重试 {q[:24]}（第{tries}次，err={err[:60]}）", flush=True)
                try:
                    tab.open()
                except Exception as e:  # noqa: BLE001
                    print("    换标签页失败", e, flush=True)
                    time.sleep(5)
            rec = {"q": q, "secs": round(time.time() - t0, 1), "chars": len(ans),
                   "ok": len(ans) > 200, "a": ans, "err": err,
                   "t": time.strftime("%Y-%m-%dT%H:%M:%S")}
            fh.write(json.dumps(rec, ensure_ascii=False) + "\n")
            fh.flush()
            print(f"[{n}/{len(todo)}] {q[:30]} → {len(ans)}字 {'OK' if rec['ok'] else 'FAIL'} {rec['secs']}s", flush=True)
    tab.close()
    print("done", flush=True)


if __name__ == "__main__":
    main()
