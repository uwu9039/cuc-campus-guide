"""包体冒烟：直接打 _modelscope_bundle_full 起起来的 7861，验上下文链路。

不是跑源码树，是跑**包里的那份 app.py**——这是发布前最后一道。
"""
from __future__ import annotations

import json
import sys
import urllib.request

BASE = "http://127.0.0.1:7861"
ROWS: list[tuple[str, bool, str]] = []


def ask(payload: dict) -> dict:
    body = json.dumps(payload).encode()
    req = urllib.request.Request(BASE + "/api/ask", data=body, method="POST",
                                 headers={"Content-Type": "application/json"})
    with urllib.request.urlopen(req, timeout=240) as r:
        return json.loads(r.read())


def rec(name: str, ok: bool, detail: str) -> None:
    ROWS.append((name, ok, detail))
    print(f"[{'PASS' if ok else 'FAIL'}] {name}  {detail}", flush=True)


def body_of(d: dict) -> str:
    bits = [str(d.get("headline") or "")]
    for a in d.get("answers") or []:
        bits.append(str(a.get("text") or ""))
        for s in a.get("steps") or []:
            bits.append(str(s.get("what") if isinstance(s, dict) else s))
    if d.get("synth"):
        s = d["synth"]
        bits.append(str(s.get("conclusion") or ""))
        for L in s.get("layers") or []:
            bits.append(str(L.get("text") or ""))
    return " ".join(bits)


def main() -> None:
    # 1. 普通链路（/desk、/classic 走的就是这条：synth=false）
    d = ask({"text": "校园卡丢了怎么补办", "synth": False})
    item = (d.get("item") or {}).get("id")
    rec("N1 普通链路锚定", item == "xyk-buka" and bool(body_of(d)), f"item={item}")

    # 2. 首轮综合层：不给 context_item，靠 rank 兜底锚定
    d1 = ask({"text": "家庭经济困难认定怎么申请", "synth": True})
    it1 = (d1.get("item") or {}).get("id")
    src = (d1.get("model_route") or {}).get("ctx_source")
    conf = d1.get("confidence")
    ok1 = it1 == "zxj-guojia-runding" and src == "rank"
    rec("S1 首轮锚定", ok1, f"item={it1} ctx_source={src} conf={conf}")
    rec("S2 置信度非常数", conf != 0.78 and bool(d1.get("confidence_note")),
        f"conf={conf} note={d1.get('confidence_note')!r}")

    # 3. 第二轮：带上锚点问「申请要求」（这就是截图里丢上下文的那一步）
    hist = [{"role": "user", "content": "家庭经济困难认定怎么申请"},
            {"role": "assistant", "content": body_of(d1)[:300]}]
    d2 = ask({"text": "申请要求", "synth": True, "context_item": it1 or "zxj-guojia-runding",
              "messages": hist})
    b2 = body_of(d2)
    mixed = [x for x in ("转专业申请要求", "社团场地申请要求") if x in b2]
    rec("S3 追问接住上文", ("家庭经济困难学生认定申请表" in b2) and not mixed,
        f"材料={'家庭经济困难学生认定申请表' in b2} 串题={mixed or '无'} len={len(b2)}")

    # 4. 旧界面路径（synth=false + context_item）：至少不能是空卡
    d3 = ask({"text": "申请要求", "synth": False, "context_item": "zxj-guojia-runding",
              "messages": hist})
    b3 = body_of(d3)
    rec("N2 旧界面不空卡", bool(b3.strip()) or bool(d3.get("synth")),
        f"answers={len(d3.get('answers') or [])} len={len(b3)} item={(d3.get('item') or {}).get('id')}")

    bad = [r for r in ROWS if not r[1]]
    print(f"\n共 {len(ROWS)} 项：PASS {len(ROWS)-len(bad)} / FAIL {len(bad)}")
    if bad:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
