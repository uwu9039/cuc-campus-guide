"""auto_23 人工复核：财务管理办法、行政表格、修学指南汇编与辅修简章。

判定原则（与 auto_17/18/19/20/21/22 一致）：
- 保留学生可执行的规则、期限、费用、材料、电话与后果
- 删除校内部门职责、委员会组成、经费与考核、制定目的、施行与解释条款
- 删除面向教职工、单位经办人与项目负责人的程序性文字
- 删除残句、表格粘连、模板占位与无信息宣传语

整源判断：
- att-acb5：大学英语选课办法，本块 3 条已被本文件在 auto_22 保留的 9 条与现有
  大学英语条目覆盖，其中 C 级二外语一条为表格粘连残句
- att-acd4：创新创业学分认定办法，企业 6/12 学分与网店三钻 3 学分已由现有来源
  e2df7556 完整覆盖，其余为通知头、制定目的与教务处内部登录时间
- att-aef3：往届生授予学士学位证明模板，证明入档案、联系电话与该生未曾入档均为
  模板套语；模板下载、办理地点与 65783223 已有条目覆盖
- att-b8d6：家庭经济困难认定表填写说明，仅承诺栏与选填项提示
- att-b97d：校内悬挂横幅标语、设置宣传广告管理办法，面向各单位与所属学生组织，
  规定审批、地点、规格与拆除，非学生常见办事
- att-bb36：精品教材建设项目实施办法，面向教师申报与教材编写
- att-bde2：全面实施预算绩效管理方案，面向校内预算与归口管理部门
- att-c034：2027 年推免诚信考试承诺书，全部为承诺与后果套语
- att-c095：因公临时出国任务和预算审批意见表，表格字段
- att-c7d4：培训费管理办法，面向各部门与培训项目负责人
- att-c86e：修学指南为传媒博物馆、学生社团、图书馆、征兵、评优、集体户口等多份
  旧文件汇编；图书馆借阅与赔偿、征兵加分与免修、评优名额、博物馆开放预约、集体
  户口等主体规则均已有更新来源覆盖；社团会费不得高于 30 元与现行「学生社团不
  收取会费」规定冲突，其余为社团财务、刊物、考核等内部管理细则
- att-c9f9：建设世界一流大学（学科）引导专项资金管理办法，面向归口部门与项目负责人
- att-ca55：会议费管理办法，面向各部门办会与报销
- att-cc35：本科生选课管理办法（试行），选课资格、补退选、12 学分、重修等规则已由
  现行本科生选课管理办法来源 xuanke-2 完整覆盖，末尾为 2018 级课程结构粘连表
- att-d326：传媒博物馆展览申办表字段，无办事规则
- att-d4ff：AIGC 与商业摄影微专业简章，已有 wzy26-* 完整结构化条目覆盖招生目标、
  课程、费用 4440 元与学分认定
- att-da51：应收及预付款借款人变更表，面向项目负责人
- att-dd71：学籍变动审批表（退学）勾选项，退学情形已由学籍管理规定条目覆盖
- att-e2ec：仅保留 2017 级及以前执行旧版大学英语规定的过渡条款，已失效

保留来源：
- att-cecf：2026 年传播学（信息传播方向）辅修招生简章，保留计划录取 20 人、
  学费 130 元/学分与合班授课方式，专业介绍与培养目标不留
"""
from __future__ import annotations

import json
import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
ITEMS = ROOT / "items.json"
CHUNK = ROOT / "_review_items" / "chunks" / "auto_23.txt"
BACKUP = ROOT / "_review_items" / "items_before_auto_23.json"
LOG = ROOT / "_review_items" / "applied_auto_23.txt"

DROP_SOURCES = {
    "att-acb5": "大学英语选课规则已由本文件保留条目与现有大学英语条目覆盖，余为表格残句",
    "att-acd4": "创新创业学分规则已由现有条目完整覆盖，余为通知头与教务处内部登录时间",
    "att-aef3": "往届生学位证明模板套语，办理方式与电话已有条目覆盖",
    "att-b8d6": "家庭经济困难认定表填写说明，无办事规则",
    "att-b97d": "校内横幅与宣传广告审批管理办法，面向各单位和学生组织，非学生常见办事",
    "att-bb36": "精品教材建设项目实施办法，面向教师",
    "att-bde2": "全面实施预算绩效管理方案，面向校内预算与归口管理部门",
    "att-c034": "推免诚信考试承诺书模板套语",
    "att-c095": "因公临时出国任务和预算审批表字段，面向教职工",
    "att-c7d4": "培训费管理办法，面向各部门与培训项目负责人",
    "att-c86e": "修学指南为多份旧文件汇编，主体规则已有更新来源覆盖，社团会费条款与现行规定冲突",
    "att-c9f9": "双一流建设引导专项资金管理办法，面向归口部门与项目负责人",
    "att-ca55": "会议费管理办法，面向各部门办会与报销",
    "att-cc35": "选课规则已由现行本科生选课管理办法覆盖，末尾为 2018 级课程结构粘连表",
    "att-d326": "传媒博物馆展览申办表字段，无办事规则",
    "att-d4ff": "AIGC 与商业摄影微专业简章，已有 wzy26-* 完整结构化条目覆盖",
    "att-da51": "应收及预付款借款人变更表，面向项目负责人",
    "att-dd71": "退学审批表勾选项，退学情形已由学籍管理规定覆盖",
    "att-e2ec": "仅保留 2017 级及以前执行旧规定的过渡条款，已失效",
}

# 2026 传播学（信息传播方向）辅修：计划人数、学费、授课方式
att_cecf_KEEP = {"pt-79c873cb22", "pt-963f24ec08", "pt-3c5fd03889"}
att_cecf_REASON = "专业介绍与培养目标，非招生办事信息"

KEEP_SOURCES = [
    ("att-cecf", att_cecf_KEEP, att_cecf_REASON),
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
