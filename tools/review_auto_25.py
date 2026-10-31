"""auto_25 人工复核：图书馆手册、四六级报名、博士与硕士招生、公寓与教室规则。

判定原则（与 auto_17/18/19/20/21/22/23/24 一致）：
- 保留学生可执行的规则、期限、费用、材料、电话与后果
- 删除校内部门职责、委员会组成、经费与考核、制定目的、施行与解释条款
- 删除面向教职工、后勤职工、项目负责人的程序性文字
- 删除已由现行服务条目完整覆盖的重复段落
- 删除残句、表格粘连、模板占位与无信息宣传语

整源判断：
- 00f4cdcc：图书馆综合办公室与借阅服务部职责，联系方式已由 lib-lianxi 覆盖
- b9812c3c：资金支付管理办法，面向财务经办与审批人（与 auto_24 同源，整源删除）
- bae9d5cb：固定资产管理办法，面向资产管理员与使用单位
- bc0bd3bb：辅修报名操作手册界面说明，报名流程已由 fuxiu-baoming 覆盖
- bc5d07ce：实验室建设与岗位管理，面向管理岗，无学生办理事项
- bd166aa2：2004 年公费医疗管理办法的急诊条款残片，无完整规则
- c3021e66：教职工因公出国（境）审批问答，面向教师与管理岗
- c497abf6：场馆位置问答，已由 campus-changguan-weizhi、campus-jiancheng 覆盖
- c5181fe8：图书馆手册的借阅、空间、座位、布局、守则均已由 lib-* 条目覆盖，
  只保留古籍阅览、索书号与在馆取阅上限 7 条

保留来源：
- ba025472：青马学院报名成绩排名、统一笔试与结业考核（学院推荐名额不保留）
- bbdc691e：四六级注册、资格复核、照片标准、缴费与候补、口试与成绩查询；
  2025 年具体日期、通知抬头与重复的缺考/成绩单表述不再保留（cet-* 已覆盖）
- bcd6aa3d：公寓内违规经商与传教、高声喧哗滋事、扰乱秩序处分 3 条；
  封闭管理、消防禁令、退宿与住宿费已由 sushe-* 覆盖
- bd7b1d20：教室借用提前 3 个工作日、拍摄申请书、送材料与截止时间、主楼范围；
  自习室开放时间与无需预约已由 lib-zixishi 覆盖
- c0c0f928：2025 年博士招生方式、报考条件、材料、学费、绿色通道与住宿；
  过期日期、通知抬头、目录指向与残句不保留
- c26b3a60：2025 年硕士复试材料清单、现场复试、入校核验、违规处理与入学复查；
  具体复试日期不保留
"""
from __future__ import annotations

import json
import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
ITEMS = ROOT / "items.json"
CHUNK = ROOT / "_review_items" / "chunks" / "auto_25.txt"
BACKUP = ROOT / "_review_items" / "items_before_auto_25.json"
LOG = ROOT / "_review_items" / "applied_auto_25.txt"

DROP_SOURCES = {
    "00f4cdcc": "图书馆部门职责，联系方式已由 lib-lianxi 覆盖",
    "b9812c3c": "资金支付管理办法，面向财务经办与审批人",
    "bae9d5cb": "固定资产管理办法，面向资产管理员与使用单位",
    "bc0bd3bb": "辅修报名操作手册界面说明，流程已由 fuxiu-baoming 覆盖",
    "bc5d07ce": "实验室建设与岗位管理，面向管理岗，无学生办理事项",
    "bd166aa2": "2004 年公费医疗急诊条款残片，无完整规则",
    "c3021e66": "教职工因公出国（境）审批问答，面向教师与管理岗",
    "c497abf6": "场馆位置问答，已由 campus-changguan-weizhi、campus-jiancheng 覆盖",
    "c5181fe8": "图书馆手册的借阅、空间、座位、布局与守则已由 lib-* 条目覆盖",
}

# 青马学院：成绩排名、统一笔试与结业考核
ba025472_KEEP = {"pt-25a3694427", "pt-35636312b0", "pt-c13eb771c0"}
ba025472_REASON = "学院推荐名额、通知抬头与贯彻精神段落"

