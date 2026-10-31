"""auto_16 人工复核：剔除科研经费报销细则、公务卡办法、校友 APP 指南、
WPS 工作坊宣传等整源；保留学生管理规定、预科生转本科、微专业、学博生培养、
学籍信息变更、本科交流学习与研究生外语验证的原文条款。

判定原则：
- 内部财务：科研经费报销与公务卡面向教师科研支出，不面向学生
- 非学生事务：校友 APP 与工作坊宣传没有学生办事步骤
- 学生管理：保留考试、学籍、退学、处分、转专业等可检索条款，删目的套话
- 微专业/培养：删校内设点评议与部门职责，保留学生修读、缴费、证书规则
"""
from __future__ import annotations

import json
import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
ITEMS = ROOT / "items.json"
CHUNK = ROOT / "_review_items" / "chunks" / "auto_16.txt"
BACKUP = ROOT / "_review_items" / "items_before_auto_16.json"
LOG = ROOT / "_review_items" / "applied_auto_16.txt"

DROP_SOURCES = {
    "7bf1736f": "科研经费报销实施细则，面向教师科研支出，不面向学生",
    "810b65ec": "中传 APP 校友版块注册、校友卡与入校 FAQ，面向已毕业校友",
    "81af7a77": "公务卡管理办法，面向在职教职工报销",
    "7a5b4290": "WPS 信息化服务工作坊宣传与回放链接，属活动通知",
}

DROPS = {
    # 7b7f3ee6 学生管理规定：删制定目的、校内决定程序与套话
    "pt-35d51e020e": "制定本规定的依据套话，无办事信息",
    "pt-07f320fd1e": "学生应当努力学习等思想教育表述，无办事信息",
    "pt-e33e67a2d0": "学校以培养人才为中心的办学表述，无办事信息",
    "pt-9f0b749d10": "施行日期与解释部门，无办事信息",
    "pt-21ffbbe481": "退学处理由校长会议研究决定，属校内程序",
    "pt-5984110dcc": "成人高等学历教育参照本规定，无办事信息",
    "pt-29096e4caf": "处分应程序正当等原则表述，无办事信息",
    "pt-4a41280ad1": "奖励处分材料归档，属校内档案管理",
    "pt-839e140fd6": "违纪处分一般在发现学期内处理结束，属校内时限",
    "pt-aaa9c929f8": "对犯错误学生要热情帮助等表述，无办事信息",
    "pt-9cffac6367": "学校应当维护校园正常秩序，无办事信息",
    "pt-b3a9052f5f": "学生参与民主管理的组织形式，无办事信息",
    "pt-cf52d14be9": "学校提倡支持学生开展文体活动，无办事信息",
    "pt-d08581ba5d": "残句「对未获批准的，学校可依法劝阻或者制止。」",
    "pt-50501a224e": "残句「情节恶劣的，请有关部门查究。」",
    "pt-19d1ca56f8": "转户口抄送公安部门的内部流程残句",
    "pt-3104d1b27b": "重考名单由教务处整理导入，属校内流程",
    "pt-ef898f702a": "旷考记零分，与 pt-27c84c5cd0 重复",
    "pt-bcc7dabe35": "其他违纪处理见处分条例的交叉引用，无具体信息",
    # 78552e60 预科生管理办法：删解释印发、原则表述与部门分工
    "pt-997519f383": "解释部门，无办事信息",
    "pt-eceefab708": "执行起始年级与印发日期，无办事信息",
    "pt-ab8d71f32c": "应当遵守国家法律和校纪校规，无办事信息",
    "pt-6d8e344c34": "课程设置原则表述，无办事信息",
    "pt-742bd604be": "招生处与人文学院负责专业选择，属校内分工",
    # 7f5ece56 微专业：删设点评议、部门职责与套话
    "pt-0db1d9191c": "教务处微专业职责，属校内分工",
    "pt-47a6f513c7": "教育质量评估与督导处职责，属校内分工",
    "pt-1ccedf564f": "教学单位重构课程内容，属校内教学建设",
    "pt-2c809c8354": "微专业调课手续，属校内教学管理",
    "pt-46b8b20fcf": "未尽事项参照本科管理规定的兜底条款",
    "pt-53736f5701": "招生简章由教学单位制定报教务处审定，属校内流程",
    "pt-ad0a8a82a5": "制定本办法的套话，无办事信息",
    "pt-ec015e4c55": "施行日期与解释部门，无办事信息",
    "pt-839ab83af6": "教务处公布微专业名录，属校内流程",
    "pt-9ae9c33bea": "微专业设点的校内评议程序",
    "pt-c6aeacc31f": "明确微专业负责人与团队，属校内建设",
    "pt-dfcace8bbd": "教学单位报名初审、录取、缴费与证书职责，属校内分工",
    "pt-ed151c374c": "培养方案调整须报教务处，属校内流程",
    "pt-f15eaf2ed7": "教务处组织专家复审并报校长办公会，属校内流程",
    "pt-893a883291": "实行微专业教育制度的目的表述，无办事信息",
    "pt-d955cbc241": "微专业开设条件，属校内设点要求",
    "pt-73da890dad": "招生宣传不得夸大，属校内宣传要求",
    # 7b720b3b 学博生培养规定：删依据、执行年级、内部表决与残句
    "pt-86419a3d3d": "制定本规定的依据套话，无办事信息",
    "pt-906e0472c9": "解释部门与印发日期，无办事信息",
    "pt-1d88c24920": "执行起始年级，无办事信息",
    "pt-d42a66a695": "分委员会建议、校委会审议的内部表决流程",
    "pt-4fcc09f892": "残句「否则，本次学位申请终止。」",
    # 7ffa147d 学籍信息变更：删面向高校的工作要求与解释条款
    "pt-282c1b0b4c": "高校留存材料接受检查，属校内工作要求",
    "pt-300a7d9136": "审核不严的责任追究，属校内工作要求",
    "pt-422979c0fd": "高校建立健全规章制度，属校内工作要求",
    "pt-7235cb152b": "高校严格新生资格审查，属校内工作要求",
    "pt-9bb89f3890": "通知适用于北京高校的适用范围说明，无办事信息",
    "pt-53850a3727": "本通知自发布之日起执行，无办事信息",
    "pt-f75adb6331": "本通知由北京市教委解释，无办事信息",
    # 7f5298ed 本科交流学习：删解释印发
    "pt-b7d7f6d8d8": "解释部门与印发日期，无办事信息",
    # 805bb0c0 研究生外语验证：删年度报到表提示
    "pt-46a1625b9c": "填报《2026 年研究生新生报到数据表》的年度提示",
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
            raise SystemExit(f"目标条目不在 auto_16 分块内：{pid}")
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
