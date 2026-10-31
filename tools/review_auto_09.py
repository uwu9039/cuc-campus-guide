"""auto_09 人工复核：整源剔除新闻、讲座、党建、展演、活动预告与过期通知，
保留学生行为准则、校外招生培训禁令、研究生培养管理、图书馆、传媒博物馆与
本科毕业论文人工智能规范等政策原文条目。

判定原则：
- 整源剔除：新闻、活动回顾、党建、获奖、展演预告、政治文章、过期名单
- 同条碎片：同一条款的碎片先核对，确认并入完整条目后再删
- 导航栏与截断：按原文连续段落重排，只取同源连续原文，不合成
- 每条改写后必须是原文连续片段，否则保留原引文并单独报告
"""
from __future__ import annotations

import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
ITEMS = ROOT / "items.json"
CHUNK = ROOT / "_review_items" / "chunks" / "auto_09.txt"
LOG = ROOT / "_review_items" / "applied_auto_09.txt"

SOURCE_DIRS = ("", "wechat", "crawl", "cdp", "pdf", "chsi", "moe", "national", "extra",
               "huibian", "local", "wendao-extra", "wendao-text", "attachments/text", "ilib-text")

DROP_SOURCES = {
    "20260621-c2064a271925": "学院党代会学习新闻",
    "20260505-c2064a269839": "习近平关于全民阅读的论述节录，非校园办事信息",
    "20260601-c2064a271193": "学术论坛新闻",
    "20260801-c2064a273091": "展览新闻与策展感想",
    "20260621-c2064a271930": "课程路演新闻",
    "20260621-c2064a271933": "毕业典礼新闻",
    "20260701-c2064a272347": "新书发布会新闻",
    "20260601-c2064a271196": "运动会新闻",
    "20260601-c2064a271203": "合唱比赛新闻",
    "20260601-c2064a271194": "学生人物报道",
    "20260601-c2064a271195": "影像征集活动",
    "20260701-c2064a272344": "校园开放日新闻",
    "20260801-c2064a273090": "专题党课新闻",
    "20260601-c2064a271190": "读书活动新闻",
    "20260620-c2064a271917": "调研活动新闻",
    "20260621-c2065a271931": "展览预告",
    "20260601-c2064a271191": "课程报道",
    "20260601-c2064a271198": "书评活动新闻",
    "20260701-c2064a272340": "讲座回顾",
    "20260801-c2064a273092": "教师发展中心成立新闻",
    "20260620-c2065a271921": "路演预告",
    "20260601-c2064a271189": "作品获奖新闻",
    "20260601-c2064a271199": "非遗进校园活动新闻",
    "20260701-c2064a272343": "党课培训新闻",
    "20260701-c2064a272345": "讲座回顾",
    "20260621-c2064a271927": "心理健康活动新闻",
    "20260701-c2064a272346": "毕业作品展新闻",
    "20260621-c2064a271926": "诚信教育班会新闻",
    "20260601-c2064a271192": "学院五年成就宣传",
    "20260601-c2064a271184": "政绩观论述，非校园办事信息",
    "20260801-c2064a273088": "讲座回顾",
    "20260603-c2065a271333": "展览预告",
    "20260601-c2065a271185": "节日祝福",
    "20260507-c6364a269956": "辅修录取名单已过期",
    "20260620-c2065a271922": "2026年暑期调研申报通知已过期",
}

