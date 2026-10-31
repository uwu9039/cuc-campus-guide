"""全库重复体检后的清理：只删与现存条目重复或已被明文废止的 51 条自动条目，
每条都已在 dup_groups.txt 中逐条核对，保留侧原件均在库内。"""
from __future__ import annotations

import json
import os
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
ITEMS = ROOT / "items.json"
BACKUP = ROOT / "_review_items" / "items_before_dedup.json"
LOG = ROOT / "_review_items" / "applied_dedup.txt"

DROPS: dict[str, tuple[str, str]] = {}

# 2017 版困难认定办法已被 2019 版明文废止（中传学字〔2019〕77 号第二十九条）
for pid, text in {
    "pt-b8301d75d4": "2017 版访谈小组流程，2019 版原文仍保留该做法",
    "pt-60ebe0769c": "2017 版特殊困难情形，2019 版有对应条目",
    "pt-a0135423ed": "2017 版资格复核，2019 版有对应条目",
    "pt-b5658dddb8": "2017 版不予认定情形，2019 版有对应条目",
}.items():
    DROPS[pid] = ("hbf8ecd720c7", text)

# 公费医疗：网页版与 2005 年原文逐字重复的 31 条，保留网页版独有的 12 条
for pid in {
    "pt-146513fd25", "pt-5c01e924d8", "pt-36090c549b", "pt-c57b25ea32",
    "pt-c63d6ce604", "pt-0ac0a419b8", "pt-923ace6f31", "pt-40bf2a10de",
    "pt-a862e5d2a0", "pt-c1006ccf6a", "pt-02cd63a745", "pt-ae09cb5644",
    "pt-024822a7bd", "pt-e6446e0e69", "pt-8a6d82d571", "pt-7d1bd5da71",
    "pt-767ddff313", "pt-ac61cf8eb4", "pt-4f6df73f6e", "pt-71c3753609",
    "pt-e70809d0e3", "pt-17f699adec", "pt-3904e51be3", "pt-98a486b528",
    "pt-76423da8f4", "pt-45dedba51f", "pt-12589d14c4", "pt-446863dfec",
    "pt-d4c369da5f", "pt-8ea318e967", "pt-a268ec6914",
}:
    DROPS[pid] = ("013d48a620", "与 2574a0e4 公费医疗办法逐字重复")

# 图书馆手册中与《中传学者文库章程》逐字重复的 2 条
for pid in {"pt-2b09328d55", "pt-3e56fe0562"}:
    DROPS[pid] = ("00f4cdcc", "与中传学者文库章程条目逐字重复")

# 补退选课通知所附退课申请表，与表格本页条目重复
DROPS["attf-6807748e19"] = ("att-6807748e19", "通知附件与退课申请表本页重复")

# 汇编重印的在读证明办法 5 条，与 3260eb0e 全本逐条包含
for pid in {
    "pt-a7230fc9eb", "pt-01340dc22e", "pt-32e8c6b097",
    "pt-e7b8801615", "pt-0809a34705",
}:
    DROPS[pid] = ("hb8d9e1380f5", "与 3260eb0e 在读证明办法逐条重复")

# 汇编重印的学士学位办法 5 条长段，已被 1ce888fb 逐条拆分覆盖
for pid in {
    "pt-3a439c306f", "pt-06597ed477", "pt-990e1c5e47",
    "pt-c6ddfed1ee", "pt-372c8941d5",
}:
    DROPS[pid] = ("hb9bc8c2793f", "与 1ce888fb 学士学位办法重复且颗粒更粗")

# 青马招募 docx 与网页版 3 条逐字重复
for pid in {"pt-25a3694427", "pt-c13eb771c0", "pt-35636312b0"}:
    DROPS[pid] = ("ba025472", "与 1d9773a9 青马招募网页版逐字重复")


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

    lines = [f"删除 {len(DROPS)} 条重复/废止条目，存留 {len(items)} 条"]
    for pid, (src, reason) in DROPS.items():
        lines.append(f"DROP {pid}  {src}  {reason}")
    LOG.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(f"已删除 {len(DROPS)} 条，当前 {len(items)} 条，备份 {BACKUP.name}")


if __name__ == "__main__":
    main()
