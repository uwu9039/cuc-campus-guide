"""auto_05 人工复核：预算法条文截断与备案条款主语、辅导员职责标题粘连、
档案办法章标题与第四十条清单、军训通知标题粘连、就业通知公文头与站点导航、
财务处页面导航、教师专访人物稿、双选月联系人、勤工助学设岗原则。

判定原则：
- 只删不可独立成句、页面导航粘连、或内容已被合并条完整保留的自动碎片
- 能修的优先修：去章标题、补全被截断的条文、给公文标题与正文补分隔
- 列表残段合并回主条后再删碎片，删前逐条核对
"""
from __future__ import annotations

import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
ITEMS = ROOT / "items.json"
CHUNK = ROOT / "_review_items" / "chunks" / "auto_05.txt"
LOG = ROOT / "_review_items" / "applied_auto_05.txt"

DROPS = {
    # 页面导航粘连，非事项
    "pt-6dc6af1b10": "财务处页面导航，非事项",
    "pt-75996adfdd": "财务处页面导航，非事项",
    "pt-22a0d43033": "财务处页面导航，非事项",
    "pt-9238ac10f0": "站点导航与公文头粘连，非事项",
    "pt-a8b87450a2": "站点导航与公文头粘连，非事项",
    "pt-6c63834095": "站点导航与公文头粘连，非事项",
    "pt-3fd8f71a75": "站点导航与公文头粘连，非事项",
    "pt-ebcf546754": "站点导航与公文头粘连，非事项",
    "pt-0ce486d2ac": "站点导航与公文头粘连，非事项",
    # 教师专访人物稿，非办事事项；三条团队成果条目保留
    "pt-099b74d045": "教师专访人物稿，非事项",
    "pt-0ba096a523": "教师专访人物稿，非事项",
    "pt-0ecfe7f64d": "教师专访人物稿，非事项",
    "pt-0ffa050f1c": "教师专访人物稿，非事项",
    "pt-144c250b40": "教师专访人物稿，非事项",
    "pt-14aafe8629": "教师专访人物稿，非事项",
    "pt-19cb2d30be": "教师专访人物稿，非事项",
    "pt-279ba8efa6": "教师专访人物稿，非事项",
    "pt-28b7e7a784": "教师专访人物稿，非事项",
    "pt-294bb8f954": "教师专访人物稿，非事项",
    "pt-30e49cca53": "教师专访人物稿，非事项",
    "pt-371bf151c6": "教师专访人物稿，非事项",
    "pt-3cfae1036c": "教师专访人物稿，非事项",
    "pt-42b93c7907": "教师专访人物稿，非事项",
    "pt-435b1e8ee1": "教师专访人物稿，非事项",
    "pt-47b22f9ce5": "教师专访人物稿，非事项",
    "pt-4ab3450d90": "教师专访人物稿，非事项",
    "pt-4d6c25e289": "教师专访人物稿，非事项",
    "pt-50bb16e517": "教师专访人物稿，非事项",
    "pt-5771f7cbb5": "教师专访人物稿，非事项",
    "pt-5a74cc2abc": "教师专访人物稿，非事项",
    "pt-5ce46b21f6": "教师专访人物稿，非事项",
    "pt-5df50bccf3": "教师专访人物稿，非事项",
    "pt-61c2add2d2": "教师专访人物稿，非事项",
    "pt-65d183b020": "教师专访人物稿，非事项",
    "pt-7c309c1269": "教师专访人物稿，非事项",
    "pt-84f4cbcd77": "教师专访人物稿，非事项",
    "pt-87255785a9": "教师专访人物稿，非事项",
    "pt-953caf467b": "教师专访人物稿，非事项",
    "pt-99fd15d8c1": "教师专访人物稿，非事项",
    "pt-9ed2cfd97e": "教师专访人物稿，非事项",
    "pt-a05c714e61": "教师专访人物稿，非事项",
    "pt-a4eca2b80a": "教师专访人物稿，非事项",
    "pt-a8f46636a1": "教师专访人物稿，非事项",
    "pt-ace6c1c942": "教师专访人物稿，非事项",
    "pt-aeff5b0326": "教师专访人物稿，非事项",
    "pt-b6f7822f6c": "教师专访人物稿，非事项",
    "pt-c0b2077cbb": "教师专访人物稿，非事项",
    "pt-c268841fd8": "教师专访人物稿，非事项",
    "pt-c3547fcb54": "教师专访人物稿，非事项",
    "pt-c79215a05b": "教师专访人物稿，非事项",
    "pt-cbfa417086": "教师专访人物稿，非事项",
    "pt-d40339f897": "教师专访人物稿，非事项",
    "pt-d4527fc1a7": "教师专访人物稿，非事项",
    "pt-d582761aac": "教师专访人物稿，非事项",
    "pt-e637f9d492": "教师专访人物稿，非事项",
    "pt-e8e0ca2c1b": "教师专访人物稿，非事项",
    "pt-ebf2089ff6": "教师专访人物稿，非事项",
    "pt-ece83a77a0": "教师专访人物稿，非事项",
    "pt-eeb5e5ff5b": "教师专访人物稿，非事项",
    "pt-f627942a62": "教师专访人物稿，非事项",
    "pt-f891d1ae3a": "教师专访人物稿，非事项",
    "pt-ff8e772fab": "教师专访人物稿，非事项",
    # 预算法残段，内容并入主条
    "pt-99b5e5e248": "第四十八条（五）至（八），内容并入 pt-42da05ee96",
    "pt-807e4cd2eb": "第十六条尾句，内容并入 pt-891f09b05c",
    "pt-eedeb190b0": "第五十四条尾句，内容并入 pt-5f357f20df",
    # 列表残段合并回主条
    "pt-19f72fdbac": "辅导员职责领起句与（一）标题，内容并入 pt-4dfc69ae37",
    "pt-33d7412430": "归档范围（四）尾句，内容并入 pt-f23bfe13a3",
    "pt-1da6ef5986": "第四十条（一）至（六），内容并入 pt-1539edd42a",
    # 联系人拆条，合并为完整一行
    "pt-022b49cb0d": "双选月第三位联系人，内容并入 pt-bad529c5d3",
}