# 四六级：注册、资格、照片、缴费、候补、口试与成绩查询
bbdc691e_KEEP = {
    "pt-060f4ea279", "pt-120e417497", "pt-15edd6f597", "pt-1ba1486119",
    "pt-30cb38c57d", "pt-3459cfc9b6", "pt-3be95134b0", "pt-49e266f509",
    "pt-4a184dd151", "pt-5b46d9bd21", "pt-6ad5096879", "pt-6d7ae39065", "pt-6e687dc9f8",
    "pt-71aa775a02", "pt-8ae715ab53", "pt-8be2e8b274", "pt-92d5ef54cc",
    "pt-966e40aeb2", "pt-b11f49682e", "pt-bbd497ff1f", "pt-bfbdb5f360",
    "pt-caeaaf2ce6", "pt-cfafecf3c2", "pt-ebc3f1d211",
}
bbdc691e_REASON = "2025 年具体日期、通知抬头、重复的缺考与成绩单表述、碎片句"

# 学生公寓：只保留未覆盖的三条行为禁令
bcd6aa3d_KEEP = {"pt-ed64e01a42", "pt-ad84095d8f", "pt-2c38385832"}
bcd6aa3d_REASON = "封闭管理、消防禁令、退宿与住宿费已由 sushe-* 条目覆盖"

# 教室：只保留借用流程与管辖范围
bd7b1d20_KEEP = {
    "pt-40540dd1a6", "pt-48e9afb94a", "pt-a518e428d2", "pt-dfb6090bb1",
    "pt-3532b12f9d", "pt-aa05ffe483", "pt-fd656b0046",
}
bd7b1d20_REASON = "自习室开放时间与无需预约已由 lib-zixishi 覆盖，问答标题与活动清单碎片"

# 博士招生：方式、条件、材料、学费、绿色通道与住宿
c0c0f928_KEEP = {
    "pt-0ab304e32a", "pt-0ca2610034", "pt-0d0308e28c", "pt-17c62abe16",
    "pt-1921a0469d", "pt-23f292620a", "pt-2835b25a38", "pt-31649573bd",
    "pt-4237e1595c", "pt-4b3c511346", "pt-4c902db246", "pt-54de1d9285",
    "pt-55f3929e0a", "pt-5a7279dacd", "pt-6835796f17", "pt-6fb749b9e5",
    "pt-718b10e043", "pt-7acedaf684", "pt-7cfffa0c18", "pt-7f0e1c715e",
    "pt-8d51c016ee", "pt-972d5d60b9", "pt-974b9f4602", "pt-aa6b1f41a6",
    "pt-b3268713ac", "pt-b3e2e8ee19", "pt-b57d824f98", "pt-c0d2f93d33",
    "pt-e4116c6522", "pt-ef9a412d0d", "pt-f048dbfffd", "pt-f8db43ec52",
    "pt-f9df25a84e",
}
c0c0f928_REASON = "过期日期、通知抬头、目录指向、条款标题与抽取残句"

# 硕士复试：材料清单、现场复试、入校核验、违规处理与入学复查
c26b3a60_KEEP = {
    "pt-0b978168eb", "pt-45596d3e38", "pt-530b5c4976", "pt-54e29de73d",
    "pt-6c348ff089", "pt-72ccbe903a", "pt-79ea625635", "pt-8787db571c",
    "pt-a1ee189a2a", "pt-b39b30eaca", "pt-b8daccedd5", "pt-dc34022c7b",
    "pt-ee7522a5af",
}
c26b3a60_REASON = "2025 年复试日期、章节标题与诚信复试套语"

# 图书馆手册：古籍阅览、索书号与在馆取阅上限
c5181fe8_KEEP = {
    "pt-07bfb82d15", "pt-18c58933b3", "pt-59bc598e2d", "pt-3a54565ad4",
    "pt-2b3d835967", "pt-47cee66d63", "pt-21161fb76b",
}
c5181fe8_REASON = "借阅、空间预约、座位、楼层布局、行为守则与数据库介绍"

KEEP_SOURCES = [
    ("ba025472", ba025472_KEEP, ba025472_REASON),
    ("bbdc691e", bbdc691e_KEEP, bbdc691e_REASON),
    ("bcd6aa3d", bcd6aa3d_KEEP, bcd6aa3d_REASON),
    ("bd7b1d20", bd7b1d20_KEEP, bd7b1d20_REASON),
    ("c0c0f928", c0c0f928_KEEP, c0c0f928_REASON),
    ("c26b3a60", c26b3a60_KEEP, c26b3a60_REASON),
    ("c5181fe8", c5181fe8_KEEP, c5181fe8_REASON),
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
        missing = keep - chunk_set
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
