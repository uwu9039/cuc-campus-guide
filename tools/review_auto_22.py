"""auto_22 人工复核：微专业简章、助学金、大学英语、培养方案与财务表格。

判定原则（与 auto_17/18/19/20/21 一致）：
- 保留学生可执行的规则、期限、费用、材料、电话与后果
- 删除校内部门职责、委员会组成、经费与考核、制定目的、施行与解释条款
- 删除面向教职工、后勤职工、项目负责人的程序性文字
- 删除残句、表格粘连、模板占位与无信息宣传语

整源判断：
- att-7205：教育教学改革项目管理办法，面向教师申报
- att-721a / att-75ed / att-7dea / att-7e0d：音乐疗愈、微短剧、短视频、
  书画四个微专业简章，库内已有 wzy26-* 完整结构化条目覆盖招生对象、人数、
  学制、授课方式、证书、报名、联系、费用与全部课程
- att-7533 / att-9549：2027 推免申请材料汇总表与申请表填写说明，表格占位文字
- att-766c：名为家属区管理办法，实为后勤管理处中层干部选拔任用条例，面向职工
- att-7880：2023 年收费公示表格残片，整行粘连无法可靠拆分；库内 2025 年收费
  公示来源实际抓取到的是财务报销手册，无法用于核对现行收费标准
- att-829b：基本建设项目竣工财务决算管理办法，面向财务处与建设部门
- att-843a / att-8f8f：家属区报刊登记表与招聘面试材料说明，非学生事务
- att-8669：创业休学审批表，休学计入最长学习年限与家长知情同意书已被学籍规定覆盖
- att-87c4：名为 2025 年收费公示，实为财务网上报销操作手册，面向教职工
- att-88d0：京外诊断证明知情同意书，办理流程与表格已由现有条目覆盖，只保留伪造处分
- att-8a99：教学成果奖评审办法，面向教师
- att-8c61：教育教学改革专项资金管理办法，面向归口部门与项目负责人
- att-9373：科研、教学、创作项目及成果认定评价办法，面向教师
- att-9633：本科专业设置管理办法的通知头，无规则
- att-990a：因公出访审批表，面向教职工
- att-9b2c / att-9bd8：采购比价表与收费票据预借审批单，面向经办单位
- att-9e25：财务综合服务平台常见问题，全部为教职工报销与劳务发放
- att-a4c3：四六级成绩证明空白模板，无办理规则
- att-a93a：会计档案保管期限附表，面向财务档案管理

保留来源：
- att-7c65：补办毕业证明书照片须蓝底，其余照片、委托书、交回原件规则已有条目
- att-88d0：伪造医院诊断证明的纪律处分
- att-9166：2025-2026 学年助学金等级金额、评定范围、双培生归属、发放方式
- att-95ff：2022 版培养方案的学分结构与学时折算，删除修订原则与课程改革论述
- att-9df1：自修申请入口、可添加课程、查不到课程与说明材料截图，其余与现有条目重复
- att-acb5：大学英语分级、必修与选修学分、不及格另选、降级与课程置换
"""
from __future__ import annotations

import json
import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
ITEMS = ROOT / "items.json"
CHUNK = ROOT / "_review_items" / "chunks" / "auto_22.txt"
BACKUP = ROOT / "_review_items" / "items_before_auto_22.json"
LOG = ROOT / "_review_items" / "applied_auto_22.txt"