DROPS = {
    # 学生行为准则：二的两句话碎片并入 pt-bfdd83e2e0，施行条并入 pt-ce923fb2fb
    "pt-1061dcd9b9": "行为准则（二）碎片，已并入 pt-bfdd83e2e0",
    "pt-6b1cd5609f": "行为准则（二）碎片，已并入 pt-bfdd83e2e0",
    "pt-ff1daf0229": "施行与解释条已并入 pt-ce923fb2fb",
    # 退宿规定：整条为导航栏拼接，退宿办事信息已有 sushe-tuixiu 等专题条目
    "pt-c0b06d6481": "导航栏拼接，退宿流程已有 sushe-tuixiu 等专题条目",
    # 校外招生培训：碎片并入对应条文
    "pt-3ae776fcda": "已并入 pt-305ec3fb2d（第五条完整条文）",
    "pt-7d9785e023": "已并入 pt-81806ec00b（附则第一条完整条文）",
    "pt-55e9f5a609": "已并入 pt-e0d66c8a7f（附则第三条完整条文）",
    # 博士匿名评阅：重复碎片并入 pt-656fa603b0
    "pt-3c7b04b3e7": "已并入 pt-656fa603b0（第十三条完整条文）",
    # 硕博连读转硕士：碎片并入对应条文
    "pt-0e6057dee7": "已并入 pt-9269392f14（第六条完整条文）",
    "pt-425568d986": "已并入 pt-dec27ca668（第七条完整条文）",
    "pt-f39427535f": "已并入 pt-dec27ca668（第七条完整条文）",
    # 图书馆：整条为导航栏拼接，借阅规则已有 lib-jieyue
    "pt-ec8d9eba2f": "导航栏拼接，借阅规则已有 lib-jieyue 专题条目",
    # 传媒博物馆简介：服务口号、合作项目、获奖与学会职务，非办事信息
    "pt-ad6f30d7fa": "服务口号，非办事信息",
    "pt-14ac31c359": "合作办学与学术活动介绍，非办事信息",
    "pt-1dfad2a960": "空泛总结句",
    "pt-b795b4cce8": "博物馆获奖与基地称号，非办事信息；国家二级博物馆另有 pt-3713f4534e",
    "pt-de41017a93": "学会职务，非办事信息",
    # 论文AI：碎片并入对应条文
    "pt-8eb4243382": "已并入 pt-da4767bf6a（第三条完整条文）",
    "pt-83cd5ca703": "已并入 pt-cde03d3404（第六条完整条文）",
    "pt-c8e636b461": "已并入 pt-11c6c3de31（第七条（一）完整条文）",
    "pt-7569ea3fe6": "已并入 pt-4cb0e95460（第七条（二）完整条文）",
    "pt-fb3100e516": "已并入 pt-d183d85d31（第七条（三）完整条文）",
    "pt-511c9dc253": "已并入 pt-3eb4393b83（第十四条完整条文）",
}

A = "20260528-c2753a271112"  # 学生行为准则
B = "20260529-c2753a271135"  # 校外招生培训
C = "20260529-c2753a271139"  # 硕博连读转硕士
D = "20260529-c2753a271142"  # 传媒博物馆简介
E = "20260716-c2753a272808"  # 本科毕业论文人工智能
F = "20260529-c2753a271140"  # 图书馆文献借阅


def squash(s: str) -> str:
    return re.sub(r"\s+", "", s or "")


def raw_lines(src: str) -> list[str]:
    for sub in SOURCE_DIRS:
        p = (ROOT / "sources" / sub if sub else ROOT / "sources") / f"{src}.txt"
        if p.exists():
            with p.open("r", encoding="utf-8", newline="") as f:
                return f.read().split("\n")
    raise SystemExit(f"源文件不存在：{src}")


def L(src: str, a: int, b: int | None = None) -> str:
    lines = raw_lines(src)
    if b is None:
        b = a
    return "\n".join(x.strip() for x in lines[a - 1:b])


SPECIAL = {
    # 学生行为准则：制定依据 + 施行时间；二为完整两句
    "pt-ce923fb2fb": L(A, 45) + "\n" + L(A, 54),
    "pt-bfdd83e2e0": L(A, 47),
    # 校外招生培训：补齐被截断的条款
    "pt-1b34ef0af6": L(B, 66),
    "pt-3e91e29b9e": L(B, 67),
    "pt-305ec3fb2d": L(B, 71),
    "pt-81806ec00b": L(B, 73),
    "pt-e0d66c8a7f": L(B, 75),
    # 硕博连读转硕士：补齐程序条尾句
    "pt-9269392f14": L(C, 56),
    "pt-dec27ca668": L(C, 57),
    "pt-19d5343775": L(C, 63),
    # 传媒博物馆简介：去掉导航栏
    "pt-8a591fd283": L(D, 44),
    # 图书馆：无法确定原价的完整赔偿标准
    "pt-aba84c2ae8": L(F, 58, 70),
    # 论文AI：补齐各条被截断的句子
    "pt-1f9ca87fe0": L(E, 47),
    "pt-da4767bf6a": L(E, 48),
    "pt-b177838537": L(E, 49),
    "pt-cde03d3404": L(E, 52),
    "pt-11c6c3de31": L(E, 54) + "\n" + L(E, 55),
    "pt-4cb0e95460": L(E, 56),
    "pt-d183d85d31": L(E, 57),
    "pt-3eb4393b83": L(E, 69),
    # 匿名评阅：补齐重复率检测后申请答辩一句
    "pt-e8309098e6": L("20260529-c2753a271136", 57),
    "pt-656fa603b0": L("20260529-c2753a271137", 57),
}

