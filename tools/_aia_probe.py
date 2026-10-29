"""调试：在页面里发一次 chat/sse，把状态码与前 300 字打出来。"""
import json
import pathlib
import time
import urllib.parse
import urllib.request
import uuid

ROOT = pathlib.Path("D:/DSH/智能体节")
cfg = json.loads((ROOT / "aia-api.json").read_text(encoding="utf-8"))
cfg.update({"content": "转专业什么时候申请", "requestId": str(uuid.uuid4()),
            "startTime": int(time.time() * 1000), "newRequest": True})

tid = (ROOT / ".cdp_tab").read_text().strip()
js = (
    "fetch('https://aihub.cuc.edu.cn/console/chat/sse',{method:'POST',"
    "headers:{'content-type':'application/json','accept':'text/event-stream','sid':localStorage.getItem('sid'),'Authorization':'Bearer '+localStorage.getItem('token')},credentials:'include',"
    "body:JSON.stringify(" + json.dumps(cfg, ensure_ascii=False) + ")}).then(async r=>{"
    "const t=(await r.text()).slice(0,400);"
    "return JSON.stringify({status:r.status,ct:r.headers.get('content-type'),head:t})})"
)
raw = urllib.request.urlopen(
    urllib.request.Request("http://localhost:3456/eval?target=" + urllib.parse.quote(tid),
                           data=js.encode(), method="POST"), timeout=60).read().decode()
print(raw[:800])
