"""重复体检第二批：汇编重印与人工条目逐字重复的 9 条，保留侧均在库内可查。"""
from __future__ import annotations

import json
import os
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
ITEMS = ROOT / "items.json"
BACKUP = ROOT / "_review_items" / "items_before_dedup2.json"
LOG = ROOT / "_review_items" / "applied_dedup2.txt"

DROPS = {
    "pt-f81d86e968": ("f2edb8b4", "与人工条目 tuimian-tiaojian 逐字重复"),
    "pt-ad782b6fe3": ("hbb91b1b03dc", "汇编重印毕业论文办法，与 a95c853a 重复"),
    "pt-e0db4996a2": ("hbb91b1b03dc", "汇编重印毕业论文办法，与 a95c853a 重复"),
    "pt-af9b72e27f": ("hbb91b1b03dc", "汇编重印毕业论文办法，与 a95c853a 重复"),
    "pt-4989d0e9d8": ("hbb91b1b03dc", "汇编重印毕业论文办法，与 a95c853a 重复"),
    "pt-9f3be009d8": ("hbb91b1b03dc", "汇编重印毕业论文办法，与 a95c853a / 66d43209 重复"),
    "pt-7f5c65e9a5": ("20220922-c8508a199117", "与 4c7f7c48 统一身份认证账号激活重复"),
    "pt-b3e62235be": ("20220922-c8508a199117", "与 4c7f7c48 统一身份认证账号激活重复"),
    "pt-a24b9e4e65": ("hbd9d7bc1592", "汇编重印学位证书管理办法，与 4dafbf1a 重复"),
}


def main() -> None:
    original = ITEMS.read_text(encoding="utf-8")
    data = json.loads(original)
    items = {it["id"]: it for it in data["items"]}

    missing = [pid for pid in DROPS if pid not in items]
    if missing:
        raise SystemExit(f"待删条目不存在：{missing}")
    wrong = []
    for pid, (src, _) in DROPS.items():
        got = (items[pid].get("evidence", {}).get("answer", {}) or {}).get("src", "")
        if got != src:
            wrong.append((pid, src, got))
    if wrong:
        raise SystemExit(f"来源不符：{wrong}")

    for pid, (src, reason) in DROPS.items():
        print(f"DROP {pid}  {src}  {reason}  |  {(items[pid].get('answer') or '')[:60]}")

    BACKUP.write_text(original, encoding="utf-8")
    for pid in DROPS:
        items.pop(pid, None)
    data["items"] = [it for it in data["items"] if it["id"] in items]
    tmp = ITEMS.with_suffix(".json.tmp")
    tmp.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
    os.replace(tmp, ITEMS)

    lines = [f"删除 {len(DROPS)} 条重复条目，存留 {len(items)} 条"]
    for pid, (src, reason) in DROPS.items():
        lines.append(f"DROP {pid}  {src}  {reason}")
    LOG.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(f"已删除 {len(DROPS)} 条，当前 {len(items)} 条，备份 {BACKUP.name}")


if __name__ == "__main__":
    main()
