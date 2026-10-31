"""auto_21 人工复核：辅修与微专业简章、选课通知、学籍审批表、缴费通知。

判定原则（与 auto_17/18/19/20 一致）：
- 保留学生可执行的规则、期限、费用、地点、材料、电话与后果
- 删除校内部门职责、委员会组成、考核与经费、制定目的、施行与解释条款
- 删除面向教职工、馆员、党支部/团组织内部的程序性文字
- 删除残句、标题粘连、空通知与无信息宣传语

整源判断：
- att-0b45：高等学校财务制度，auto_20 已整源剔除，本块为同一来源余下 25 条
- att-0d04：教材选用管理办法，面向学院教材委员会与教师
- att-1a82：名为学生缴费通知，实为财务处暑期值班与报销安排，面向教职工
- att-1dbf：2012 年乒乓球赛新闻，已过期
- att-250c / att-2acb / att-427b / att-63ea / att-6555 / att-6574：
  2026 秋季微专业简章，库内已有 wzy26-* 完整结构化条目覆盖招生对象、人数、
  学制、授课方式、证书、报名、联系方式、费用与课程表，本块为同一 PDF 的局部抽取
- att-2565：成绩单办理流程，库内可信电子成绩单说明已覆盖，试运行免费提示已过期
- att-36fb：2025 年行政管理辅修简章，已被 2026 年简章与辅修管理办法取代
- att-38c9：因公临时出国经费管理办法，面向教职工报销
- att-3d9a：收费票据申领单承诺书，面向校内票据领用单位
- att-4bce：基本科研业务费管理办法，面向在编教职工
- att-589c：资助资金管理办法附件中的一条废止条款，无办事信息
- att-5d5c：学生出国（境）审批表签字页，无规则
- att-6041：基层教学组织建设意见，面向教学单位与教师
- att-7186：实为 2021-2022 学年缴费通知，已被库内 2027 学年缴费通知取代
- att-7205：教育教学改革项目管理办法，面向教师项目申报

保留来源：
- att-0d17 / att-19ac / att-4b0a / att-6c49：学籍变动审批表中的保留学籍、休学、
  学业留级、复学条件与后果
- att-2b40：请假审批权限、事假上限、缺课三分之一无考试资格与留级
- att-48f4：辅修报名系统入口与操作步骤
- att-621b：2026 年行政管理辅修招生对象、志愿数、人数、授课、学费与证书限制
- att-5baa：推免个人陈述中的自我评价、报考原因、职业规划与特长材料
- att-1aee：2026-2027 秋季选课的平台入口、志愿规则、补退选、成绩构成、
  考试要求、面授要求、客服与名单有效性；其余为教师简介与课程介绍
"""
from __future__ import annotations

import json
import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
ITEMS = ROOT / "items.json"
CHUNK = ROOT / "_review_items" / "chunks" / "auto_21.txt"
BACKUP = ROOT / "_review_items" / "items_before_auto_21.json"
LOG = ROOT / "_review_items" / "applied_auto_21.txt"

DROP_SOURCES = {
    "att-0b45": "高等学校财务制度，面向高校财务机构，auto_20 已整源剔除，本块为余下条目",
    "att-0d04": "教材选用管理办法，面向学院教材委员会与教师，无学生办事规则",
    "att-1a82": "名为学生缴费通知，实为财务处暑期值班与报销安排，面向教职工",
    "att-1dbf": "2012 年乒乓球赛新闻，已过期且无办事信息",
    "att-250c": "数字媒体经济微专业简章，已有 wzy26-* 完整结构化条目覆盖",
    "att-2565": "成绩单办理流程，已有可信电子成绩单说明覆盖，试运行免费提示已过期",
    "att-2acb": "数智电竞微专业简章，已有 wzy26-* 完整结构化条目覆盖",
    "att-36fb": "2025 年行政管理辅修简章，已被 2026 年简章与辅修管理办法取代",
    "att-38c9": "因公临时出国经费管理办法，面向教职工报销，学生仅随教师出访时参照",
    "att-3d9a": "收费票据申领单承诺书，面向校内票据领用单位",
    "att-427b": "数智品牌传播微专业简章，已有 wzy26-* 完整结构化条目覆盖",
    "att-4bce": "基本科研业务费管理办法，面向在编教职工科研项目",
    "att-589c": "学生资助资金管理办法附件中的一条废止条款，无办事信息",
    "att-5d5c": "学生出国（境）审批表签字页，无规则",
    "att-6041": "基层教学组织建设意见，面向教学单位与教师",
    "att-63ea": "传媒产业投融资微专业简章，已有 wzy26-* 完整结构化条目覆盖",
    "att-6555": "AI 与设计思维创新微专业简章，已有 wzy26-* 完整结构化条目覆盖",
    "att-6574": "AI 实训营微专业简章，已有 wzy26-* 完整结构化条目覆盖",
    "att-7186": "实为 2021-2022 学年缴费通知，已被库内 2027 学年缴费通知取代",
    "att-7205": "教育教学改革项目管理办法，面向教师项目申报",
}

