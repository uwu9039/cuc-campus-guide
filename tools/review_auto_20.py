"""auto_20 人工复核：入团细则、混合式教学、征兵条例、博士生培养、转专业、
招生章程、智慧财务报销、研究生院服务、校友入校、财务备案表、辅修简章、
高等学校财务制度。

判定原则（与 auto_17/18/19 一致）：
- 保留学生可执行的规则、期限、费用、地点、材料、电话与后果
- 删除校内部门职责、委员会组成、经费与考核、制定目的、施行与解释条款
- 删除面向教职工、馆员、校友、团组织内部的程序性文字
- 删除残句、标题粘连、空通知与无信息宣传语

整源判断：
- ae319fe4：2023 年本科招生章程，面向高考考生与家长，录取与监察规则不适用
  于在校生，学费住宿费为 2022 年标准
- aeb52846：智慧财务网上报销操作手册，面向教职工报账，含大量截图占位与残句
- aeb74d15：研究生院教改项目申报与成绩修改，服务对象为教师
- afb562dc：中传 APP 校友返校注册指南，面向已毕业校友
- att-0794：财务签字备案留底表，面向部门经费负责人
- att-085a：保留入学资格申请表勾选项残片，无完整规则
- att-0b45：高等学校财务制度（2013 年施行），面向高校财务机构，无学生办事信息
- ace5831c：2021 年本科生转专业管理办法，已被 2025 年办法取代（公示 5 天、
  每学年秋季一次、可填两个志愿等规则均已变化）。2024 版 ef97da2a 在 auto_29
  复核时整源剔除；2025 版 zhuanzhuanye-2025 在 auto_34 必须保留

aaf7b0fc 是国家征兵工作条例（2023-05-01 施行），只保留 25 条学生侧事实：
应征条件、应征地、保留学籍、兵役登记、体检互认、公示、优待金与拒绝逃避后果。
aa7cb24a 只保留 13 条入团申请侧事实，团组织内部程序删除。
ac35a75d 与 6cbe728b 是同一份博士培养规定的两次入库，7 条同文条目删除。
att-0a0c 是数字经济辅修简章，保留 13 条办事规则，删 11 条宣传与过期时间。
"""
from __future__ import annotations

import json
import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
ITEMS = ROOT / "items.json"
CHUNK = ROOT / "_review_items" / "chunks" / "auto_20.txt"
BACKUP = ROOT / "_review_items" / "items_before_auto_20.json"
LOG = ROOT / "_review_items" / "applied_auto_20.txt"

DROP_SOURCES = {
    "ae319fe4": "2023 年本科招生章程，面向高考考生与家长，学费住宿费为 2022 年标准",
    "aeb52846": "智慧财务报销操作手册，面向教职工报账，含截图占位与残句",
    "aeb74d15": "研究生院教改项目申报与成绩修改，服务对象为教师",
    "afb562dc": "中传 APP 校友返校注册指南，面向已毕业校友",
    "att-0794": "财务签字备案留底表，面向部门经费负责人",
    "att-085a": "保留入学资格申请表勾选项残片，无完整规则",
    "att-0b45": "高等学校财务制度（2013 年施行），面向高校财务机构，无学生办事信息",
    "ace5831c": "2021 年转专业管理办法，已被 2025 年办法取代，公示期与组织学期等规则已变",
}

DROPS = {
    # ---- aad83084 混合式教学与校历残句 ----
    "pt-6121d3bda3": "教师混合式教学资格与排课，面向教师",
    "pt-9ca8c5ce32": "校历信息残句，无完整表述",
    # ---- ac35a75d 与 6cbe728b 同一份博士培养规定的重复条目 ----
    "pt-0a6fe9c243": "补修课程要求，与 pt-d54cfca4be 同文（仅序号不同）",
    "pt-2c2ed233c2": "发表学术论文要求，与 pt-a80cefbca1 同文",
    "pt-4ecf066392": "学术汇报要求，与 pt-c07be7c0d4 同文",
    "pt-522bf65629": "最长修业年限，与 pt-bfb158b868 规范化后完全相同",
    "pt-57799a536a": "社会服务要求，与 pt-1b2663cfdb 同文",
    "pt-ca40ef9ffb": "国际学术会议要求，与 pt-6a5249f191 同文",
    "pt-eb3c291be5": "文献阅读数量，与 pt-06698eba72 规范化后完全相同",
    # ---- att-0a0c 数字经济辅修简章：宣传与过期时间 ----
    "pt-22bcf29fe3": "毕业生能力第 4 项，无办事信息",
    "pt-02e08633ae": "2025 年 5 月公布录取名单，年度已过",
    "pt-3019714b99": "毕业生能力第 5 项，无办事信息",
    "pt-72bcccb03d": "培养要求中的思政表述，套话",
    "pt-83b0aea7d6": "专业研究范围介绍，无办事信息",
    "pt-9d42780cca": "培养目标，宣传性内容",
    "pt-cb7cd8a74f": "毕业生能力第 1 项，无办事信息",
    "pt-cc9aca2191": "毕业生能力第 2 项，无办事信息",
    "pt-d17b560fd6": "毕业去向介绍，无办事信息",
    "pt-fbf6726afa": "毕业生能力第 3 项，无办事信息",
    "pt-fdba62c8b2": "数字经济背景介绍，宣传性内容",
}