TAIL_TRIM = {
    "pt-83a7d9ee0e": "第二章预算管理职权",
    "pt-e8f50300e7": "第二章机构设置与人员配备",
}

PREPEND = {
    "pt-43cbd64f41": ("国务院和县级以上地方各级政府对下一级政府依照本法第八十一条", "规定报送备案的决算"),
    "pt-44500acdc3": ("国务院和县级以上地方各级政府对下一级政府依照本法第五十条", "规定报送备案的预算"),
    "pt-4dfc69ae37": ("辅导员的主要工作职责是：（一）思想理论教育和价值引领。", "引导学生深入学习"),
}

SUB = {
    "pt-42da05ee96": (
        "（五）预算的编制是否完整，是否符合本法",
        "（五）预算的编制是否完整，是否符合本法第四十六条的规定；"
        "（六）对下级政府的转移性支出预算是否规范、适当；"
        "（七）预算安排举借的债务是否合法、合理，是否有偿还计划和稳定的偿还资金来源；"
        "（八）与预算有关重要事项的说明是否清晰。",
    ),
    "pt-891f09b05c": (
        "配套资金。",
        "配套资金。但是，按照国务院的规定应当由上下级政府共同承担的事项除外。",
    ),
    "pt-5f357f20df": (
        "以及用于自然灾害等突发事件处理的支出。",
        "以及用于自然灾害等突发事件处理的支出。根据前款规定安排支出的情况，应当在预算草案的报告中作出说明。",
    ),
    "pt-072c9b6b02": (
        "参与危机事件后期应对及总结研究分析。（八）职业规划与就业创业指导。",
        "参与危机事件后期应对及总结研究分析。（八）职业规划与就业创业指导。"
        "为学生提供科学的职业生涯规划和就业指导以及相关服务，帮助学生树立正确的就业观念，"
        "引导学生到基层、到西部、到祖国最需要的地方建功立业。",
    ),
    "pt-1539edd42a": (
        "构成犯罪的，由司法机关依法追究刑事责任。",
        "构成犯罪的，由司法机关依法追究刑事责任。"
        "(一)玩忽职守，造成档案损坏、丢失或者擅自销毁档案的；(二)违反保密规定，擅自提供、抄录、公布档案的；"
        "(三)涂改、伪造档案的；(四)擅自出卖、赠送、交换档案的；"
        "(五)不按规定归档，拒绝归档或者将档案据为己有的；(六)其他违反档案法律法规的行为。",
    ),
    "pt-f23bfe13a3": (
        "等活动的文件材料。",
        "等活动的文件材料。按原国家教委、国家档案局发布的《高等学校教学文件材料归档范围》"
        "((87)教办字016号)的相关规定执行。",
    ),
    "pt-3409f3f871": ("（二）加强师生安全教育加强学生安全教育。", "（二）加强师生安全教育。加强学生安全教育。"),
    "pt-5199ca4e75": ("（五）规范承训基地管理学生军事训练基地", "（五）规范承训基地管理。学生军事训练基地"),
    "pt-74fc27f747": ("（三）确保训练活动安全学校负责人", "（三）确保训练活动安全。学校负责人"),
    "pt-f587be09a9": ("（四）强化集体生活管理学生军事训练期间", "（四）强化集体生活管理。学生军事训练期间"),
    "pt-a551995191": (
        "各项工作（一）严格落实教学大纲各地教育行政部门",
        "各项工作。（一）严格落实教学大纲。各地教育行政部门",
    ),
    "pt-cabff579e8": (
        "一、充分认识加强学生军事训练管理的重要性加强学生军事训练管理",
        "一、充分认识加强学生军事训练管理的重要性。加强学生军事训练管理",
    ),
    "pt-fb9eb8863a": (
        "二、切实加强学生军事训练的组织领导各地教育行政部门",
        "二、切实加强学生军事训练的组织领导。各地教育行政部门",
    ),
    "pt-791ade5105": (
        "四、建立健全学生军事训练质量监测机制省级教育行政部门",
        "四、建立健全学生军事训练质量监测机制。省级教育行政部门",
    ),
    "pt-f915b3b374": (
        "五、积极营造学生军事训练良好环境各级教育行政部门",
        "五、积极营造学生军事训练良好环境。各级教育行政部门",
    ),
}

