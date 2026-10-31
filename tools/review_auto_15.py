"""auto_15 人工复核：剔除过期招生简章（2023/2024 硕士、2024 港澳台、2026 博士）、
教职工差旅报销指南、校园新闻、校团委实践部介绍、校友会成立指南、公共实践场馆
消防责任书、重复的校园网 FAQ 与 2019 年旧学籍规定；保留本科毕业论文管理办法、
基层就业学费补偿与国家资助标准、2024 年研究生学籍规定、继续教育学位授予办法、
预科生管理办法、交流学习规定与水电购电办事信息。

判定原则：
- 过期年度：招生简章与节假日通知按年度更新，整源剔除
- 内部管理：报销、消防责任书、校友会组建、学生组织介绍不面向学生办事
- 重复条目：校园网 FAQ 已由 pt-45f6e704dd 等收录；2019 学籍规定已被 2024 版取代
- 政策条文：逐条看过，保留可检索的原文条款
"""
from __future__ import annotations

import json
import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
ITEMS = ROOT / "items.json"
CHUNK = ROOT / "_review_items" / "chunks" / "auto_15.txt"
BACKUP = ROOT / "_review_items" / "items_before_auto_15.json"
LOG = ROOT / "_review_items" / "applied_auto_15.txt"

DROP_SOURCES = {
    "5ee0f0ae": "公共实践场馆管理办法与消防安全责任书，以制作单位施工消防责任为主，预约要点已由 pt-c1daba422a、pt-0d8d352d16 等收录",
    "6efad535": "校团委实践部部门介绍与年度工作总结，没有办事步骤",
    "7190d6f9": "2024 年面向港澳台招收硕士研究生简章，招生年度已过期",
    "69382686": "2026 年博士学位研究生招生简章，属上一招生年度且含 2025 年学费标准",
    "7424a63b": "教职工国内差旅费报销与电子发票指南，不面向学生",
    "75d87713": "2023 年硕士研究生招生简章，招生计划、专业与日程已过期",
    "78137397": "校园新闻、活动动态与首页栏目内容，无办事信息",
    "63af4a53": "地区与学院校友会成立指南，面向校友工作部门，非学生办事",
    "74f0e198": "2024 年硕士研究生招生简章，招生计划与收费标准已过期",
    "5d67dc12": "2019 年研究生学籍管理规定，已被 2024 年修订版（7691069e）取代",
    "64448247": "校园网 FAQ 与既有条目重复（SSID、认证页、资费、宿舍网络已由 pt-45f6e704dd、pt-c348581ada、pt-68c812e2fd 等收录）",
    "66a1243f": "中央行政事业单位国有资产使用管理办法印发通知，非校园办事信息",
    "6677d716": "校园卡残句「信息化处负责…校备进行妥善保管」，校园卡已由 rule-6677d716 收录",
    "7684e018": "2024 年国庆假期图书馆闭馆通知，已过期",
}

