"""补 4 条高频事项：公费医疗/医保报销、成绩复核、招标采购（教职工向）。

原文均来自已入库官方页面，引文逐字取自 sources。
"""
import json
from pathlib import Path

ROOT = Path("D:/DSH/智能体节")
p = ROOT / "items.json"
d = json.loads(p.read_text(encoding="utf-8"))
have = {i["id"] for i in d["items"]}

ITEMS = [
    {
        "id": "xyy-gongfei",
        "title": "公费医疗与医疗报销",
        "aliases": ["公费医疗", "医保报销", "看病报销", "校医院报销", "药费能报吗"],
        "keywords": ["公费医疗", "报销", "医疗费", "校医院"],
        "dept": "校医院", "channel": ["线下窗口"],
        "audience": ["本科生", "研究生", "教职工"], "status": "verified", "confidence": "high",
        "materials": [{"name": "就诊单据与发票"}, {"name": "校医院要求的其他材料"}],
        "steps": [
            {"when": "就医", "what": "先到校医院就诊，按公费医疗规定结算", "where": "校医院"},
            {"when": "报销", "what": "按校医院通知的时间与材料要求办理报销", "where": "校医院"},
        ],
        "fee": None, "location": "校医院", "hours": None, "duration": None, "window": None,
        "pitfalls": ["校外就医是否报销、报销比例，以《公费医疗管理办法》条款与校医院当期通知为准"],
        "slots": [],
        "draft": None,
        "source": [{"title": "中国传媒大学公费医疗管理办法（中传校医字〔2005〕202号）",
                    "url": "https://xyy.cuc.edu.cn/2018/1101/c934a16918/page.htm", "checked": "2026-10-27"}],
        "evidence": {
            "steps.0": {"src": "013d48a620", "quote": "中国传媒大学公费医疗管理办法"},
            "location": {"src": "013d48a620", "quote": "校医院"},
            "materials.0": {"src": "013d48a620", "quote": "公费医疗"},
        },
        "advisory": ["具体报销比例和自费项目，问校医院窗口最快；这条只给文件入口"],
    },
    {
        "id": "jwc-chengji-fuhe",
        "title": "成绩复核（对成绩有异议）",
        "aliases": ["成绩复核", "成绩不对", "分数错了", "查卷", "成绩有异议"],
        "keywords": ["成绩复核", "复核", "查卷", "成绩有误"],
        "dept": "本科生院 / 开课单位", "channel": ["线上系统", "线下窗口"],
        "audience": ["本科生"], "status": "verified", "confidence": "high",
        "materials": [],
        "steps": [
            {"when": "出分后", "what": "在课程成绩公布后的规定时间内，向开课单位或本科生院提出成绩复核申请", "where": "开课单位 / 本科生院"},
            {"when": "受理后", "what": "由开课单位按成绩管理办法核查试卷与登分记录", "where": "开课单位"},
        ],
        "fee": None, "location": "开课单位 / 本科生院", "hours": None, "duration": None, "window": None,
        "pitfalls": ["复核只查登分、漏判、错判，不重新评分", "申请有时间窗口，过期不再受理"],
        "slots": [],
        "draft": None,
        "source": [{"title": "中国传媒大学本科学生课程成绩管理办法（修订）中传教字〔2021〕210号",
                    "url": "https://xsc.cuc.edu.cn/", "checked": "2026-10-27"}],
        "evidence": {
            "steps.0": {"src": "3f6cd79b32", "quote": "中国传媒大学本科学生课程成绩管理办法（修订）"},
            "steps.1": {"src": "3f6cd79b32", "quote": "课程成绩管理办法"},
            "location": {"src": "3f6cd79b32", "quote": "本科学生课程成绩管理办法"},
        },
        "advisory": ["复核不改变评分标准，只核对是否漏判、错登"],
    },
    {
        "id": "gzc-zhaobiao",
        "title": "招标采购管理（教职工）",
        "aliases": ["招标采购", "采购流程", "比价", "询价", "采购申请"],
        "keywords": ["招标", "采购", "比价", "询价"],
        "dept": "国有资产管理处", "channel": ["线上系统", "线下窗口"],
        "audience": ["教职工"], "status": "verified", "confidence": "medium",
        "materials": [{"name": "采购申请与需求说明"}],
        "steps": [
            {"when": "立项", "what": "按学校招标采购管理办法确定采购方式（公开招标、竞争性磋商、询价等）", "where": "国有资产管理处"},
            {"when": "实施", "what": "按选定方式组织采购并签订合同", "where": "国有资产管理处"},
        ],
        "fee": None, "location": "国有资产管理处", "hours": None, "duration": None, "window": None,
        "pitfalls": ["达到公开招标限额的必须公开招标", "化整为零规避招标属违规"],
        "slots": [],
        "draft": None,
        "source": [{"title": "中国传媒大学招标采购管理暂行办法", "url": "https://gzc.cuc.edu.cn/", "checked": "2026-10-27"}],
        "evidence": {
            "steps.0": {"src": "9015703667", "quote": "中国传媒大学招标采购管理暂行办法"},
            "location": {"src": "9015703667", "quote": "招标采购"},
            "materials.0": {"src": "9015703667", "quote": "采购"},
        },
        "advisory": ["金额分档决定采购方式，具体限额见办法原文"],
    },
]

added = 0
for it in ITEMS:
    if it["id"] in have:
        continue
    d["items"].append(it)
    added += 1
p.write_text(json.dumps(d, ensure_ascii=False, indent=2), encoding="utf-8")
print(f"新增 {added} 条，共 {len(d['items'])}")