# aaf7b0fc 征兵条例：学生可直接使用的条件、登记、应征、优待与后果
ZF_KEEP = {
    "pt-03623e6472", "pt-0584876002", "pt-0631b8650d", "pt-07a1c97791",
    "pt-11e7bc7c5d", "pt-1cfb0a52f0", "pt-1fe1f5d5f4", "pt-2057fc4a83",
    "pt-2541dfe477", "pt-48da4f46c0", "pt-4f716b74f1", "pt-559a40f9f7",
    "pt-5c24ffd7f4", "pt-77878384cb", "pt-a640835ef1", "pt-a6965dab20",
    "pt-b4b7ef9643", "pt-baaf25bcef", "pt-cafe98b3ac", "pt-d227e1c875",
    "pt-e24a5edd3e", "pt-e80cb79404", "pt-e84f68a66a", "pt-eb027b8f3e",
    "pt-fa4a93a208",
}
ZF_DEFAULT_REASON = "征兵工作中的机构职责、军地运输保障与退回处理程序，非学生可直接使用"

# aa7cb24a 入团细则：只保留学生申请侧事实
AA_KEEP = {
    "pt-8f729856af", "pt-92b324ac1a", "pt-ad99c340c0", "pt-aff154df3f",
    "pt-ba53c0b45d", "pt-c2664ae5ef", "pt-cf0a97f688", "pt-d89522569e",
    "pt-dac93084cc", "pt-db4926f3fa", "pt-dc819f81e0", "pt-e6c5d2e57c",
    "pt-f83df22356",
}
AA_DEFAULT_REASON = "团组织发展团员的内部程序与职责，非学生可直接使用的事项"

# ac35a75d 博士培养规定：学生可执行的环节、期限、学分与答辩要求
BS_KEEP = {
    "pt-0d874657a0", "pt-0faa51e517", "pt-122b910425", "pt-12a473a56e",
    "pt-132b5c84fd", "pt-1376150268", "pt-15ad170b6d", "pt-16078f1b91",
    "pt-16eee2d86f", "pt-17d4c6d2ec", "pt-18526e497a", "pt-1b6b1389f4",
    "pt-1bce2300e0", "pt-1e443e9977", "pt-1f04e743ab", "pt-21829cca59",
    "pt-29fb9fd805", "pt-2b4088e6e4", "pt-3554ebc530", "pt-36d953d8c2",
    "pt-37b3ed5af7", "pt-392d11ff44", "pt-41166e3611", "pt-41aa46b5fa",
    "pt-4c4e18bebd", "pt-5977d3d432", "pt-5f4fa6a581", "pt-6196383280",
    "pt-62b593a3d9", "pt-73128ee967", "pt-74d6b94b50", "pt-7cb0e8b888",
    "pt-7cb23e0d09", "pt-7d0d609f18", "pt-7d247747d9", "pt-7ec3be906c",
    "pt-819439e4e4", "pt-8718f5ff1a", "pt-a1bc115a43", "pt-a21bb14dda",
    "pt-a81547e680", "pt-a90b629c77", "pt-abb4098f81", "pt-b11f8d52cd",
    "pt-b848bdc3fc", "pt-b98e146a35", "pt-c09b892c45", "pt-c77db6f79d",
    "pt-cd779e941e", "pt-cf6d323159", "pt-d0171143fd", "pt-d54f1f38eb",
    "pt-d8fd1d6ea5", "pt-db30d21104", "pt-dd55e8d998", "pt-dd87b20f8d",
    "pt-ddce41a183", "pt-df90a6422e", "pt-e359acf42d", "pt-e742d032d9",
    "pt-ea50a61af1", "pt-f52935bc57",
}
BS_DEFAULT_REASON = "博士生培养中的培养方案制定、课程表、机构职责、定义与目的条款，非学生可直接操作"

KEEP_SOURCES = [
    ("aaf7b0fc", ZF_KEEP, ZF_DEFAULT_REASON),
    ("aa7cb24a", AA_KEEP, AA_DEFAULT_REASON),
    ("ac35a75d", BS_KEEP, BS_DEFAULT_REASON),
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

    for pid, reason in DROPS.items():
        if pid not in chunk_set:
            raise SystemExit(f"目标条目不在 auto_20 分块内：{pid}")
        if pid not in items:
            raise SystemExit(f"条目不存在：{pid}")
        drops[pid] = reason

    for prefix, keep, default_reason in KEEP_SOURCES:
        seen = 0
        for pid in chunk_ids:
            src = (items[pid].get("evidence", {}).get("answer", {}) or {}).get("src", "")
            if not src.startswith(prefix):
                continue
            seen += 1
            if pid in keep or pid in drops:
                continue
            drops[pid] = default_reason
        missing = keep - chunk_set
        if missing:
            raise SystemExit(f"{prefix} 保留清单有误，条目不在分块内：{sorted(missing)}")
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
