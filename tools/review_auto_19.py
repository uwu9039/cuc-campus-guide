"""auto_19 人工复核：发展党员程序、BALIS 介绍、本科课程考核与成绩管理办法、
新入职政审、学士学位授予、图书馆前台问答、2026 迎新通知、毕业论文管理办法、
学生公费医疗、2023 秋期末通知、高职学籍、入团细则。

判定原则（与 auto_17/18 一致）：
- 保留学生可执行的规则、期限、费用、地点、材料、电话与后果
- 删除校内部门职责、委员会组成、考核与经费、制定目的、施行与解释条款
- 删除面向教职工、馆员、党支部/团组织内部的程序性文字
- 删除残句、标题粘连、空通知与无信息宣传语

整源判断：
- 9fba5c06：发展党员工作内部程序，auto_18 已删 10 条，本块 73 条一并剔除
- a1811e41：新入职教职工政审材料与证明模板，不面向学生
- a68ce0ec：与已入库的同一份学位授予办法 1ce888fb 重复，21 条规范化后完全
  相同，余 1 条「逾期未提交不再受理」也已见 pt-d98093724e，整源剔除
- a7225474：图书馆前台内部问答 2024 年版 OCR，错字缺字严重，且多为馆员
  答复口径，座位预约等已有专门来源
- a9dfad84：2023-2024 学年秋季学期期末工作通知，考试周与截止日期已过期，
  且多为教学单位内部组考任务
- a9efc2d9：高等职业教育（专科）学籍规定，条款与本科规定不同，检索时会给
  本科生返回错误规则
- aa7cb24a：团中央发展团员工作细则，只保留学生申请入团直接相关的事实，
  本块保留年龄条件与两名介绍人 2 条；auto_20 的 47 条同样只留 13 条

a95c853a 与 66d43209 是同一份 2018 年论文管理办法的两次入库，66d43209 已有
49 条但缺查重线、答辩公开、有效期完成等规则，故只删内部职责与两条完全重复。
"""
from __future__ import annotations

import json
import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
ITEMS = ROOT / "items.json"
CHUNK = ROOT / "_review_items" / "chunks" / "auto_19.txt"
BACKUP = ROOT / "_review_items" / "items_before_auto_19.json"
LOG = ROOT / "_review_items" / "applied_auto_19.txt"

DROP_SOURCES = {
    "9fba5c06": "发展党员工作内部程序，面向党支部与党总支，不面向学生办事",
    "a1811e41": "新入职教职工政审材料与证明模板，不面向学生办事",
    "a68ce0ec": "与已入库的同一份学位授予办法（1ce888fb）重复，21 条逐字相同，余 1 条也已覆盖",
    "a7225474": "图书馆前台内部问答 OCR，错字缺字严重且多为馆员答复口径",
    "a9dfad84": "2023-2024 秋期末考试工作通知，时间节点已过期，多为教学单位内部组考任务",
    "a9efc2d9": "高等职业教育（专科）学籍规定，条款与本科规定冲突，面向对象不符",
}

DROPS = {
    # ---- a07d9d27 课程考核与成绩管理办法：套话与脱节残句 ----
    "pt-bbcd9b4401": "制定办法的目的与依据，无办事信息",
    "pt-6bf58269f8": "适用范围与第二章标题粘连，无新增信息",
    "pt-ec9c093d2d": "课程考核目的表述，无办事信息",
    "pt-7ef6609ccc": "GPA 公式中的变量说明，脱离公式无法使用",
    # ---- a95c853a 毕业论文管理办法：校内职责与重复 ----
    "pt-0266ae5e65": "论文由学院保管与保密转存，属校内档案",
    "pt-180672c90e": "学院落实毕业论文组织管理，属校内职责",
    "pt-226b0ef44e": "学院制定评分标准，属校内职责",
    "pt-2cb3ebd93a": "指导教师审阅内容，与 pt-6d86d52915 完全相同",
    "pt-4845343e3a": "论文材料装订存档，与 pt-af9b72e27f 完全相同",
    "pt-57bd84d529": "学院总结报教务处，属校内程序",
    "pt-600dc20329": "成立学院答辩委员会，属校内组织",
    "pt-68404e8603": "答辩小组人数，属校内组织",
    "pt-817fb6d31c": "指导教师工作要求，面向教师",
    "pt-8d9e65e0aa": "学院职责清单，属校内分工",
    "pt-accb1541be": "指导教师任职条件，面向教师",
    "pt-c59c2b158d": "学院制定实施细则，属校内程序",
    "pt-d33174b3a9": "指导教师职责清单，面向教师",
    "pt-da955d13cd": "解释部门，无办事信息",
    # ---- a96f1bcc 学生公费医疗：施行条款 ----
    "pt-bed8daace3": "施行与废止条款，无办事信息",
    # ---- BALIS 馆际互借：内部职能 ----
    "pt-5183877df5": "馆际互借中心内部职能与补贴结算，面向馆员",
    # ---- a7c6e197 迎新通知：单独判断的重复与残句 ----
    "pt-3afd0f1ddf": "保卫部电话与附件标题粘连，电话已见 pt-2d10c789cb",
    "pt-85e2d35bc4": "报到日程表与公寓电话粘连成残句",
    "pt-cd688afb3e": "报到日期为 pt-33a81c62a6 的子集",
    "pt-dbd3059d46": "爱心大礼包与 pt-6219421d85 重复",
    "pt-ebc014f7ee": "到学院报到点报到已含于 pt-56cbf531ca",
}

