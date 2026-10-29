"""向问道中传提问（走 execCommand 注入，能触发 Quill 的输入事件）。"""
from __future__ import annotations

import json
import sys
import time
import urllib.request
from pathlib import Path

CDP = "http://localhost:3456"
TAB = Path(__file__).resolve().parent.parent / ".cdp_tab"


def esc(t: str) -> str:
    return "".join(
        c.replace("\\", "\\\\").replace("'", "\\'") if ord(c) < 128 else "\\u%04x" % ord(c)
        for c in t
    )


def ev(js: str) -> str:
    tid = TAB.read_text(encoding="utf-8").strip()
    req = urllib.request.Request(f"{CDP}/eval?target={tid}", data=js.encode("utf-8"), method="POST")
    return json.loads(urllib.request.urlopen(req, timeout=90).read()).get("value", "")


def click_send() -> str:
    tid = TAB.read_text(encoding="utf-8").strip()
    req = urllib.request.Request(f"{CDP}/click?target={tid}", data=b".send-btn", method="POST")
    return urllib.request.urlopen(req, timeout=60).read().decode()


def ask(q: str, wait: int = 40) -> str:
    q_esc = esc(q)
    setup = (
        "(()=>{const ed=document.querySelector('.ql-editor');if(!ed)return 'no editor';"
        "ed.innerHTML='<p><br></p>';ed.focus();"
        "const sel=window.getSelection();const r=document.createRange();"
        "r.selectNodeContents(ed);r.collapse(false);sel.removeAllRanges();sel.addRange(r);"
        f"document.execCommand('insertText',false,'{q_esc}');"
        "return ed.innerText.trim()})()"
    )
    typed = ev(setup)
    print(f"  输入框内容：{typed[:40]}")
    click_send()
    last = -1
    for _ in range(wait * 2):
        time.sleep(0.5)
        t = ev("document.body.innerText")
        if len(t) == last:
            break
        last = len(t)
    return ev("document.body.innerText")


def main() -> None:
    q = sys.argv[1] if len(sys.argv) > 1 else "成绩单密封章几点能办？"
    text = ask(q)
    # 只保留最后一段（回答）
    print("\n--- 页面文本尾部 ---")
    print(text[-1200:] if len(text) > 1200 else text)


if __name__ == "__main__":
    main()
