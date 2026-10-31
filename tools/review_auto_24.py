"""auto_24 人工复核：旧版大学英语与学籍规定、研究生入学须知、收费与教室规则。

判定原则（与 auto_17/18/19/20/21/22/23 一致）：
- 保留学生可执行的规则、期限、费用、材料、电话与后果
- 删除校内部门职责、委员会组成、经费与考核、制定目的、施行与解释条款
- 删除面向教职工、后勤职工、项目负责人的程序性文字
- 删除残句、表格粘连、模板占位与无信息宣传语

整源判断：
- att-e2ec：2018 版大学英语规定，四六级赠 2 学分规则自 2022 级起废止
  （pt-ddf4b65303「自2022级起，四六级成绩不可兑换奖励学分，不在成绩单显示」），
  三级分级与 8+4 学分结构已被 dcc459b1 的 A+/A/B/C 现行方案覆盖
- att-e569：系（部）设置及负责人聘任，面向教师与管理岗
- att-e7dc：因公出差审批单，面向教职工
- att-ebd6：在线开放课程管理办法，面向课程建设与教师工作量
- att-f77f：博士研究生培养工作规定，面向培养管理且表格行粘连
- att-fc54：成绩等级证明空白模板，无办理规则
- att-fc5d：传媒博物馆办展安全承诺书，模板套语
- b2476067：2022 年硕士招生简章，已被库内 2025 年硕士招生简章取代
- b9812c3c：资金支付管理办法，面向财务经办与审批人
- b7460e91：2021 版本科生学籍管理规定，已被中传教字〔2025〕195 号完整取代；
  学分退学、学业留级、休学复学、保留学籍、请假、缓考、转学、毕业结业、
  最长年限、旷课处分均有 2025 版或现行专项条目覆盖

保留来源：
- att-f527：新生选课系统网址与统一身份认证、通识/体育模块、推荐浏览器
- b603a9cb：缴费注册、退学按月退学费、退宿按月退住宿费、休学与保留入学资格收费、
  转专业与延期学费、服务性收费自愿、收费公示
- b6592b35：2026 级研究生报到、档案、户口、党团关系、学费、住宿、资助与材料
- b739c4e2：WPS 365 的 SSO 登录、校园内网/VPN 要求、重装说明与 WPS 灵犀
- b825a538：食堂消费须走校园卡渠道才享基本伙补助
- b839cb7a：教室借用事由、提前 1 个工作日、违约三次、行为规范与损坏赔偿；
  自习室开放与提前 3 个工作日规则以 bd7b1d20 现行指南为准，不再保留旧表述
- b863d755：校庆活动与银行推广均已过期，只保留美食广场与北苑二层营业信息
"""
from __future__ import annotations

import json
import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
ITEMS = ROOT / "items.json"
CHUNK = ROOT / "_review_items" / "chunks" / "auto_24.txt"
BACKUP = ROOT / "_review_items" / "items_before_auto_24.json"
LOG = ROOT / "_review_items" / "applied_auto_24.txt"

DROP_SOURCES = {
    "att-e2ec": "2018 版大学英语规定，四六级赠 2 学分自 2022 级起废止，分级与学分结构已被现行方案覆盖",
    "att-e569": "系（部）设置及负责人聘任，面向教师与管理岗",
    "att-e7dc": "因公出差审批单，面向教职工",
    "att-ebd6": "在线开放课程管理办法，面向课程建设与教师工作量",
    "att-f77f": "博士研究生培养工作规定，面向培养管理且表格行粘连",
    "att-fc54": "成绩等级证明空白模板，无办理规则",
    "att-fc5d": "传媒博物馆办展安全承诺书，模板套语",
    "b2476067": "2022 年硕士招生简章，已被库内 2025 年硕士招生简章取代",
    "b9812c3c": "资金支付管理办法，面向财务经办与审批人",
    "b7460e91": "2021 版本科生学籍管理规定，已被中传教字〔2025〕195 号完整取代",
}

# 新生选课通知：网址与认证、通识/体育模块、推荐浏览器
att_f527_KEEP = {"pt-35690eddad", "pt-f2b10b27ca", "pt-1f8ebeb370"}
att_f527_REASON = "示例提示、课表界面与已由现行选课通知覆盖的操作步骤"

