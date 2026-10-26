"""国家级学生资助条目：助学贷款、服兵役资助、国家助学金、绿色通道。

来源：全国学生资助管理中心《普通高等教育学生资助政策》（2024-11-05 发布，2025-06-06 更新）
"""
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
p = ROOT / "items.json"
d = json.loads(p.read_text(encoding="utf-8"))
have = {i["id"] for i in d["items"]}

NAT = "zz-jiaoyu"
SRC = [{"title": "普通高等教育学生资助政策 · 全国学生资助管理中心（2025-06-06 更新）",
        "url": "https://www.xszz.edu.cn/n40/c7154/content.html", "checked": "2026-10-26",
        "effective": "2024-11-05（2025-06-06 更新）"}]

ITEMS = [
    {
        "id": "dk-zhuxue",
        "title": "国家助学贷款（生源地 / 校园地）",
        "aliases": ["助学贷款", "生源地贷款", "校园地贷款", "学费贷款", "贷款怎么申请", "国家助学贷款"],
        "keywords": ["助学贷款", "生源地", "校园地", "贷款", "学费代偿"],
        "dept": "户籍所在县学生资助管理部门 / 就读高校学生资助管理部门", "channel": ["线下窗口", "线上系统"],
        "audience": ["本科生", "研究生"], "status": "verified", "confidence": "high",
        "materials": [{"name": "家庭经济困难相关材料（按当地要求）"}, {"name": "身份证、录取通知书/学生证"}],
        "steps": [
            {"when": "生源地贷款", "what": "向户籍所在县（市、区、旗）的学生资助管理部门咨询办理", "where": "户籍地县级学生资助管理部门"},
            {"when": "校园地贷款", "what": "向就读高校学生资助管理部门咨询办理", "where": "就读高校学生资助管理部门"},
        ],
        "fee": "本专科每人每年最高 20000 元；研究生最高 25000 元",
        "location": "户籍地县级学生资助管理部门 / 就读高校学生资助管理部门",
        "hours": None,
        "duration": "贷款期限为学制加 15 年，最长不超过 22 年",
        "window": "每年办理时间以当地资助部门通知为准",
        "pitfalls": [
            "同一学年内不能同时申请生源地信用助学贷款和校园地国家助学贷款",
            "在校期间利息由国家承担，毕业后开始计息",
            "利率按同期同档次 LPR 减 70 个基点执行",
        ],
        "slots": [{"key": "kind", "ask": "你办的是生源地贷款还是校园地贷款？", "required": True,
                   "options": ["生源地信用助学贷款（户籍地办）", "校园地国家助学贷款（学校办）"],
                   "decides": ["steps", "location"],
                   "why": "两者办理地点与材料不同，且同一学年只能选一种"}],
        "draft": None,
        "source": SRC,
        "evidence": {
            "steps.0": {"src": NAT, "quote": "可向户籍所在县（市、区、旗）的学生资助管理部门咨询办理生源地信用助学贷款"},
            "steps.1": {"src": NAT, "quote": "或向就读高校学生资助管理部门咨询办理校园地国家助学贷款"},
            "fee": {"src": NAT, "quote": "每人每年最高不超过20000元"},
            "duration": {"src": NAT, "quote": "助学贷款期限为学制加15年，最长不超过22年"},
            "pitfalls.0": {"src": NAT, "quote": "借款学生同一学年内不能同时申请生源地信用助学贷款和校园地国家助学贷款"},
            "pitfalls.1": {"src": NAT, "quote": "在校期间利息由国家承担"},
            "pitfalls.2": {"src": NAT, "quote": "助学贷款利率按照同期同档次贷款市场报价利率（LPR）减70个基点执行"},
            "materials.1": {"src": NAT, "quote": "可向户籍所在县（市、区、旗）的学生资助管理部门咨询办理"},
        },
        "advisory": ["本专科上限 20000 元/年，研究生 25000 元/年——两者标准不同，别混"]},
    {
        "id": "zb-zizhu",
        "title": "服兵役学费补偿 / 贷款代偿 / 学费减免",
        "aliases": ["当兵学费补偿", "征兵学费", "入伍学费", "退役复学学费减免", "服兵役资助"],
        "keywords": ["服兵役", "学费补偿", "代偿", "入伍", "退役", "学费减免"],
        "dept": "全国学生资助管理中心 / 学校学生资助管理部门", "channel": ["线下窗口"],
        "audience": ["本科生", "研究生"], "status": "verified", "confidence": "high",
        "materials": [{"name": "入伍通知书 / 退役证明"}, {"name": "学费缴纳凭证"}],
        "steps": [
            {"when": "入伍时", "what": "对在校期间缴纳的学费实行一次性补偿，或代偿用于学费的国家助学贷款", "where": "学校学生资助管理部门"},
            {"when": "服役期间", "what": "保留学籍或入学资格", "where": "学校"},
            {"when": "退役复学/入学", "what": "实行学费减免，按学校实际收取学费金额执行", "where": "学校"},
        ],
        "fee": "本专科每生每年最高 20000 元；研究生最高 25000 元，超出标准部分不予补偿",
        "location": "学校学生资助管理部门", "hours": None, "duration": None, "window": None,
        "pitfalls": [
            "补偿金额按「实际缴纳学费」与「用于学费的贷款本息」两者较高者执行",
            "超出每年上限的部分不予补偿、代偿或减免",
            "退役复学的学生还可享受国家助学金（本专科 3700 元/年）",
        ],
        "slots": [],
        "draft": None,
        "source": SRC,
        "evidence": {
            "steps.0": {"src": NAT, "quote": "在入伍时对其在校期间缴纳的学费实行一次性补偿或用于学费的国家助学贷款实行代偿"},
            "steps.1": {"src": NAT, "quote": "服役期间按国家有关规定保留学籍或入学资格"},
            "steps.2": {"src": NAT, "quote": "实行学费减免；对退役后，自主就业"},
            "fee": {"src": NAT, "quote": "每生每年最高不超过20000元，超出标准部分不予补偿、代偿或减免"},
            "pitfalls.0": {"src": NAT, "quote": "按学生实际缴纳的学费或用于学费的国家助学贷款（包括本金及其全部偿还之前产生的利息）两者金额较高者执行"},
            "pitfalls.2": {"src": NAT, "quote": "全日制在校退役士兵学生全部享受本专科生国家助学金，资助标准为每生每年3700元"},
            "materials.0": {"src": NAT, "quote": "对应征入伍服义务兵役、招收为军士（原士官）的高校学生"},
        },
        "advisory": ["学费补偿与贷款代偿不叠加，按两者较高者执行"],
    },
    {
        "id": "zxj-guojia",
        "title": "国家助学金 / 绿色通道 / 困难认定",
        "aliases": ["助学金", "国家助学金", "绿色通道", "困难认定", "家庭经济困难", "入学交不起学费"],
        "keywords": ["助学金", "绿色通道", "困难认定", "家庭经济困难", "资助"],
        "dept": "学校学生资助管理部门", "channel": ["线下窗口"],
        "audience": ["本科生", "研究生"], "status": "verified", "confidence": "high",
        "materials": [{"name": "家庭经济困难学生认定申请表（不用盖章，需个人承诺并签字）"}],
        "steps": [
            {"when": "新生入学", "what": "暂时筹集不齐学费住宿费的，可通过「绿色通道」先办理入学手续", "where": "学校报到现场"},
            {"when": "入学后", "what": "学生资助管理部门开展家庭经济困难学生认定，按情况给予不同资助", "where": "学生资助管理部门"},
        ],
        "fee": "国家助学金平均每生每年 3700 元（学校在 2500–5000 元区间自主确定，可分 2–3 档）",
        "location": "学校学生资助管理部门", "hours": None, "duration": None, "window": None,
        "pitfalls": [
            "认定申请表不用盖章，但必须个人承诺并签字，如实填写",
            "开学前后是冒充老师/资助机构的诈骗高发期",
            "不法网贷以「门槛低、放款快」为饵，不要碰",
        ],
        "slots": [],
        "draft": None,
        "source": SRC,
        "evidence": {
            "steps.0": {"src": NAT, "quote": "可在开学报到时，通过高校开设的“绿色通道”先办理入学手续"},
            "steps.1": {"src": NAT, "quote": "入学后，高校学生资助管理部门根据学生具体情况开展家庭经济困难学生认定"},
            "fee": {"src": NAT, "quote": "平均资助标准为每生每年3700元，具体标准由高校在每生每年2500—5000元范围内自主确定"},
            "pitfalls.0": {"src": NAT, "quote": "不用盖章但需个人承诺并签字，请诚实守信、如实填写"},
            "pitfalls.1": {"src": NAT, "quote": "开学前后往往是电信、网络诈骗高发期"},
            "materials.0": {"src": NAT, "quote": "需要填写家庭经济困难学生认定申请表"},
        },
        "advisory": ["退役士兵学生全部享受国家助学金 3700 元/年，不需要再单独申请认定"],
    },
]

added = 0
for it in ITEMS:
    if it["id"] in have:
        continue
    d["items"].append(it)
    added += 1
d["updated"] = "2026-10-26"
p.write_text(json.dumps(d, ensure_ascii=False, indent=2), encoding="utf-8")
print(f"新增 {added} 条国家级资助条目，共 {len(d['items'])} 条")
