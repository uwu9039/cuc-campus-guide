"""向「问道中传」提问：用 CDP 注入 Unicode 转义后的 JS，避开 shell 编码问题。

用法：
    python tools/ask_aia.py "成绩单密封章几点能办？"
    python tools/ask_aia.py --batch questions.txt --out answers.md

注意：只问公开政策类问题，不涉及任何个人信息。
"""
from __future__ import annotations

import json
import sys
import time
import urllib.request
from pathlib import Path

CDP = "http://localhost:3456"
TAB_FILE = Path(__file__).resolve().parent.parent / ".cdp_tab"


def esc(text: str) -> str:
    out = []
    for ch in text:
        if ord(ch) < 128:
            out.append(ch.replace("\\", "\\\\").replace("'", "\\'"))
        else:
            out.append("\\u%04x" % ord(ch))
    return "".join(out)


def tab_id() -> str:
    if TAB_FILE.exists():
        return TAB_FILE.read_text(encoding="utf-8").strip()
    req = urllib.request.Request(f"{CDP}/new", data=b"https://aihub.cuc.edu.cn/", method="POST")
    tid = json.loads(urllib.request.urlopen(req, timeout=60).read())["targetId"]
    TAB_FILE.write_text(tid, encoding="utf-8")
    return tid


def ev(js: str) -> str:
    req = urllib.request.Request(f"{CDP}/eval?target={tab_id()}", data=js.encode("utf-8"), method="POST")
    return json.loads(urllib.request.urlopen(req, timeout=90).read()).get("value", "")


def ask(q: str, wait: float = 25.0) -> str:
    before = ev("document.body.innerText.length")
    js = (
        "(()=>{const ed=document.querySelector('.ql-editor');if(!ed)return 'no editor';"
        "ed.focus();ed.innerHTML='<p>%s</p>';"
        "ed.dispatchEvent(new InputEvent('input',{bubbles:true}));"
        "const b=document.querySelector('.send-btn');if(!b)return 'no btn';b.click();"
        "return 'sent'})()" % esc(q)
    )
    status = ev(js)
    if status != "sent":
        return f"[发送失败 {status}]"
    # 轮询等回答：正文长度不再增长即视为完成
    last, stable = before, 0
    for _ in range(int(wait * 2)):
        time.sleep(0.5)
        cur = ev("document.body.innerText.length")
        try:
            cur_i = int(cur)
        except ValueError:
            break
        if cur_i == last:
            stable += 1
            if stable >= 6:
                break
        else:
            stable = 0
            last = cur_i
    return ev("document.body.innerText.slice(-2000)")


def main() -> None:
    if "--batch" in sys.argv:
        src = Path(sys.argv[sys.argv.index("--batch") + 1])
        out = Path(sys.argv[sys.argv.index("--out") + 1]) if "--out" in sys.argv else Path("aia-answers.md")
        qs = [l.strip() for l in src.read_text(encoding="utf-8").splitlines() if l.strip()]
        lines = ["# 问道中传 回答记录", ""]
        for q in qs:
            print(f"问：{q}")
            a = ask(q)
            print(f"  答：{a[:80].replace(chr(10), ' ')}…")
            lines += [f"## {q}", "", "```", a.strip(), "```", ""]
            time.sleep(1)
        out.write_text("\n".join(lines), encoding="utf-8")
        print(f"已写入 {out}")
    else:
        q = sys.argv[1] if len(sys.argv) > 1 else "成绩单密封章几点能办？"
        print(ask(q))


if __name__ == "__main__":
    main()