# 保留学籍审批表：两条完整规则，一条勾选项残句
att_0d17_KEEP = {"pt-11a6011f2a", "pt-4a49011223", "pt-a78a59f276"}
att_0d17_REASON = "保留学籍审批表中的勾选项，无完整规则"

# 2025 市场营销辅修：学费与计划录取人数，其余为专业介绍
att_13c1_KEEP = {"pt-6a2ead2ef0", "pt-df5c458134"}
att_13c1_REASON = "专业介绍、培养目标与能力描述，非招生办事信息"

# 家长知情同意书：保留一方签字视同另一方同意的规则
att_1719_KEEP = {"pt-2cc9ffd38a"}
att_1719_REASON = "家长知情同意书模板套语，无办事规则"

# 调课管理办法：只保留向学生公布调课信息的渠道
att_1958_KEEP = {"pt-2fc4b52bfd"}
att_1958_REASON = "任课教师调课审批流程与教学事故条款，面向教师"

# 选课通知：保留学生选课、学习、考试、成绩与支持信息
att_1aee_KEEP = {
    "pt-0a18ef6a26", "pt-0b1ed2cb70", "pt-1aca2e922f", "pt-1b6dc02a2e",
    "pt-25e1abb5d7", "pt-28f42d4675", "pt-33a3311f6b", "pt-38d0c7465c",
    "pt-4723cd290f", "pt-482b5a52ff", "pt-4efc00da54", "pt-55fa18ab95",
    "pt-59d6e88b15", "pt-5fa17c71b3", "pt-796b6111c8", "pt-7a468ac4cd",
    "pt-87ffdb6128", "pt-8be2e28884", "pt-99f5fb3042", "pt-9a010c14e5",
    "pt-9b4a32ceff", "pt-ab93055438", "pt-aee028f3cb", "pt-b6c496e67e",
    "pt-bad243d634", "pt-c51a57fb7d", "pt-c8c23e6658", "pt-c97bfa2ba5",
    "pt-c9df83eae5", "pt-d311c3bc65", "pt-d509d78f01", "pt-e36a13592d",
    "pt-ead5e05862", "pt-e961cd38ba", "pt-f4ef189264", "pt-fa77704d91",
}
att_1aee_REASON = "教师简介、课程内容介绍、平台界面说明与残句，非选课办事规则"

# 毕业证/学位证遗失证明：只保留本科生院电话
att_2ca1_KEEP = {"pt-70d8975958"}
att_2ca1_REASON = "遗失证明模板占位文字，无办事规则"

# 推免个人陈述：保留四个实质栏目，删除两个独立问句
att_5baa_KEEP = {"pt-2db1805179", "pt-3ded7b7f6b", "pt-67d9efd357", "pt-8ebce3bf37"}
att_5baa_REASON = "个人陈述中的独立问句，非材料要求"

# 2026 行政管理辅修：保留招生与证书限制，删除专业介绍
att_621b_KEEP = {
    "pt-6932a9c449", "pt-3ac00d925d", "pt-cb8d403020", "pt-5f3313061d",
    "pt-6d329e2726", "pt-ecb8322a13", "pt-fd69f26474",
}
att_621b_REASON = "专业介绍与培养目标，非招生办事信息"

# 学生证遗失证明：只保留仅限本学期期末考试的规则
att_6c52_KEEP = {"pt-3fb7b0b106"}
att_6c52_REASON = "遗失证明模板占位文字，无办事规则"

# 2025 播音辅修：学位条件、学费与计划录取人数
att_6ec1_KEEP = {"pt-14f8dcbef2", "pt-20a68c4df8", "pt-3cb81b396a"}
att_6ec1_REASON = "专业介绍、培养目标与能力描述，非招生办事信息"

KEEP_SOURCES = [
    ("att-0d17", att_0d17_KEEP, att_0d17_REASON),
    ("att-13c1", att_13c1_KEEP, att_13c1_REASON),
    ("att-1719", att_1719_KEEP, att_1719_REASON),
    ("att-1958", att_1958_KEEP, att_1958_REASON),
    ("att-1aee", att_1aee_KEEP, att_1aee_REASON),
    ("att-2ca1", att_2ca1_KEEP, att_2ca1_REASON),
    ("att-5baa", att_5baa_KEEP, att_5baa_REASON),
    ("att-621b", att_621b_KEEP, att_621b_REASON),
    ("att-6c52", att_6c52_KEEP, att_6c52_REASON),
    ("att-6ec1", att_6ec1_KEEP, att_6ec1_REASON),
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
            if pid in keep:
                continue
            if pid in drops:
                continue
            drops[pid] = reason
        print(f"{prefix} 本块 {seen} 条，保留 {len(keep)} 条")

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
