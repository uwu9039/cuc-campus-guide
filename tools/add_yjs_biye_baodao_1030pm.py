"""新增研究生提前/延期毕业、研究生新生报到两条，并补别名与适用范围说明。"""
from __future__ import annotations

import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
ITEMS = ROOT / "items.json"
SRC = ROOT / "sources"

TEXTS: dict[str, str] = {}
for base in ["wechat", "crawl", "cdp", "pdf", "chsi", "moe", "national", "extra",
             "huibian", "local", "wendao-extra", "wendao-text",
             "attachments/text", "ilib-text"]:
    for f in (SRC / base).glob("*.txt"):
        TEXTS[f.stem] = re.sub(r"\s+", "", f.read_text(encoding="utf-8", errors="ignore"))


def check(src: str, quote: str) -> dict:
    assert src in TEXTS, f"来源不存在：{src}"
    assert re.sub(r"\s+", "", quote) in TEXTS[src], f"引文找不到：{src} {quote}"
    return {"src": src, "quote": quote}


def item(iid, title, aliases, keywords, steps, ev_src, scope_note=None,
         scope_note_if=None, exclude=None, location=None, location_quote=None,
         materials=None, material_quotes=None):
    data = {"id": iid, "title": title, "dept": "中国传媒大学",
            "aliases": aliases, "keywords": keywords,
            "steps": [{"when": w, "what": t, "where": "研究生院"} for w, t, _q in steps],
            "evidence": {}, "source": ev_src}
    data["evidence"].update({f"steps.{i}": check(ev_src, q)
                             for i, (_, _, q) in enumerate(steps)})
    if location:
        data["location"] = location
        data["evidence"]["location"] = check(ev_src, location_quote)
    if materials:
        data["materials"] = [{"name": m} for m in materials]
        for i, q in enumerate(material_quotes or []):
            data["evidence"][f"materials.{i}"] = check(ev_src, q)
    if scope_note:
        data["scope_note"] = scope_note
    if scope_note_if:
        data["scope_note_if"] = scope_note_if
    if exclude:
        data["exclude"] = exclude
    return data


