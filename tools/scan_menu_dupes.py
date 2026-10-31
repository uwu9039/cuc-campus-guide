"""扫描现有问答入口里的候选菜单，找出点不同选项却落到同一结果的菜单。"""
from __future__ import annotations

import json
import sys
from collections import defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

import app  # noqa: E402


def questions() -> list[str]:
    out = [ln.strip() for ln in (ROOT / "aia-runs" / "questions-expanded.txt")
           .read_text(encoding="utf-8").splitlines() if ln.strip()]
    presets = json.loads((ROOT / "presets.json").read_text(encoding="utf-8"))
    for g in presets.get("groups") or []:
        out.extend(q for q in g.get("items") or [] if isinstance(q, str) and q.strip())
    menus = json.loads((ROOT / "topic-menus.json").read_text(encoding="utf-8"))
    for m in menus.get("menus") or []:
        out.extend(t for t in m.get("triggers") or [] if isinstance(t, str) and t.strip())
    seen: set[str] = set()
    uniq = []
    for q in out:
        if q not in seen:
            seen.add(q)
            uniq.append(q)
    return uniq


def sig(r: dict) -> str:
    it = r.get("item") or {}
    parts = tuple((a.get("label"), a.get("text")) for a in r.get("answers") or [])
    return json.dumps({
        "item": it.get("id"), "answers": parts,
        "dis": [o.get("title") for o in r.get("disambiguate") or []],
        "follow": [(f.get("key"), f.get("options")) for f in r.get("followups") or []],
        "blank": not parts and not (r.get("disambiguate") or r.get("followups")),
    }, ensure_ascii=False, sort_keys=True)


def main() -> None:
    rows = []
    for q in questions():
        try:
            r = app.answer_question(q, {})
        except Exception as e:  # noqa: BLE001
            rows.append(f"[{q}] 报错 {type(e).__name__}: {e}")
            continue
        opts = r.get("disambiguate") or []
        if len(opts) < 2:
            continue
        groups: dict[str, list[str]] = defaultdict(list)
        blanks: list[str] = []
        for o in opts:
            title = o.get("title") or ""
            try:
                sub = app.answer_question(title, {})
                key = sig(sub)
            except Exception as e:  # noqa: BLE001
                key = f"ERR {type(e).__name__}: {e}"
            groups[key].append(title)
            if (not sub.get("answers") and not sub.get("disambiguate")
                    and not sub.get("followups")):
                blanks.append(title)
        dup = {k: v for k, v in groups.items() if len(v) > 1}
        if dup or blanks:
            rows.append(f"\n[{q}] {len(opts)} 个选项，重复结果 {len(dup)} 组")
            for k, v in dup.items():
                rows.append("  重复：" + " | ".join(v))
            if blanks:
                rows.append("  空结果：" + " | ".join(blanks))
    out = ROOT / "_review_items" / "menu_dupes_1030.txt"
    out.write_text("\n".join(rows) or "没有发现重复结果的菜单", encoding="utf-8")
    print(f"扫描 {len(questions())} 个问法，问题菜单 {sum(1 for r in rows if r.startswith(chr(10)))} 个")
    print("写入", out)


if __name__ == "__main__":
    main()
