"""auto_10 人工复核：剔除新闻、活动、招新、班会类整源条目与导航拼接碎片，
保留退宿规定、图书馆读者守则、军事课实施办法、研究生学籍规定、公费医疗管理办法的原文条款。

判定原则：
- 整源剔除：新闻回顾、活动预告、招新名单、新生班会、学术论坛报道
- 导航拼接：菜单与正文粘在一起的条目直接删
- 空泛残句：离开上下文没有信息的条款碎片删
- 政策条文：逐条看过，保留可检索的原文条款
"""
from __future__ import annotations

import json
import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
ITEMS = ROOT / "items.json"
CHUNK = ROOT / "_review_items" / "chunks" / "auto_10.txt"
BACKUP = ROOT / "_review_items" / "items_before_auto_10.json"
LOG = ROOT / "_review_items" / "applied_auto_10.txt"

DROP_SOURCES = {
    "20260801-c20": "大地传媒坊答辩新闻、师资班招生与研讨会征稿报道",
    "20260909-c20": "新闻中心秋季招新推文",
    "20260919-c20": "学生会招新推文",
    "20260924-c20": "新生入学教育、迎新、军训动员与班级班会报道",
    "20260924-c43": "信息传播师资班与博士生论坛报道",
    "20261009-c20": "留学生参访、学生会名单、中秋活动、公考讲座、体育队招新等新闻",
    "20261009-c43": "金蔷薇学术季博士生论坛报道",
}

DROPS = {
    "pt-690e4dbf16": "导航栏与正文拼接，正文内容另有 pt-4d3a1cc034",
    "pt-1a14edd5a3": "空泛残句「特殊情况报学校审批」，无上下文",
    "pt-1fb6f6e909": "空泛残句「按照执行学校的相关规定」，无上下文",
    "pt-3d5c1f7c89": "空泛残句「其他均按教学管理规定执行」，无上下文",
    "pt-2f3ca72dd1": "空泛残句「个别职务如有调整」，无上下文",
    "pt-0c463e56bd": "附件标题与制定依据拼接，依据内容已由 pt-7720f3bdcc 收录",
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

    drops = dict(DROPS)
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
        raise SystemExit(f"目标条目不在 auto_10 分块内：{outside}")
    missing = [pid for pid in drops if pid not in items]
    if missing:
        raise SystemExit(f"条目不存在：{missing}")

    log: list[str] = []
    for src, n in sorted(src_counts.items()):
        log.append(f"SOURCE {src}  删除 {n} 条：{DROP_SOURCES[src]}")
    for pid, reason in sorted(drops.items()):
        log.append(f"DROP  {pid}  {reason}  |  {str(items[pid].get('answer') or '')[:50]}")

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
