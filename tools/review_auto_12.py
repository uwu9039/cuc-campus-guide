"""auto_12 人工复核：剔除国有资产、采购招标、家属区管理等内部管理文件，
过期的 2022/2024 博士招生简章，以及培训项目立项公示的导航拼接；
保留国家励志奖学金、考试违纪处理、课程成绩管理、在读证明、学硕培养规定、
2026 西部计划的原文条款，并清掉表格与签字栏残片。

判定原则：
- 内部管理：面向职能部门/教职工的管理办法，不是学生办事信息
- 过期文件：招生简章按年度更新，旧年份的招生计划和日程不再适用
- 拼接残片：页眉导航、附件签字栏、表格字段粘在一起无法阅读的删
- 政策条文：逐条看过，保留可检索的原文条款
"""
from __future__ import annotations

import json
import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
ITEMS = ROOT / "items.json"
CHUNK = ROOT / "_review_items" / "chunks" / "auto_12.txt"
BACKUP = ROOT / "_review_items" / "items_before_auto_12.json"
LOG = ROOT / "_review_items" / "applied_auto_12.txt"

DROP_SOURCES = {
    "3218ab4a": "财政部事业单位国有资产管理暂行办法，属内部资产管理，不面向学生办事",
    "3a172130": "国资处采购招标与资产处置内部流程，不面向学生办事",
    "35d42491": "家属区管理办法（住户、家委会、物业），非学生校园事务",
    "3511d430": "2022 年博士招生简章，招生计划与日程已过期",
    "32c632c9": "2024 年博士招生简章，招生计划与日程已过期",
    "32f02aa026": "培训项目立项公示，页眉导航与正文粘连",
    "3ada4747f1": "培训项目立项公示，页眉导航与正文粘连",
    "3da6836d": "2003 年西部计划政策问答，每月 600 元等标准已过期；现行政策见 305b6b81",
}

DROPS = {
    "pt-b4594c0624": "只有问句「参加西部计划主要做些什么？」，无答案",
    "pt-c4caf6a68d": "只有问句「招募选拔流程是怎样的？」，无答案",
    "pt-e72d0de2c5": "宣传语与公众号来源尾，无办事信息",
    "pt-ecebe3fb3a": "推文标题与报名信息粘连，报名信息另见 pt-9fb631a0c0",
    "pt-5c4272d8a3": "附件说明与证明正文粘连",
    "pt-7172dd3cfc": "审批表签字栏文字乱序，不可读",
    "pt-7e48b11549": "审批表签字栏文字乱序，不可读",
    "pt-4238c829c2": "落款、电话与有效期粘连，缺正文",
    "pt-d99b8606b3": "证明正文填空残句，无办理信息",
    "pt-f75fd90762": "附件表格字段粘连，不可读",
    "pt-2371dfe4bc": "证明套话「我校同意该生…」，无办理信息",
    "pt-5aa55dbfaf": "残句「处理，逾期不予受理。」，无上下文",
    "pt-3c98baf617": "解释部门与印发日期，无办事信息",
    "pt-8e7f973a88": "教务员汇总报送内部流程，不面向学生",
    "pt-86f1b70dd6": "教师未按时提交成绩的处理，不面向学生",
    "pt-79ae48a4c6": "教师延期录入成绩的内部申请流程，不面向学生",
    "pt-6c230b6ded": "任课教师提交成绩的内部流程，不面向学生",
    "pt-bbc9ef75bb": "新旧办法废止说明，无办事信息",
    "pt-2eb2e434e0": "课程学分表格字段粘连，不可读",
    "pt-d6bffbd032": "课程学分表格字段粘连，不可读",
    "pt-8c64cda8b8": "规定执行起始年级，无办事信息",
    "pt-e40118a0b3": "旧规定废止说明，无办事信息",
    "pt-39abc70876": "培养方案制定要求，属内部教学管理",
    "pt-5983e910df": "培养方案制定单位要求，属内部教学管理",
    "pt-cf76919e56": "要求培养单位制定细则，属内部教学管理",
    "pt-8df502764f": "培养方案定义，属内部教学管理",
    "pt-8d059999e1": "个人培养计划定义，无办事信息",
    "pt-e4b5ba4d41": "学校与培养单位两级管理分工，属内部管理",
    "pt-af4a9269ac": "培养目标口号，无办事信息",
    "pt-363e4f5ccc": "培养目标表述，无办事信息",
    "pt-aeec2493da": "培养目标表述，无办事信息",
    "pt-649db3d67b": "培养方式表述，无办事信息",
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
        raise SystemExit(f"目标条目不在 auto_12 分块内：{outside}")
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