DROPS = {
    # 66d43209 本科毕业论文管理办法：删目的套话、校内职责与人数上限
    "pt-507a193e54": "教学目的表述，无办事信息",
    "pt-1e08d4c04d": "统一要求与分类指导原则，无办事信息",
    "pt-bf06124a63": "选题结果报学部审定、教务处备案，属校内流程",
    "pt-4403275828": "指导教师指导人数上限，属教师工作量管理",
    "pt-4c4770b6bd": "超过指导人数需教务处批准，属教师工作量管理",
    "pt-772115cebf": "外聘指导教师指导人数上限，属教师工作量管理",
    "pt-9879f8859e": "指导教师工作态度表述，无办事信息",
    "pt-aec6080f82": "教务处职责，属校内管理分工",
    "pt-4cf7141ea9": "学部（直属学院）职责，属校内管理分工",
    "pt-b95fcd8865": "学部职责编号碎片「3.落实…检查与考核」",
    "pt-c4383092c2": "学部职责编号碎片「5.成立学部答辩委员会…」",
    "pt-e492de28d0": "学部职责编号碎片「4.…制定具体评分标准」",
    "pt-b568569fbf": "各学部制定实施细则，属校内管理分工",
    "pt-9be99d34e1": "学部工作总结报教务处，属校内管理流程",
    "pt-4387ccb409": "解释部门与印发日期，无办事信息",
    "pt-f2fcc4703c": "施行日期套话，无办事信息",
    # 61f74587 基层就业代偿与学生资助标准：删目的、定义与废止说明
    "pt-bb7cfd2f11": "引导毕业生基层就业的政策目的表述",
    "pt-ec15f79572": "制定本办法的依据套话，无办事信息",
    "pt-8b538a2e60": "学生资助资金的范围定义，无办事信息",
    "pt-dfc175e909": "中央财政资助资金的构成定义，无办事信息",
    "pt-8f217d47fd": "残句「奖励标准见研究生学业奖学金管理办法。（六）研究生国家助学金。」",
    "pt-263e8874f3": "旧国家奖学金评定办法的废止说明",
    # 7691069e 2024 研究生学籍规定：删执行起始年级、解释部门与答辩表决内部规则
    "pt-32b4226f40": "执行起始年级，无办事信息",
    "pt-8b06eb1fed": "解释部门与印发日期，无办事信息",
    "pt-d6dd319172": "毕业答辩委员会无记名投票的内部规则",
    # 75ebf118 继续教育学士学位授予办法：删依据、废止、内部审议流程与残句
    "pt-ed81a5e1db": "制定本办法的依据套话，无办事信息",
    "pt-4a30ddcbf3": "施行日期与旧细则废止说明",
    "pt-493a4515db": "校委会召开学位评定会议的内部流程",
    "pt-302a1d2c19": "残句「规定的标准。（五）不存在考试或学术违纪…」",
    "pt-cb08e29b20": "学院初审、本科生院复审、报校委会的内部流程",
    # 77917c5f 后勤水电：删家属区、商户与问句粘连残片
    "pt-2e31b6fbe2": "家属住户电表流程标题与「如何买水」问句粘连",
    "pt-32e2d0d9de": "定福庄北理 2 号院家属水费流程，非学生",
    "pt-3b5b1b1269": "商户购电咨询与「校内商户如何买水」问句粘连",
    "pt-4cfa8bc1f8": "家属购水咨询与「家属住户如何购电」问句粘连",
    "pt-51b9c0be0d": "家属区通用购电方式残片，无适用对象",
    "pt-5bc1207d0e": "商户预交电费方式，非学生",
    "pt-5cdbe84562": "家属区购电咨询与问句粘连",
    "pt-5d166b4605": "通用购电方式残片，无适用对象",
    "pt-5ef440cd3b": "商户预交水费方式，非学生",
    "pt-65a9ba6504": "「校内及中蓝学生公寓如何购电？」问句残片",
    "pt-8a53f1893e": "商户预交电费方式，非学生",
    "pt-c5842ebe8e": "家属区购水咨询与问句粘连",
    "pt-dd56210151": "家属水表绑定问句残片",
    "pt-ead1b731f4": "商户预交水费方式，非学生",
    # 78552e60 预科生管理办法：删制定依据
    "pt-03aede9310": "制定本办法的依据套话，无办事信息",
    # 6cbe728b 博士培养规定：删依据与解释印发
    "pt-b431fb6cf0": "解释部门与印发日期，无办事信息",
    "pt-e4b15c87e6": "制定本规定的依据套话，无办事信息",
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

    for pid, reason in DROPS.items():
        if pid not in chunk_set:
            raise SystemExit(f"目标条目不在 auto_15 分块内：{pid}")
        if pid not in items:
            raise SystemExit(f"条目不存在：{pid}")
        drops[pid] = reason

    log: list[str] = []
    for src, n in sorted(src_counts.items()):
        log.append(f"SOURCE {src}  删除 {n} 条：{DROP_SOURCES[src]}")
    for pid, reason in sorted(drops.items()):
        snippet = str(items[pid].get("answer") or "")[:50].replace("\n", " ")
        log.append(f"DROP  {pid}  {reason}  |  {snippet}")

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