SPECIAL = {
    "pt-ebc668150a": (
        "经省、自治区、直辖市政府批准，乡、民族乡、镇本级预算草案、预算调整方案、决算草案，"
        "可以由上一级政府代编，并依照本法第二十一条的规定报乡、民族乡、镇的人民代表大会审查和批准。"
    ),
    "pt-c39d979cf1": "经批准的预算调整方案，各级政府应当严格执行。",
    "pt-bad529c5d3": (
        "四、联系人及联系方式教育部高校学生司：简成章，电话010-66097835；"
        "国务院国资委综合局：孙家琛，电话010-63192686；"
        "教育部全国高等学校学生信息咨询与就业指导中心：习俊男，电话010-62111790，邮箱＊＊@＊＊。"
    ),
    "pt-b54a8978a9": (
        "教育部办公厅关于进一步做好高校毕业生就业创业工作的通知（教学厅〔2016〕5号）："
        "党中央、国务院高度重视高校毕业生就业创业工作。"
    ),
    "pt-b91a065f7f": (
        "教育部关于做好2019届全国普通高等学校毕业生就业创业工作的通知（教学〔2018〕8号）："
        "促进高校毕业生就业创业，既是民生，也是国计，事关广大群众切身利益，事关社会和谐稳定，"
        "事关社会主义现代化建设，事关高等教育健康发展。"
    ),
    "pt-d63c38cbcb": (
        "教育部关于加强学生军事训练管理工作的通知（教体艺〔2017〕3号）："
        "青年学生是祖国的未来和民族的希望。"
    ),
    "pt-fc06d1a10d": (
        "教育部办公厅关于下达2019年“退役大学生士兵”专项硕士研究生招生计划的通知（教学厅〔2018〕9号）："
        "设立“退役大学生士兵”专项硕士研究生招生计划（以下简称“退役大学生士兵计划”），"
        "是鼓励更多高素质高校学生参军入伍，支持国防和军队现代化建设的一项重要举措。"
    ),
    "pt-9142b96ef9": (
        "教育部关于做好2018届全国普通高等学校毕业生就业创业工作的通知（教学〔2017〕11号）："
        "就业是最大的民生。"
    ),
    "pt-7871b334c8": (
        "教育部办公厅国务院国资委办公厅关于举办全国大中型企业面向2019届高校毕业生网上双选月活动的通知"
        "（教学厅函〔2018〕43号）：为做好2019届全国普通高等学校毕业生就业工作，"
        "促进高校毕业生与国有大中型企业人才供需对接，教育部、国务院国资委定于2018年11月20日至12月20日"
        "联合举办“全国大中型企业面向2019届高校毕业生网上双选月”活动（以下简称“双选月”）。"
    ),
    "pt-ec26e6eddb": (
        "设岗原则：（一）学校应积极开发校内资源，保证学生参与勤工助学的需要。"
        "校内勤工助学岗位设置应以校内教学助理、科研助理、行政管理助理和学校公共服务等为主。"
        "按照每个家庭经济困难学生月平均上岗工时原则上不低于20小时为标准，"
        "测算出学期内全校每月需要的勤工助学总工时数（20工时×家庭经济困难学生总数），"
        "统筹安排、设置校内勤工助学岗位。"
        "（二）勤工助学岗位既要满足学生需求，又要保证学生不因参加勤工助学而影响学习。"
        "学生参加勤工助学的时间原则上每周不超过8小时，每月不超过40小时。"
        "寒暑假勤工助学时间可根据学校的具体情况适当延长。"
    ),
}