def main() -> None:
    data = json.loads(ITEMS.read_text(encoding="utf-8"))
    by = {it["id"]: it for it in data["items"]}

    def add(lst, *vals):
        for v in vals:
            if v not in lst:
                lst.append(v)

    add(by["lib-jieyue"].setdefault("aliases", []),
        "自助借还机怎么用", "借书卡刷不出来", "借还机怎么用")
    add(by["xyy-jiuzhen"].setdefault("aliases", []),
        "看病带什么", "看病要带什么", "就诊带什么", "带什么证件")
    add(by["shijian-changguan-yuyue"].setdefault("aliases", []), "演播厅")
    add(by["jwc-zhuanhuan"].setdefault("aliases", []),
        "外校修的学分", "学分转换", "外校学分转换")
    add(by["doc-20260724-c6479a272951"].setdefault("exclude", []),
        "大类招生", "大类", "分流", "选专业")

    it = by["tiyu-changguan-yuyue"]
    it["scope_note"] = ("官方公开的场馆清单里没有羽毛球馆、网球馆和排练厅的预约说明，"
                        "也没有写退订怎么操作；本条只讲可预约的体育场馆以及开放、核销、违约规则")
    it["scope_note_if"] = ["羽毛球", "网球", "排练厅", "排练室", "舞蹈室", "退订", "取消"]

    by["sushe-kongtiao"]["scope_note"] = (
        "官方公开信息只写了宿舍空调免费使用、电费自理；空调租赁和报修没有公开流程，"
        "需要联系学生公寓服务中心")
    by["sushe-kongtiao"]["scope_note_if"] = ["租", "修", "坏", "报修"]

    by["xiyi-liangshai"]["scope_note"] = (
        "官方公开的洗衣说明只写了设备位置和使用方式，没有写每次收费多少")
    by["xiyi-liangshai"]["scope_note_if"] = ["收费", "多少钱", "价格", "费用"]

    by["jwc-buxuanke"]["scope_note"] = (
        "官方公开的选课办法只写了补（退）选的时间窗口和两种例外，"
        "没有写候补、系统卡顿或人数满了怎么处理")
    by["jwc-buxuanke"]["scope_note_if"] = ["候补", "卡顿", "进不去", "系统", "满了", "抢课"]

    by["jwc-zaidu"]["scope_note"] = (
        "官方公开的在读证明办理说明只覆盖出国（境）用途；考研复试、就业等其他用途需要什么，"
        "公开页面没有写")
    by["jwc-zaidu"]["scope_note_if"] = ["考研", "复试", "就业", "实习", "保研"]

    new_items = [
        item(
            "yjs-tiqian-yanqi-biye", "研究生提前毕业与延期毕业",
            ["提前毕业", "提前毕业条件", "研究生提前毕业", "延期毕业", "延期毕业怎么申请",
             "研究生延期毕业", "延毕", "延期手续"],
            ["提前毕业", "延期毕业", "延毕", "延期"],
            [
                ("提前毕业", "提前完成个人培养计划和学位论文、成绩优秀的三年制硕士研究生可申请提前毕业；博士研究生和两年制硕士研究生原则上不得提前毕业",
                 "提前完成个人培养计划和学位论文、成绩优秀的三年制硕士研究生可按规定申请提前毕业。研究生提前毕业应由本人提出申请，经导师和所在培养单位同意，报研究生院审核批准。博士研究生和两年制硕士研究生原则上不得提前毕业。"),
                ("延期申请", "因客观原因未按期完成学业，可在原定毕业日期所在学期提出延期申请；硕士、普博和硕博连读博士延期累计最长两年，直博生最长三年",
                 "硕士研究生、普博生和硕博连读生博士培养阶段延期期限累计最长为两年，直博生延期期限累计最长为三年。研究生延期，应于原定毕业日期所在学期由本人提出申请，经导师和所在培养单位同意，报研究生院审核批准。"),
                ("延期期间", "延期期间学校不拨付培养费，不发给奖学金，也不提供住宿",
                 "延期期间，学校不拨付培养费，不发给奖学金，不提供住宿。"),
                ("离校", "提前毕业、结业或肄业的研究生，须自毕业、结业或肄业之日起一周内办结离校手续",
                 "提前毕业、结业或肄业的研究生，须自毕业、结业或肄业之日起一周内办结离校手续。"),
            ],
            "baa04f656e",
            scope_note="官方公开的提前毕业、延期毕业规定写在研究生学籍管理规定里；本科生提前毕业没有查到公开条件，需要问本科生院",
            location="研究生院",
            location_quote="研究生提前毕业应由本人提出申请，经导师和所在培养单位同意，报研究生院审核批准",
        ),
        item(
            "yjs-xinsheng-baodao", "研究生新生报到（要带什么、请假）",
            ["研究生新生报到", "研究生报到", "研究生新生入学", "研究生入学要带什么",
             "研究生报到带什么"],
            ["研究生新生", "研究生报到", "研究生入学"],
            [
                ("报到携带", "持研究生录取通知书和相关证件、材料（户口、工资关系、组织关系等），按规定日期到校办理入学手续",
                 "应持中国传媒大学研究生录取通知书和相关证件、材料（户口、工资关系、组织关系等），按照规定日期到校办理入学手续"),
                ("请假", "不能按期报到须事先书面请假，请假不超过两周；未请假或逾期未入学的，除不可抗力等正当事由外，视为自动放弃入学资格",
                 "请假时长不得超过两周，未请假或请假逾期未入学者，除因不可抗力等正当事由以外，视为自动放弃入学资格"),
                ("资格初审", "报到时学校初审研究生录取通知书、考生信息等证明材料，合格后办理入学手续、注册学籍",
                 "学校在新生报到时对其入学资格进行初步审查。审查内容包括研究生录取通知书、考生信息等证明材料。"),
            ],
            "baa04f656e",
            materials=["研究生录取通知书", "相关证件、材料（户口、工资关系、组织关系等）"],
            material_quotes=["应持中国传媒大学研究生录取通知书和相关证件、材料",
                             "相关证件、材料（户口、工资关系、组织关系等）"],
            exclude=["本科", "本科生", "本科新生"],
        ),
    ]
    for it in new_items:
        assert it["id"] not in by, f"条目已存在：{it['id']}"
    for s in new_items[1]["steps"]:
        s["where"] = "学校 / 培养单位"
    data["items"].extend(new_items)

    ITEMS.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
    print("新增 2 条、补充别名与适用范围，条目数", len(data["items"]))


if __name__ == "__main__":
    main()