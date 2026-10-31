"""auto_14 人工复核：剔除非学历教育办学审批问答、2025 年硕士招生简章、
2015 年旧学籍规定碎片、学校章程与教师手册治理条文，以及设备验收等
内部采购流程；保留实习、优秀本科生奖学金、设备共享、研究生学籍与
学位授予、实验室开放预约与 2027 年推免的原文条款。

判定原则：
- 过期年度：2025 年招生简章整源剔除；2027 年推免为当前周期，保留
- 内部管理：办学单位立项审批、设备验收、学院职责分工不面向学生
- 重复条目：校园卡与奖学金全文已由 rule-* 收录，只删前言套话与碎片
- 政策条文：逐条看过，保留可检索的原文条款
"""
from __future__ import annotations

import json
import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
ITEMS = ROOT / "items.json"
CHUNK = ROOT / "_review_items" / "chunks" / "auto_14.txt"
BACKUP = ROOT / "_review_items" / "items_before_auto_14.json"
LOG = ROOT / "_review_items" / "applied_auto_14.txt"

DROP_SOURCES = {
    "56bb3879": "非学历教育项目办学指导问答，面向办学单位立项审批，且抓取词序严重破碎",
    "583a8801": "2025 年硕士研究生招生简章，招生计划、专业与日程已过期",
    "533d23ad": "学校章程与教代会、学位委员会等内部治理条文（含教师手册乱码）",
    "5b13d3aa": "制度汇编中校园卡办法前言与处分条款碎片，无办理信息；校园卡已由 rule-6677d716 收录",
    "5d67dc12": "2019 年研究生学籍管理规定及其学位细则已被 2024 年修订版（7691069e）与现行学位授予办法（rule-hb6886c409c6）取代",
}

DROPS = {
    # 55b38320 实验室与设备：验收属内部采购
    "pt-4f57e44b99": "30 万以下设备验收的内部流程，不面向学生",
    "pt-69cde68248": "设备与项目验收申请／备案，属内部采购流程",
    "pt-80f0f3e183": "建设项目验收办理时间，属内部采购流程",
    "pt-83a17809ea": "学院自行验收并报备案，属内部采购流程",
    "pt-aa1307c783": "30 万以上项目验收组织方式，属内部采购流程",
    "pt-b59a9f8e8d": "30 万以上在线申请与校级验收，属内部采购流程",
    "pt-f191df6255": "验收材料准备，属内部采购流程",
    "pt-2e66d030df": "服务条款编号残句「(7)实验室开放预约办理流程…」，无完整信息",
    "pt-5d212dd674": "残句「仪器设备借用按具体设备共享中心要求」，无完整信息",
    # 534a4add 本科实习：删编号碎片、套话与校内管理职责
    "pt-0d9bd10a5a": "编号残句「（6）实习纪律或注意事项；」",
    "pt-3e33be4684": "编号残句「（3）实习队伍（指导老师和学生）；」",
    "pt-621fd9681a": "编号残句「（2）实习目的与要求；」",
    "pt-7d35e9c7c5": "编号残句「（2）实习单位、地点、时间与日程安排；」",
    "pt-b6e64055b0": "编号残句「（4）实习经费预算；」",
    "pt-d56a03f64b": "编号残句「（7）实习考核方式；」",
    "pt-d950f66328": "编号残句「（5）实习成绩考核办法；」",
    "pt-fd7fd4bd7c": "编号残句「（5）实习的组织领导；」",
    "pt-494fefd449": "印发套话「经主管校领导同意，现予以印发」",
    "pt-a425e47007": "解释部门套话，无办事信息",
    "pt-aa00b95c5e": "制定本规定的目的套话，无办事信息",
    "pt-cc11c2a558": "实习意义表述，无办事信息",
    "pt-809ffc0626": "11 项规章制度印发通知，与实习办理无关",
    "pt-1fc05d5644": "校、学部、学院三级实习管理制度，属校内管理分工",
    "pt-3c82ea6db1": "学部级实习管理职责，属校内管理分工",
    "pt-5ac839d2b8": "校级实习管理职责，属校内管理分工",
    "pt-96b7ced111": "学院级实习管理职责，属校内管理分工",
    "pt-9850a8823b": "学院实习组织职责细分，属校内管理分工",
    "pt-0fb8e31593": "集中／分散实习计划的制订与审批流程，属校内管理分工",
    "pt-0fd49b28a7": "实习大纲报教务处备案，属校内管理流程",
    "pt-48d8be888c": "带队教师填写实习总结，属教师工作",
    "pt-5a43027646": "学院实习总结报教务处备案，属校内管理流程",
    "pt-a1b67287f4": "学院或指导教师定期检查，属校内管理流程",
    "pt-a454da0e84": "实习计划一式二份的存档要求，属校内管理流程",
    "pt-b88db2f0bd": "实习总结报告表交学院和教务处存档，属校内管理流程",
    # 53e04a6d 优秀本科生奖学金：删套话
    "pt-0b7556985f": "制定本办法的套话，无评选信息",
    "pt-7f92b825a0": "执行起始年级与解释部门，无办事信息",
    "pt-0b1ce7903d": "设立奖学金的目的表述，无评选信息",
    # 5a54d96750 2027 推免：删导航粘连与套话
    "pt-9da601a2db": "招生网导航栏与办法前言粘连，正文不可读",
    "pt-3c5fc4cc99": "与教育部政策冲突时的执行说明，属套话",
    "pt-c4a38c4956": "最终解释权表述，无办事信息",
    "pt-3dd784048d": "招生总体原则表述，无办事信息",
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
            raise SystemExit(f"目标条目不在 auto_14 分块内：{pid}")
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