def squash(s: str) -> str:
    return re.sub(r"\s+", "", s or "")


def load_texts() -> dict[str, str]:
    texts: dict[str, str] = {}
    for sub in ("", "wechat", "crawl", "cdp", "pdf", "chsi", "moe", "national", "extra",
                "huibian", "local", "wendao-extra", "wendao-text", "attachments/text", "ilib-text"):
        base = ROOT / "sources" / sub if sub else ROOT / "sources"
        for f in base.glob("*.txt"):
            texts[f.stem] = squash(f.read_text(encoding="utf-8"))
    return texts


def retitle(item: dict, new_answer: str) -> None:
    old = item.get("title", "")
    suffix = ""
    if " · " in old:
        suffix = " · " + old.rsplit(" · ", 1)[1]
    item["title"] = new_answer[:40] + ("…" if len(new_answer) > 40 else "") + suffix
    aliases = item.get("aliases") or []
    if aliases:
        aliases[0] = new_answer[:40] + ("…" if len(new_answer) > 40 else "")
        item["aliases"] = aliases


def build_changes(items: dict[str, dict]) -> dict[str, str]:
    changes: dict[str, str] = {}
    for pid, (a, b) in SUB.items():
        old = items[pid]["answer"]
        if a not in old:
            raise SystemExit(f"子串不匹配 {pid}: {a[:30]}")
        changes[pid] = old.replace(a, b)
    for pid, tail in TAIL_TRIM.items():
        old = items[pid]["answer"]
        if not old.endswith(tail):
            raise SystemExit(f"尾部不匹配 {pid}: {old[-30:]}")
        changes[pid] = old[:-len(tail)]
    for pid, (prefix, anchor) in PREPEND.items():
        old = items[pid]["answer"]
        if not old.startswith(anchor):
            raise SystemExit(f"待补前缀的残段不匹配 {pid}: {old[:40]}")
        changes[pid] = prefix + old
    changes.update(SPECIAL)
    overlap = set(DROPS) & set(changes)
    if overlap:
        raise SystemExit(f"同一条既删又改：{overlap}")
    return changes


def main() -> None:
    dry = "--dry-run" in sys.argv
    data = json.loads(ITEMS.read_text(encoding="utf-8"))
    items = {it["id"]: it for it in data["items"]}
    texts = load_texts()

    chunk_ids = {line.split()[0] for line in CHUNK.read_text(encoding="utf-8").splitlines() if line.strip()}
    targets = set(DROPS) | set(SUB) | set(TAIL_TRIM) | set(PREPEND) | set(SPECIAL)
    outside = sorted(targets - chunk_ids)
    if outside:
        raise SystemExit(f"目标条目不在 auto_05 分块内：{outside}")
    missing = [pid for pid in targets if pid not in items]
    if missing:
        raise SystemExit(f"条目不存在：{missing}")

    changes = build_changes(items)
    log: list[str] = []

    not_in_source = []
    for pid, new in changes.items():
        src = (items[pid].get("evidence", {}).get("answer", {}) or {}).get("src", "")
        if squash(new) not in texts.get(src, ""):
            not_in_source.append((pid, src, new[:60]))

    for pid, reason in sorted(DROPS.items()):
        log.append(f"DROP  {pid}  {reason}  |  {items[pid]['answer'][:50]}")
    for pid in sorted(changes):
        log.append(f"FIX   {pid}  {items[pid]['answer'][:50]}  ->  {changes[pid][:70]}")

    print(f"删除 {len(DROPS)} 条，修改 {len(changes)} 条，当前 {len(data['items'])} 条")
    if not_in_source:
        print(f"\n改写后不是原文连续片段 {len(not_in_source)} 条（保留原引文）：")
        for pid, src, head in not_in_source:
            print(f"  {pid} {src} {head}")

    if dry:
        print("\n".join(log))
        return

    for pid in DROPS:
        data["items"].remove(items[pid])
    for pid, new in changes.items():
        it = items[pid]
        old = it["answer"]
        if new == old or not new:
            raise SystemExit(f"空改写 {pid}")
        it["answer"] = new
        retitle(it, new)
        ev = (it.get("evidence") or {}).get("answer")
        if ev and squash(new) in texts.get(ev.get("src", ""), ""):
            ev["quote"] = new

    ITEMS.write_text(json.dumps(data, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
    LOG.write_text("\n".join(log) + "\n", encoding="utf-8")
    print(f"已写回，剩余 {len(data['items'])} 条；日志 {LOG.relative_to(ROOT)}")


if __name__ == "__main__":
    main()