# a7c6e197 保留项：学生可直接使用的时间、地点、费用、材料、流程与设施信息
A7_KEEP = {
    "pt-0268ab2d58", "pt-04fb5697fb", "pt-0b648e16a8", "pt-0b94078f7c",
    "pt-0f81ac37ee", "pt-12908759ce", "pt-2485fa5f63", "pt-2edf62629a",
    "pt-33a81c62a6",
    "pt-33e86b232b", "pt-3730a53906", "pt-3cf22c6de6", "pt-3d8589464e",
    "pt-3db8697c30", "pt-3deefd8ec1", "pt-456156b43e", "pt-46dd1ed5cb",
    "pt-4a6741e4b4", "pt-5117de53c2", "pt-52029eef2e", "pt-542e262398",
    "pt-5432c810db", "pt-55ab98b5b8", "pt-56cbf531ca", "pt-5db2d8b587",
    "pt-5e9c55b455", "pt-6219421d85", "pt-643b174c22", "pt-645f70514f",
    "pt-659c3673cd", "pt-65cc583aa0", "pt-65d5d0d84a", "pt-68ac127f7a",
    "pt-68ee87fcff", "pt-6a603d21ee", "pt-7028391734", "pt-763ccb6283",
    "pt-789a0d81a1", "pt-79453cd022", "pt-79b84dc5d2", "pt-7e44a53d6f",
    "pt-7e8ee9b35a", "pt-8206d5e9bf", "pt-8e7882cf5b", "pt-923cfa5706",
    "pt-9c47fe708b", "pt-9d7d8da3ec", "pt-9f6bd14eb9", "pt-a14990b09b",
    "pt-a762303f85", "pt-a7f17a1cfd", "pt-a896ba72f8", "pt-ad7a62b767",
    "pt-b574e3d94e", "pt-ced86ec65f", "pt-d18d07614a", "pt-d1ff8aecb9",
    "pt-db5755d272", "pt-db7e2d422f", "pt-e2af563d99", "pt-e384096cf2",
    "pt-e43461fd5e", "pt-e477a22a17", "pt-e4cadf918f", "pt-e67e21de77",
    "pt-e73996dae6", "pt-e7ff9f047b", "pt-efe5a8be6d", "pt-f5f98682b0",
    "pt-f6142425c7",
}

A7_DEFAULT_REASON = "校内迎新工作部署、宣传表述、阶段划分或残句，非学生可直接使用的事项"

# aa7cb24a 只保留学生申请入团时直接相关的事实，团组织内部程序一律删除
AA_KEEP = {"pt-646bf2f75d", "pt-5f9cef16f3"}
AA_DEFAULT_REASON = "团组织发展团员的内部程序与职责，非学生可直接使用的事项"


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
            raise SystemExit(f"目标条目不在 auto_19 分块内：{pid}")
        if pid not in items:
            raise SystemExit(f"条目不存在：{pid}")
        drops[pid] = reason

    a7_seen = 0
    for pid in chunk_ids:
        src = (items[pid].get("evidence", {}).get("answer", {}) or {}).get("src", "")
        if not src.startswith("a7c6e197"):
            continue
        a7_seen += 1
        if pid in A7_KEEP:
            continue
        if pid in drops:
            continue
        drops[pid] = A7_DEFAULT_REASON

    missing_keep = A7_KEEP - chunk_set
    if missing_keep:
        raise SystemExit(f"保留清单有误，条目不在分块内：{sorted(missing_keep)}")
    print(f"a7c6e197 本块 {a7_seen} 条，保留 {len(A7_KEEP)} 条")

    aa_seen = 0
    for pid in chunk_ids:
        src = (items[pid].get("evidence", {}).get("answer", {}) or {}).get("src", "")
        if not src.startswith("aa7cb24a"):
            continue
        aa_seen += 1
        if pid in AA_KEEP:
            continue
        drops[pid] = AA_DEFAULT_REASON

    missing_aa = AA_KEEP - chunk_set
    if missing_aa:
        raise SystemExit(f"入团保留清单有误，条目不在分块内：{sorted(missing_aa)}")
    print(f"aa7cb24a 本块 {aa_seen} 条，保留 {len(AA_KEEP)} 条")

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
