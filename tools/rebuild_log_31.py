"""重建 auto_31 的应用日志：脚本在写日志时因 f-string 类型错误中断，
数据已落盘但 applied_auto_31.txt 未生成。此处只读备份与分块重算，不改数据。"""
from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
ITEMS = ROOT / "items.json"
BACKUP = ROOT / "_review_items" / "items_before_auto_31.json"
CHUNK = ROOT / "_review_items" / "chunks" / "auto_31.txt"
LOG = ROOT / "_review_items" / "applied_auto_31.txt"

sys.path.insert(0, str(ROOT / "tools"))
import review_auto_31 as R  # noqa: E402


def main() -> None:
    before = json.loads(BACKUP.read_text(encoding="utf-8"))
    after = json.loads(ITEMS.read_text(encoding="utf-8"))
    items = {it["id"]: it for it in before["items"]}

    chunk_ids = [
        line.split()[0]
        for line in CHUNK.read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]
    chunk_set = set(chunk_ids)

    drops: dict[str, str] = {}
    for prefix, reason in R.DROP_SOURCES.items():
        for pid in chunk_ids:
            src = (items[pid].get("evidence", {}).get("answer", {}) or {}).get("src", "")
            if src.startswith(prefix):
                drops[pid] = reason

    for prefix, keep, reason in R.KEEP_SOURCES:
        missing = keep - chunk_set
        if missing:
            raise SystemExit(f"{prefix} 保留清单有误：{sorted(missing)}")
        for pid in chunk_ids:
            src = (items[pid].get("evidence", {}).get("answer", {}) or {}).get("src", "")
            if src.startswith(prefix) and pid not in keep:
                drops.setdefault(pid, reason)

    retitled = 0
    for pid in chunk_ids:
        if pid in drops:
            continue
        src = (items[pid].get("evidence", {}).get("answer", {}) or {}).get("src", "")
        for prefix, title in R.RETITLE.items():
            if not src.startswith(prefix) or pid in R.NO_RETITLE:
                continue
            for s in items[pid].get("source") or []:
                if str(s.get("title", "")).startswith("中国传媒大学关于专业学位博士研究生"):
                    retitled += 1
                    break

    expected_ids = [it["id"] for it in before["items"] if it["id"] not in drops]
    actual_ids = [it["id"] for it in after["items"]]
    if expected_ids != actual_ids:
        extra = set(actual_ids) - set(expected_ids)
        lost = set(expected_ids) - set(actual_ids)
        raise SystemExit(f"当前数据与重算不一致：多 {len(extra)} 条，少 {len(lost)} 条")

    kept = len(chunk_ids) - len(drops)
    if len(drops) != 353 or kept != 247 or retitled != 87:
        raise SystemExit(f"计数与中断时的输出不符：删除 {len(drops)} 存留 {kept} 标题 {retitled}")

    lines = [f"删除 {len(drops)} 条，存留 {kept} 条，更正来源标题 {retitled} 条"]
    for prefix, reason in R.DROP_SOURCES.items():
        n = sum(1 for p in chunk_ids if drops.get(p) == reason)
        lines.append(f"SOURCE {prefix}  删除 {n} 条：{reason}")
    for prefix, keep, reason in R.KEEP_SOURCES:
        lines.append(f"KEEP {prefix} {len(keep)}：{reason}")
    lines.append(f"RETITLE {retitled} 条 hb921f79 为 {R.RETITLE['hb921f79']}，专博 7 条保留原题")
    LOG.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print("\n".join(lines))


if __name__ == "__main__":
    main()
