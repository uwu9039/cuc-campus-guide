"""广院通宣传片 · 最终素材采集（阶段 4）。

本机没有 puppeteer/playwright，采集走两条已验证的路：
  · Edge headless `--force-device-scale-factor` 出 2x / 4x 整页纹理（tools/shoot_frames.py 同款写法）
  · 同源注入代理补上「点页签、开面板、等答案」这些 URL 到不了的状态，
    并用 `--dump-dom` 把 layout.json（元素在整页坐标系里的 bbox）捞回来

不动业务代码：代理只给 text/html 响应追加一个 script，其余字节原样转发。

用法：
  .venv/Scripts/python.exe video-promo/tools/capture.py            # 全量
  .venv/Scripts/python.exe video-promo/tools/capture.py --only s3_answer,s5_quotes
"""
from __future__ import annotations

import argparse
import html
import json
import re
import subprocess
import tempfile
import threading
import urllib.error
import urllib.parse
import urllib.request
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
# 采集专用后端：8077（8000 留给开发/测试的那个 agent，两边互不打架）
UPSTREAM = "http://127.0.0.1:8077"
PROXY_PORT = 8099
EDGE = r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe"
TEX = ROOT / "video-remotion" / "public" / "textures" / "live"
LAYOUT = ROOT / "video-remotion" / "src" / "promo" / "layout.json"

# 每个镜头要什么状态、量哪些元素
SHOTS: dict[str, dict] = {
    "s0_hero": {
        "url": "/field",
        "sel": ["body", ".topbar", ".brand", ".hero h1", ".hero .kicker", ".rotate",
                ".composer", ".presets button", ".rail", ".inspector", ".inshead h2"],
    },
    "s2_typing": {
        "url": "/field",
        "type": "校园卡丢了怎么补",
        "sel": ["body", ".composer", ".composer .ask", "#q", ".presets", ".presets button"],
    },
    "s3_answer": {
        "url": "/field?q=校园卡丢了怎么补",
        "hi": [".card h2", ".card"],
        "sel": ["body", ".card", ".card h2", ".card .meta", ".step", ".badge", ".inspector",
                "#tabs [data-tab]", ".insbody", ".insfoot", "#stamp"],
    },
    "s4_overview": {
        "url": "/field?q=校园卡丢了怎么补",
        "click": "[data-tab=\"overview\"]",
        "sel": ["body", ".inspector", "#tabs", ".insbody .frow", ".insbody dl", ".insbody .row"],
    },
    "s5_quotes": {
        "url": "/field?q=校园卡丢了怎么补",
        "click": "[data-tab=\"quotes\"]",
        "sel": ["body", ".inspector", "#tabs", ".insbody .quote", ".insbody .qrow", ".insbody li"],
    },
    "s7_material": {
        "url": "/field?q=校园卡丢了怎么补",
        "click": "[data-tab=\"material\"]",
        "sel": ["body", ".inspector", "#tabs", ".insbody .mrow", ".insbody li", ".card"],
    },
    "s9_map": {
        "url": "/field?q=48教在哪",
        "click": "[data-panel=\"map\"]",
        "sel": ["body", ".panel", ".panelhead", "#mapcanvas", ".mapdetail", ".poirow"],
    },
    "s10_refuse": {
        "url": "/field?q=帮我写一封给辅导员的请假邮件要盖几个章",
        "sel": ["body", ".card", ".card h2", ".thread", ".toast"],
    },
    "s12_checklist": {
        "url": "/field?q=校园卡丢了怎么补",
        "click": "[data-tab=\"steps\"]",
        "sel": ["body", ".inspector", "#tabs", ".insbody", ".card .step", ".insfoot"],
    },
}

INJECT = """
(function(){
  var qs = new URLSearchParams(location.search);
  var typeText = qs.get("inject_type") || "";
  var clickSel = qs.get("inject_click") || "";
  var sels = (qs.get("inject_sel") || "").split("|").filter(Boolean);
  function box(el, pageH){
    var r = el.getBoundingClientRect();
    return {x: Math.round(r.left + scrollX), y: Math.round(r.top + scrollY),
            w: Math.round(r.width), h: Math.round(r.height)};
  }
  function dump(){
    var out = {pageW: document.documentElement.scrollWidth,
               pageH: Math.max(document.documentElement.scrollHeight, innerHeight),
               innerH: innerHeight, elements: {}};
    sels.forEach(function(sel){
      var list = Array.prototype.slice.call(document.querySelectorAll(sel)).slice(0, 12);
      if (list.length === 1) out.elements[sel] = box(list[0], out.pageH);
      else if (list.length > 1) out.elements[sel] = list.map(function(e){ return box(e, out.pageH); });
    });
    var pre = document.createElement("pre");
    pre.id = "__layout";
    pre.style.display = "none";
    pre.textContent = JSON.stringify(out);
    document.body.appendChild(pre);
    document.title = "READY";
  }
  function after(ms, fn){ setTimeout(fn, ms); }
  window.addEventListener("load", function(){
    after(1200, function(){
      var q = document.getElementById("q");
      if (typeText && q) {
        q.value = typeText;
        q.dispatchEvent(new Event("input", {bubbles: true}));
      }
      after(900, function(){
        if (clickSel) {
          var el = document.querySelector(clickSel);
          if (el) el.click();
        }
        after(1800, function(){
          var card = document.querySelector(".card");
          var ready = !qs.get("q") || !!card;
          if (ready) dump(); else after(2000, dump);
        });
      });
    });
  });
})();
"""


