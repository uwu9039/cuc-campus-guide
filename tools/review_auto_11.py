"""auto_11 人工复核：剔除部门职能内部职责模板句、严重乱序的志愿答疑、
抓取时问题与答案粘连的食堂问答、被新规取代的 2009 退宿规定与 2015 年
研究生学籍管理规定等，保留公费医疗管理办法、2026 西部计划的原文条款。

判定原则：
- 内部职责：面向职能部门的岗位职责（「完成领导交办」等），不是学生办事信息
- 乱序粘连：问句与答句粘在一起、词序破碎到无法还原的整源剔除
- 已有条目：同一内容已由 rule-* / 专门条目完整收录的，不重复接入
- 政策条文：逐条看过，保留可检索的原文条款
"""
from __future__ import annotations

import json
import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
ITEMS = ROOT / "items.json"
CHUNK = ROOT / "_review_items" / "chunks" / "auto_11.txt"
BACKUP = ROOT / "_review_items" / "items_before_auto_11.json"
LOG = ROOT / "_review_items" / "applied_auto_11.txt"

DROP_SOURCES = {
    "2b17fefd": "各职能部门内部岗位职责模板句，非学生办事信息；学生相关电话已由 bumen-dianhua、qa-18fe5c7d-52 收录",
    "2afde8b9": "志愿答疑推文在抓取时词序严重破碎（如「o日无务」「系动负责人协」），无法还原原意",
    "28d54bca": "食堂问答网页的问题与答案粘连（如「…搭伙费北苑食堂可以用什么方式付款？」），食堂餐厅信息已由 shitang-* 条目收录",
    "2d160827": "2009 年退宿规定已被现行退宿流程取代，全文另见 rule-2d160827 与 sushe-tuixiu",
    "2e14e6ba": "2015 年研究生学籍管理规定已被 2019 年修订版取代，现行条款见 2024 年修订版 7691069e",
    "2e0ac4ee": "公共实践场馆条目文字残缺（「M80演播」「于服的」），不可读",
    "2cec291b": "国际处概况与因公出国流程已由 rule-2cec291b、jiaogong-yingong-chuguo 收录",
    "2c2d263a": "邮箱客户端设置步骤残句，校园邮箱开通流程已由 it-youxiang 收录",
}

DROPS = {
    "pt-1e85cfe46c": "调课服务说明与正文粘连，残留「(2)(3)(4)(5)(6)」编号碎片",
    "pt-3813102b39": "服务标题与正文粘连，内容另见 pt-607c06ee15",
    "pt-604a73bea8": "两句不同段落拼接，残留小节编号「2.强化过程管理」",
    "pt-796bee4c5c": "推文扫码关注引导语，无办事信息",
    "pt-0e6e5f0a33": "咨询群二维码有效期与个人微信号，属临时信息",
    "pt-55d4af82c6": "报名宣传语，无办事信息",
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
        raise SystemExit(f"目标条目不在 auto_11 分块内：{outside}")
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
