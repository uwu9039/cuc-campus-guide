"""auto_13 人工复核：剔除学生组织介绍、教代会/章程等内部治理条文、
教职工办公电话业务、过期考研考点须知与艺术类博士招生安排；
保留报修、辅修、就业手续、体育场馆、缴费、人脸闸机、硕士答辩、档案、
纪律处分、证书、游泳馆与信息化服务 FAQ 的原文条目。

判定原则：
- 学生组织：社团介绍与招新宣传，没有办事步骤
- 内部治理：教代会、学位委员会、章程条文，不面向学生日常办事
- 过期通知：考研考点须知、博士招生安排按年度更新
- 政策条文：逐条看过，保留可检索的原文条款
"""
from __future__ import annotations

import json
import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
ITEMS = ROOT / "items.json"
CHUNK = ROOT / "_review_items" / "chunks" / "auto_13.txt"
BACKUP = ROOT / "_review_items" / "items_before_auto_13.json"
LOG = ROOT / "_review_items" / "applied_auto_13.txt"

DROP_SOURCES = {
    "3da6836d": "2003 年西部计划政策问答，标准已过期；现行政策见 305b6b81",
    "402ecf2831": "校团委各学生组织介绍与招新宣传，没有办事步骤",
    "4647e42b": "艺术类博士招生综合考核安排，按年度更新且非校园日常事务",
    "48c034fb": "教职工办公电话新装、移机与停机保号内部流程",
    "52fae1ee": "2025 年硕士研究生招生考试 1133 考点须知，已过期",
    "533d23ad": "学校章程与教代会、学位委员会等内部治理条文",
}


def main() -> None:
    dry = "--dry-run" in sys.argv
    original = ITEMS.read_text(encoding="utf-8")
    data = json.loads(original)
    items = {it["id"]: it for it in data["items"]}

    chunk_ids = []
    for line in CHUNK.read_text(encoding="utf-8").splitlines():
        if line.strip():
            chunk_ids.append(line.split()[0])
    chunk_set = set(chunk_ids)

    drops: dict[str, str] = {}
    src_counts: dict[str, int] = {}
    for pid in chunk_ids:
        src = (items[pid].get("evidence", {}).get("answer", {}) or {}).get("src", "")
        for prefix, reason in DROP_SOURCES.items():
            if src.startswith(prefix):
                drops[pid] = reason
                src_counts[prefix] = src_counts.get(prefix, 0) + 1
                break

    outside = sorted(set(drops) - chunk_set)
    if outside:
        raise SystemExit(f"目标条目不在 auto_13 分块内：{outside}")
    missing = [pid for pid in drops if pid not in items]
    if missing:
        raise SystemExit(f"条目不存在：{missing}")

    log: list[str] = []
    for src, n in sorted(src_counts.items()):
        log.append(f"SOURCE {src}  删除 {n} 条：{DROP_SOURCES[src]}")
    for pid, reason in sorted(drops.items()):
        log.append(f"DROP  {pid}  {reason}  |  {str(items[pid].get('title') or '')[:50]}")

    survivors = [pid for pid in chunk_ids if pid not in drops]
    print(f"整源剔除 {len(src_counts)} 个来源，删除 {len(drops)} 条，"
          f"当前 {len(data['items'])} 条，存留 {len(survivors)} 条")

    if dry:
        print("\n".join(log))
        return

    for pid in drops:
        data["items"].remove(items[pid])

    if not BACKUP.exists():
        BACKUP.write_text(original, encoding="utf-8")
    tmp = ITEMS.with_suffix(".json.tmp")
    tmp.write_text(json.dumps(data, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
    os.replace(tmp, ITEMS)
    LOG.write_text("\n".join(log) + "\n", encoding="utf-8")
    print(f"已写回，剩余 {len(data['items'])} 条；备份 {BACKUP.relative_to(ROOT)}；日志 {LOG.relative_to(ROOT)}")


if __name__ == "__main__":
    main()