class Handler(BaseHTTPRequestHandler):
    def log_message(self, *a):
        pass

    def do_GET(self):
        parsed = urllib.parse.urlsplit(self.path)
        qs = urllib.parse.parse_qs(parsed.query)
        if parsed.path == "/__promo_inject.js":
            body = INJECT.encode("utf-8")
            self.send_response(200)
            self.send_header("Content-Type", "application/javascript; charset=utf-8")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)
            return

        upstream_qs = parsed.query.replace("inject_type", "_it").replace("inject_click", "_ic").replace("inject_sel", "_is")
        url = UPSTREAM + parsed.path + ("?" + urllib.parse.urlencode(
            {k: v[0] for k, v in qs.items() if not k.startswith("inject_")}, quote_via=urllib.parse.quote) if upstream_qs else "")
        try:
            with urllib.request.urlopen(url, timeout=60) as r:
                data = r.read()
                ctype = r.headers.get("Content-Type", "")
        except urllib.error.HTTPError as e:
            self.send_response(e.code)
            self.end_headers()
            return
        if "text/html" in ctype and "</body>" in data.decode("utf-8", "ignore"):
            tag = b'<script src="/__promo_inject.js"></script>'
            data = data.replace(b"</body>", tag + b"</body>")
        self.send_response(200)
        self.send_header("Content-Type", ctype or "application/octet-stream")
        self.send_header("Content-Length", str(len(data)))
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(data)


def run_edge(url: str, out: Path, w: int, h: int, dpr: int, dump: bool = False, timeout: int = 240) -> str | None:
    cmd = [EDGE, "--headless=new", "--disable-gpu", "--hide-scrollbars",
           f"--force-device-scale-factor={dpr}", f"--window-size={w},{h}",
           "--virtual-time-budget=20000",
           f"--user-data-dir={Path(tempfile.gettempdir()) / ('edge-cap-' + out.stem)}"]
    if dump:
        cmd.append("--dump-dom")
    else:
        cmd.append(f"--screenshot={out.as_posix()}")
    cmd.append(url)
    res = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout, encoding="utf-8", errors="ignore")
    return res.stdout if dump else None


def shot_url(name: str, spec: dict) -> str:
    split = urllib.parse.urlsplit(spec["url"])
    parts = dict(urllib.parse.parse_qsl(split.query))
    parts["inject_sel"] = "|".join(spec["sel"])
    if spec.get("type"):
        parts["inject_type"] = spec["type"]
    if spec.get("click"):
        parts["inject_click"] = spec["click"]
    return f"http://127.0.0.1:{PROXY_PORT}{split.path}?" + urllib.parse.urlencode(parts, quote_via=urllib.parse.quote)


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--only", default="")
    args = ap.parse_args()

    srv = ThreadingHTTPServer(("127.0.0.1", PROXY_PORT), Handler)
    threading.Thread(target=srv.serve_forever, daemon=True).start()
    TEX.mkdir(parents=True, exist_ok=True)
    LAYOUT.parent.mkdir(parents=True, exist_ok=True)

    layout = {"source": UPSTREAM, "viewport_css_px": 1920, "shots": {}}
    if LAYOUT.exists():
        layout = json.loads(LAYOUT.read_text(encoding="utf-8"))
        layout.setdefault("shots", {})

    want = [s.strip() for s in args.only.split(",") if s.strip()] or list(SHOTS)
    for name in want:
        spec = SHOTS[name]
        url = shot_url(name, spec)
        dom = run_edge(url, TEX / f"{name}.png", 1920, 1080, 1, dump=True) or ""
        m = re.search(r'<pre id="__layout"[^>]*>(.*?)</pre>', dom, re.S)
        if not m:
            print(f"  {name:<16} 没拿到 layout（页面没进 READY）")
            continue
        info = json.loads(html.unescape(m.group(1)))
        page_h = min(int(info["pageH"]), 2400)
        run_edge(url, TEX / f"{name}.png", 1920, page_h, 2)
        size = (TEX / f"{name}.png").stat().st_size if (TEX / f"{name}.png").exists() else 0
        print(f"  {name:<16} {size/1024:7.0f} KB  pageH {page_h}  元素 {len(info['elements'])}")

        entry = {"pageH": page_h, "pageW": info["pageW"], "dpr": 2, "png": f"textures/live/{name}.png",
                 "elements": info["elements"]}
        for sel in spec.get("hi", []):
            tag = re.sub(r"[^0-9A-Za-z]+", "_", sel).strip("_").lower()
            out = TEX / f"{name}__{tag}_4x.png"
            # 4x 只取视口（7680×4320），整页 4x 在 240s 内跑不完
            run_edge(url, out, 1920, 1080, 4, timeout=420)
            entry.setdefault("hi4x", {})[sel] = f"textures/live/{out.name}"
            print(f"    4x {tag:<18}{out.stat().st_size/1024:7.0f} KB" if out.exists() else f"    4x {tag} 失败")
        layout["shots"][name] = entry

    LAYOUT.write_text(json.dumps(layout, ensure_ascii=False, indent=1), encoding="utf-8")
    print(f"layout -> {LAYOUT.relative_to(ROOT)}  镜头 {len(layout['shots'])}")
    srv.shutdown()


if __name__ == "__main__":
    main()
