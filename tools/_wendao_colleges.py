"""探查中传官网「院系设置/教学单位」列表。"""
from __future__ import annotations

import json
import sys

sys.path.insert(0, __file__.rsplit("\\", 1)[0])
import cdp  # noqa: E402

tid = cdp.new("https://www.cuc.edu.cn/", wait=4)
print("tid", tid)
print("URL:", cdp.ev(tid, "location.href"))
print("TITLE:", cdp.ev(tid, "document.title"))

links = cdp.ev(tid, """
JSON.stringify([...document.querySelectorAll('a')].map(a=>({t:(a.innerText||'').trim().slice(0,30),h:a.href}))
 .filter(x=>x.t && /院系|学院|教学单位|机构|学部/.test(x.t)).slice(0,60))
""")
try:
    for x in json.loads(links):
        print(f"- {x['t']:24s} {x['h']}")
except Exception:  # noqa: BLE001
    print(links[:2000])

print("=== body head ===")
print(cdp.text(tid)[:500])