DROP_SOURCES = {
    "att-7205": "教育教学改革项目管理办法，面向教师申报",
    "att-721a": "人工智能与音乐疗愈微专业简章，已有 wzy26-* 完整结构化条目覆盖",
    "att-7533": "2027 年推免申请材料汇总表填写说明，模板占位文字",
    "att-75ed": "微短剧表演创作微专业简章，已有 wzy26-* 完整结构化条目覆盖",
    "att-766c": "名为家属区管理办法，实为后勤中层干部选拔任用条例，面向职工",
    "att-7880": "2023 年收费公示表格残片，整行粘连无法拆分，且无现行版本可核对",
    "att-7dea": "短视频与数字文化传播微专业简章，已有 wzy26-* 完整结构化条目覆盖",
    "att-7e0d": "书画理论与实践微专业简章，已有 wzy26-* 完整结构化条目覆盖",
    "att-829b": "基本建设项目竣工财务决算管理办法，面向财务处与建设部门",
    "att-843a": "家属区报刊登记表填写说明，非学生事务",
    "att-8669": "创业休学审批表，休学年限与家长同意书已被学籍管理规定覆盖",
    "att-87c4": "名为 2025 年收费公示，实为财务网上报销操作手册，面向教职工",
    "att-8a99": "教学成果奖评审及奖励办法，面向教师",
    "att-8c61": "教育教学改革专项资金管理办法，面向归口部门与项目负责人",
    "att-8f8f": "家属区招聘面试材料说明，非学生事务",
    "att-9373": "科研、教学、创作项目及成果认定评价办法，面向教师",
    "att-9549": "2027 年推免申请表填写说明，模板占位文字",
    "att-9633": "本科专业设置管理办法的通知头，无规则",
    "att-990a": "因公出访人员审批表，面向教职工",
    "att-9b2c": "采购比价情况汇总表，面向采购经办单位",
    "att-9bd8": "收费票据预借审批单，面向校内票据领用单位",
    "att-9e25": "财务综合服务平台常见问题，全部为教职工报销与劳务发放",
    "att-a4c3": "全国大学英语四、六级成绩证明空白模板，无办理规则",
    "att-a93a": "会计档案保管期限附表，面向财务档案管理",
}

# 补办毕业证明书：只保留照片蓝底要求
att_7c65_KEEP = {"pt-8caca90137"}
att_7c65_REASON = "照片命名、委托书与交回原件规则已有条目覆盖，模板套语无信息"

# 体育免修京外诊断证明：只保留伪造处分
att_88d0_KEEP = {"pt-1ad0aa6619"}
att_88d0_REASON = "知情同意书模板套语，办理流程与表格已由现有条目覆盖"

# 2025-2026 助学金：等级金额、范围、发放与双培生归属
att_9166_KEEP = {
    "pt-0b6ca331ee", "pt-1bd333d641", "pt-26d4195fd8", "pt-3d6109b74f",
    "pt-46d5db7804", "pt-4d06884d38", "pt-5525a8cfba", "pt-61112d24d8",
    "pt-664cd76cfa", "pt-96f72c09b3", "pt-b37554bd2d",
    "pt-c818b0cb5c", "pt-ebc49375c8",
}
att_9166_REASON = "学院工作方案、宣传要求、评审小组与系统操作等行政流程，非学生办事规则"

# 2022 版培养方案：只保留通顺的学分与学时规则，表格行粘连的一律不留
att_95ff_KEEP = {
    "pt-26b57a8bb4", "pt-45c314967d", "pt-b80c3ff84d", "pt-b9cfcc6e3f",
    "pt-d49d1fb66c", "pt-e8dd5a8d38",
}
att_95ff_REASON = "修订原则与课程改革论述，以及体育、思政、大学英语等表格行抽取粘连"

# 自修申请操作手册：入口、可添加课程、查不到课程、说明材料
att_9df1_KEEP = {"pt-88daabc94d", "pt-9713b1d562", "pt-113a417547", "pt-21faca256a"}
att_9df1_REASON = "申请资格、审核流程与操作步骤已由本科生院服务常见问题覆盖"

# 大学英语选课办法：分级、学分、不及格、降级与置换
att_acb5_KEEP = {
    "pt-00011bdc86", "pt-30ea4439b8", "pt-52e1f57024",
    "pt-55aa439d71", "pt-799bc93755", "pt-7cd8db3754", "pt-93b728dff5",
    "pt-aabd08e451", "pt-bba59240df",
}
att_acb5_REASON = "课程设置附表粘连、解释权条款与重复的修读顺序说明"

KEEP_SOURCES = [
    ("att-7c65", att_7c65_KEEP, att_7c65_REASON),
    ("att-88d0", att_88d0_KEEP, att_88d0_REASON),
    ("att-9166", att_9166_KEEP, att_9166_REASON),
    ("att-95ff", att_95ff_KEEP, att_95ff_REASON),
    ("att-9df1", att_9df1_KEEP, att_9df1_REASON),
    ("att-acb5", att_acb5_KEEP, att_acb5_REASON),
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