TITLES = {
    # 学生行为准则（9）
    "pt-ce923fb2fb": "学生行为准则（修订）的制定依据与施行时间",
    "pt-093ea355db": "学生行为准则（一）志存高远，坚定信念",
    "pt-bfdd83e2e0": "学生行为准则（二）热爱祖国，服务人民",
    "pt-58de99c369": "学生行为准则（三）勤奋学习，自强不息",
    "pt-6eb2f9ddf0": "学生行为准则（四）遵纪守法，弘扬正气",
    "pt-7f3fd79c21": "学生行为准则（五）诚实守信，严于律己",
    "pt-e311790456": "学生行为准则（六）明礼修身，团结友爱",
    "pt-4ea739d8bb": "学生行为准则（七）勤俭节约，艰苦奋斗",
    "pt-4ea0e18257": "学生行为准则（八）强健体魄，热爱生活",
    # 严禁参与校外招生培训（23）
    "pt-3ad2e0bebb": "严禁参与校外招生培训工作规定的制定目的与依据",
    "pt-d1e246a5bd": "严禁参与校外招生培训规定的适用范围",
    "pt-df25c7e349": "严禁为校外培训机构提供校内场所与宣传便利",
    "pt-a4b352e836": "严禁与招生考试培训机构或个人开展合作",
    "pt-6ff7e7ae02": "师生禁止参与考前辅导、应试培训与志愿填报辅导",
    "pt-908733197b": "禁止向培训机构提供考试信息、试题与答案",
    "pt-7ec81f35df": "禁止为培训机构宣传或推荐学生",
    "pt-c1c1781f85": "禁止与培训机构勾连牟利或收受财物",
    "pt-2230e9c2fc": "部门单位违反校外招生培训规定的处理",
    "pt-d5cd0e7eff": "教职工违反校外招生培训规定的处理（列入黑名单等）",
    "pt-cc33d5efe8": "教职工违规当年的考核与评优限制",
    "pt-54654a8d04": "教职工违规可给予警告直至开除处分",
    "pt-a047168b65": "教职工违反师德规范的另行处理",
    "pt-4d6f42e02c": "学生违反校外招生培训规定的处理（通报批评等）",
    "pt-1b34ef0af6": "学生违规收受财物的纪律处分",
    "pt-3e91e29b9e": "学生与机构勾连牟取不正当利益的纪律处分",
    "pt-c5a3b29b85": "学生严重破坏招生公平的纪律处分（直至开除学籍）",
    "pt-b38666cda6": "其他违反校外招生培训规定的处理",
    "pt-9e064d6c14": "违反校外招生培训规定的法律责任",
    "pt-305ec3fb2d": "违反校外招生培训规定的调查与处理部门",
    "pt-81806ec00b": "离退休人员与校外人员的参照执行",
    "pt-27ec2d9839": "严禁参与校外招生培训工作规定的解释单位",
    "pt-e0d66c8a7f": "本规定与上级文件不一致时的适用",
    # 匿名评阅（2）
    "pt-e8309098e6": "硕士生答辩未获学位后重新申请学位的匿名评阅结果",
    "pt-656fa603b0": "博士生答辩未获学位后重新申请学位的匿名评阅结果",
    # 硕博连读转硕士（14）
    "pt-ccfbdc1f5b": "硕博连读生、直博生转为硕士生培养管理办法的制定目的",
    "pt-2ed2530822": "硕博连读生、直博生转为硕士生培养管理办法的适用范围",
    "pt-aed3e2cde5": "博士生申请转为硕士生的时间条件",
    "pt-13e91affcd": "博士生可申请转为硕士生培养的学业情形",
    "pt-9269392f14": "博士生转为硕士生的申请与审批程序",
    "pt-dec27ca668": "跨学科硕博连读生退回原学科转为硕士生的程序",
    "pt-1383c47a76": "转硕后培养单位、专业与责任导师原则上不变",
    "pt-f567c951f7": "研究生学籍变动的办理依据",
    "pt-5809f7c954": "转硕后须按硕士培养方案重新制定培养计划",
    "pt-ac57044ab7": "转硕后博士期间课程的学分认定",
    "pt-176fc420e7": "转硕前已完成培养环节的认定",
    "pt-077ab40968": "转硕后的毕业与硕士学位申请",
    "pt-19d5343775": "转硕后不再具有硕博连读资格",
    "pt-68789d87b0": "国际博士生分流参照本办法",
    # 传媒博物馆团体参观（1）
    "pt-90eed29dfb": "传媒博物馆开放时间",
    # 传媒博物馆简介（3）
    "pt-8a591fd283": "传媒博物馆简介",
    "pt-11027b0a2f": "传媒博物馆的分馆设置与馆藏规模",
    "pt-3713f4534e": "传媒博物馆为国家二级博物馆",
    # 图书馆（1）
    "pt-aba84c2ae8": "无法确定原价的图书赔偿标准",
    # 传媒博物馆场馆管理规定（10）
    "pt-071dfd3ca7": "传媒博物馆面向社会免费开放",
    "pt-e75441cfc9": "新生入馆教育由各学院提前预约组织",
    "pt-b82f982b79": "传媒博物馆入馆方式（一卡通、刷脸、身份证登记）",
    "pt-81915b1cc7": "传媒博物馆谢绝入馆的情形",
    "pt-8d284561d5": "传媒博物馆入馆安检要求",
    "pt-b53d5eb75d": "馆内禁止携带食品饮料与吸烟",
    "pt-bc9713e398": "馆内拍摄须经馆方批准",
    "pt-eb86d4e763": "传媒博物馆参观秩序要求",
    "pt-dcbfebe40d": "参观须服从馆内工作人员管理",
    "pt-538d481d08": "传媒博物馆场馆管理规定的解释单位",
    # 临时展厅管理办法（7）
    "pt-4c58e3ca3e": "传媒博物馆临时展厅的用途",
    "pt-76d9d1aa9b": "校内单位免费使用临时展厅，展期原则上7—14天",
    "pt-ac97a194cb": "临时展厅使用申请须提前30天提交",
    "pt-4a8b51bd7c": "校外单位申请临时展厅须提供主办方信函原件",
    "pt-0ca2eb509a": "临时展厅展览申请的审核时限",
    "pt-2e177cf6e5": "临时展厅内禁止锯刨钻焊油漆作业",
    "pt-02cd8b2861": "传媒博物馆不提供展品安保服务",
    # 本科毕业论文人工智能使用规范（18）
    "pt-f8aba7fe31": "本科毕业论文使用人工智能的合法合规原则",
    "pt-1f9ca87fe0": "本科毕业论文使用人工智能的学术诚信原则",
    "pt-da4767bf6a": "本科毕业论文使用人工智能的风险可控原则",
    "pt-b177838537": "本科毕业论文使用人工智能的权责一致原则",
    "pt-b7af79b28a": "学生是毕业论文使用人工智能的直接责任主体",
    "pt-cde03d3404": "指导教师对论文使用人工智能的告知与审核责任",
    "pt-11c6c3de31": "毕业论文可使用人工智能辅助的非核心环节",
    "pt-4cb0e95460": "论文数据分析与可视化使用人工智能的要求",
    "pt-d183d85d31": "毕业论文禁止使用人工智能生成的内容",
    "pt-9cbe6bc3b3": "毕业设计可使用人工智能的范围与留痕要求",
    "pt-723822ea6f": "毕业设计禁止由人工智能完全生成作品",
    "pt-c3fca370b6": "毕业设计报告可用人工智能润色但不得生成创作阐述",
    "pt-82b1de7419": "使用人工智能须提交情况说明表并标注工具",
    "pt-5ed858a875": "未提交人工智能使用说明者不得参加答辩",
    "pt-33242e6b25": "答辩中须解释人工智能使用过程并验证原创性",
    "pt-19ab2ed271": "违反人工智能使用规范的处分",
    "pt-ca536d913e": "各学院可进一步明确人工智能使用要求",
    "pt-3eb4393b83": "本科毕业论文人工智能使用规范的适用范围",
    # 暑假期间办理成绩单等材料（4）
    "pt-8459fc0966": "可信电子凭证的效力与打印使用",
    "pt-0c87bbf639": "本科生院公共邮箱可转发电子版成绩单",
    "pt-dbedfc9a66": "成绩单等材料邮件申请的审核时间与主题格式",
    "pt-821e174cd6": "成绩单盖章现场不提供打印服务",
}

