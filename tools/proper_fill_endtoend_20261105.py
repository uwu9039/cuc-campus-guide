"""甲（候选池补面）落地后的端到端实测：这几句原先答「未收录」，现在走真实模型该答对。

打分、75/60/10 门槛与复核一行没动，只把「问句点名、池子里却没人带这个名字」时
带名的条目补进池尾。这里跑的是完整作答链（含模型），逐题记录路由台账与答句开头，
产出交人工逐条复看。

用法：./.venv/Scripts/python.exe -u tools/proper_fill_endtoend_20261105.py
"""
from __future__ import annotations

import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

import app  # noqa: E402

OUT = ROOT / "_review_items" / "proper_fill_endtoend_20261105.txt"

# 前三句是这次要救的；word/excel 是家族名登记后规则腿自己该落对的那两句；
# 后两句是负控：库里真没这个东西，补面不许凭空塞条目把「未收录」洗成错答。
CASES = [
    ("photoshop怎么安装", "该答"),
    ("ps怎么安装", "该答"),
    ("全家桶怎么下载", "该答"),
    ("adobe全家桶怎么下载", "该答"),
    ("word怎么激活", "该答"),
    ("excel怎么激活", "该答"),
    ("figma怎么导出", "负控·该说没收录"),
    ("校园卡丢了怎么补办", "负控·原有答法不许变"),
]


def main() -> None:
    lines: list[str] = []
    w = lines.append
    t_all = time.time()
    items = app.ITEMS
    w(f"items.json 载入 {len(items)} 条｜补面开关 PROPER_FILL_ADD={app.PROPER_FILL_ADD}")
    w("")
    for q, note in CASES:
        t0 = time.time()
        out = app.answer_question(q)
        el = time.time() - t0
        mr = out.get("model_route") or {}
        chosen = out.get("item") or {}
        parts = " ".join(str(p.get("text") or p.get("label") or "")
                         for p in (out.get("answers") or []) if isinstance(p, dict))
        w(f"=== {q}（{note}，{el:.1f}s）===")
        w(f"  命中 {chosen.get('id')}「{str(chosen.get('title'))[:40]}」 matched={out.get('matched')}")
        w(f"  模型腿 gate={mr.get('gate')} 池={mr.get('pool')} 模型分={mr.get('score')}"
          f" 规则分={mr.get('rule_score')}")
        w(f"  补面 {len(mr.get('proper_fill') or [])} 条 {mr.get('proper_fill') or []}")
        if mr.get("proper_map"):
            w(f"  映射 {mr.get('proper_map')}")
        w(f"  模型为什么这么挑：{str(mr.get('why'))[:120]}")
        w(f"  答句开头：{parts[:200]}")
        w("")
    text = "\n".join(lines)
    OUT.write_text(text, encoding="utf-8")
    print(text)
    print(f"总耗时 {time.time() - t_all:.0f}s，wrote {OUT}")


if __name__ == "__main__":
    main()
