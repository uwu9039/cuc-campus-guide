"""反问槽位一致性检查：有分支的步骤必须问得出对应条件。

规则：
- 每个 steps[*].if 的键，条目必须有同名 slot；
- 条件值必须在该 slot 的 options 里；
- slot key 不重复；
- decides 只能指向答案里真实存在的面（overview / FOCUS_LABEL）。
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
FOCUS = {"overview", "note", "contact", "fee", "window", "hours", "location",
         "material", "duration", "pitfalls", "steps"}


def main() -> int:
    items = json.loads((ROOT / "items.json").read_text(encoding="utf-8"))["items"]
    problems: list[str] = []
    slot_items = 0
    branch_steps = 0
    for it in items:
        slots = it.get("slots") or []
        if slots:
            slot_items += 1
        by_key = {}
        for s in slots:
            key = s.get("key")
            if not key:
                problems.append(f"{it['id']}：slot 缺 key")
                continue
            if key in by_key:
                problems.append(f"{it['id']}：slot {key} 重复")
            by_key[key] = s
            if not s.get("ask"):
                problems.append(f"{it['id']}：slot {key} 没写问句")
            if not s.get("options"):
                problems.append(f"{it['id']}：slot {key} 没有选项")
            bad = set(s.get("decides") or []) - FOCUS
            if bad:
                problems.append(f"{it['id']}：slot {key} decides 指向不存在的面 {sorted(bad)}")
        for n, st in enumerate(it.get("steps") or []):
            cond = st.get("if") or {}
            if not cond:
                continue
            branch_steps += 1
            for key, val in cond.items():
                s = by_key.get(key)
                if not s:
                    problems.append(f"{it['id']}：steps.{n} 需要 {key}，但没有对应反问")
                    continue
                if val not in (s.get("options") or []):
                    problems.append(f"{it['id']}：steps.{n} 的 {key}={val} 不在选项里")

    print(f"条目 {len(items)}，带反问 {slot_items} 条，条件分支步骤 {branch_steps} 个")
    if problems:
        print(f"✗ {len(problems)} 处不一致：")
        for p in problems[:20]:
            print("  -", p)
        return 1
    print("✓ 每个分支都问得出来，条件值与选项一致")
    return 0


if __name__ == "__main__":
    sys.exit(main())