# 大厅类拼接条：引文取原文连续段
QUOTES = {
    "pt-ce923fb2fb": L(A, 45),
}


def load_texts() -> dict[str, str]:
    texts: dict[str, str] = {}
    for sub in SOURCE_DIRS:
        base = ROOT / "sources" / sub if sub else ROOT / "sources"
        for f in base.glob("*.txt"):
            texts[f.stem] = squash(f.read_text(encoding="utf-8"))
    return texts


def retitle(item: dict, new_answer: str) -> None:
    old = item.get("title", "")
    suffix = ""
    if " · " in old:
        suffix = " · " + old.rsplit(" · ", 1)[1]
    title = TITLES.get(item["id"], new_answer[:40] + ("…" if len(new_answer) > 40 else ""))
    title = title.replace("\n", " ")
    item["title"] = title + suffix
    aliases = item.get("aliases") or []
    if aliases:
        aliases[0] = title
        item["aliases"] = aliases


def main() -> None:
    dry = "--dry-run" in sys.argv
    data = json.loads(ITEMS.read_text(encoding="utf-8"))
    items = {it["id"]: it for it in data["items"]}
    texts = load_texts()

    chunk_ids = []
    for line in CHUNK.read_text(encoding="utf-8").splitlines():
        if line.strip():
            chunk_ids.append(line.split()[0])
    chunk_set = set(chunk_ids)

    drops = dict(DROPS)
    src_counts: dict[str, int] = {}
    for pid in chunk_ids:
        src = (items[pid].get("evidence", {}).get("answer", {}) or {}).get("src", "")
        if src in DROP_SOURCES:
            drops[pid] = DROP_SOURCES[src]
            src_counts[src] = src_counts.get(src, 0) + 1

    changes = {}
    for pid, new in SPECIAL.items():
        if new and new != items[pid].get("answer"):
            changes[pid] = new

    overlap = set(drops) & set(changes)
    if overlap:
        raise SystemExit(f"同一条既删又改：{overlap}")
    targets = set(drops) | set(changes)
    outside = sorted(targets - chunk_set)
    if outside:
        raise SystemExit(f"目标条目不在 auto_09 分块内：{outside}")
    missing = [pid for pid in targets if pid not in items]
    if missing:
        raise SystemExit(f"条目不存在：{missing}")

    survivors = [pid for pid in chunk_ids if pid not in drops]
    no_title = [pid for pid in survivors if pid not in TITLES]
    if no_title:
        raise SystemExit(f"存留条目缺少标题：{no_title}")

    not_in_source = []
    for pid, new in changes.items():
        src = (items[pid].get("evidence", {}).get("answer", {}) or {}).get("src", "")
        if squash(new) not in texts.get(src, ""):
            not_in_source.append((pid, src, new[:60]))

    log: list[str] = []
    for src, n in sorted(src_counts.items()):
        log.append(f"SOURCE {src}  删除 {n} 条：{DROP_SOURCES[src]}")
    for pid, reason in sorted(drops.items()):
        log.append(f"DROP  {pid}  {reason}  |  {str(items[pid].get('answer') or '')[:50]}")
    for pid in sorted(changes):
        log.append(f"FIX   {pid}  {str(items[pid].get('answer') or '')[:50]}  ->  {changes[pid][:70]}")
    log.append(f"TITLE 存留 {len(survivors)} 条全部重写标题")

    print(f"整源剔除 {len(src_counts)} 个来源，删除 {len(drops)} 条，修改 {len(changes)} 条，"
          f"当前 {len(data['items'])} 条，存留 {len(survivors)} 条")
    if not_in_source:
        print(f"\n改写后不是原文连续片段 {len(not_in_source)} 条（保留原引文）：")
        for pid, src, head in not_in_source:
            print(f"  {pid} {src} {head}")

    if dry:
        print("\n".join(log))
        return

    for pid in drops:
        data["items"].remove(items[pid])
    for pid, new in changes.items():
        it = items[pid]
        it["answer"] = new
        ev = (it.get("evidence") or {}).get("answer")
        if ev:
            if pid in QUOTES:
                ev["quote"] = QUOTES[pid]
            elif squash(new) in texts.get(ev.get("src", ""), ""):
                ev["quote"] = new
    for pid in survivors:
        retitle(items[pid], items[pid].get("answer") or "")

    ITEMS.write_text(json.dumps(data, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
    LOG.write_text("\n".join(log) + "\n", encoding="utf-8")
    print(f"已写回，剩余 {len(data['items'])} 条；日志 {LOG.relative_to(ROOT)}")


if __name__ == "__main__":
    main()