# 收费管理办法：只保留学生缴费、退费、休学与公示规则
b603a9cb_KEEP = {
    "pt-882d433da4", "pt-d0765a05c9", "pt-27dc9844d1", "pt-452070027d",
    "pt-2d2adb94b3", "pt-9a4aadeb0e", "pt-df129b5a7c", "pt-99bcb592c4",
    "pt-4d5ca8fe3e", "pt-9361f5c788", "pt-dcf13f8ccc", "pt-3e2303021d",
    "pt-fc9732221c", "pt-6662ff6bec", "pt-ba0f419b80", "pt-d1eb2085b1",
}
b603a9cb_REASON = "部门职责、立项审批、票据与监督检查等校内管理流程"

# 研究生入学须知：删除奖助名单碎片、范围说明与抽取残句
b6592b35_DROP = {
    "pt-13abd2628b", "pt-f25612c7a8", "pt-d09d5df24c", "pt-5e81dee69d",
    "pt-62e6f99d32", "pt-455c145cbd", "pt-ea0b9deefe", "pt-5ab52f7fa1",
    "pt-7d12945f83", "pt-bc3913038c", "pt-5beac90e89",
}
b6592b35_REASON = "奖助项目名单碎片、须知对象说明、导航句与带①②占位的抽取残句"

# WPS 365：只保留登录方式、内网/VPN、重装说明与 WPS 灵犀
b739c4e2_KEEP = {"pt-f3b9ddcf49", "pt-041bf09eb7", "pt-b7570e4523", "pt-edf4033ab0"}
b739c4e2_REASON = "会员权益推广、扫码文案与页面导航等宣传语"

# 公共教室：保留学生行为规范、借用事由与违约后果
b839cb7a_KEEP = {
    "pt-048090e3e5", "pt-06d9aeaa3b", "pt-3758498c7c", "pt-4134e2df42",
    "pt-7ec95311e5", "pt-ce1ff6cf7c", "pt-c13cbebd46", "pt-6b3e1952e3",
    "pt-3f56f85592",
}
b839cb7a_REASON = "中心与后勤职责、检查考核、借用时限旧表述（现行指南为提前 3 个工作日）"

# 校庆返校日：活动已结束，只留两处长期营业信息
b863d755_KEEP = {"pt-967b7d3b22", "pt-a06596a0c1"}
b863d755_REASON = "2024 年校庆活动、银行联名卡推广、停车与文创宣传已过期"

# 误扣款公告：整条保留
b825a538_KEEP = {"pt-7c9244553b"}
b825a538_REASON = ""

KEEP_SOURCES = [
    ("att-f527", att_f527_KEEP, att_f527_REASON),
    ("b603a9cb", b603a9cb_KEEP, b603a9cb_REASON),
    ("b739c4e2", b739c4e2_KEEP, b739c4e2_REASON),
    ("b839cb7a", b839cb7a_KEEP, b839cb7a_REASON),
    ("b863d755", b863d755_KEEP, b863d755_REASON),
    ("b825a538", b825a538_KEEP, b825a538_REASON),
]


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

    unused = set(DROP_SOURCES) - set(src_counts)
    if unused:
        raise SystemExit(f"整源剔除清单有误，分块内找不到：{sorted(unused)}")

    for prefix, keep, reason in KEEP_SOURCES:
        keep_in_chunk = {pid for pid in keep if pid in chunk_set}
        missing = keep - keep_in_chunk
        if missing:
            raise SystemExit(f"{prefix} 保留清单有误，条目不在分块内：{sorted(missing)}")
        seen = 0
        for pid in chunk_ids:
            src = (items[pid].get("evidence", {}).get("answer", {}) or {}).get("src", "")
            if not src.startswith(prefix):
                continue
            seen += 1
            if pid in keep or pid in drops:
                continue
            drops[pid] = reason
        print(f"{prefix} 本块 {seen} 条，保留 {len(keep)} 条")

    missing = b6592b35_DROP - chunk_set
    if missing:
        raise SystemExit(f"b6592b35 剔除清单有误，条目不在分块内：{sorted(missing)}")
    seen = 0
    for pid in chunk_ids:
        src = (items[pid].get("evidence", {}).get("answer", {}) or {}).get("src", "")
        if not src.startswith("b6592b35"):
            continue
        seen += 1
        if pid in b6592b35_DROP:
            drops[pid] = b6592b35_REASON
    print(f"b6592b35 本块 {seen} 条，保留 {seen - len(b6592b35_DROP)} 条")

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
