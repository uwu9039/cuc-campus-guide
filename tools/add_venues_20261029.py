"""补两条手工条目：游泳馆开放与收费、校医院门急诊时间。

来源都是问道原文：
  sources/wendao-text/513edd5d.txt  游泳馆相关事项
  sources/wendao-text/f6e9cd2f.txt  校医院门急诊时间

引文用 seg() 从原文里截，避免手抄出错。
"""
from __future__ import annotations

import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
ITEMS = ROOT / "items.json"
SWIM_SRC = "513edd5d"
HOSP_SRC = "f6e9cd2f"


def read_src(slug: str) -> str:
    raw = (ROOT / "sources" / "wendao-text" / f"{slug}.txt").read_text(encoding="utf-8")
    return raw.replace("\xa0", " ")


def seg(text: str, start: str, end: str) -> str:
    i = text.index(start)
    j = text.index(end, i) + len(end)
    return text[i:j]


def q(src: str, quote: str) -> dict:
    return {"src": src, "quote": quote}


def main() -> None:
    swim = read_src(SWIM_SRC)
    hosp = read_src(HOSP_SRC)

    swim_intro = seg(swim, "场馆介绍", "标准泳池。")
    swim_hours = seg(swim, "场馆开放周期：", "21:30。")
    swim_fee = seg(swim, "游泳馆的收费标准?", "（以上所有卡类型都是限时两小时）")
    swim_student = seg(swim, "学校游泳馆学生如何办卡？学生培训如何收费？", "是传媒大学在校生）")
    swim_book = seg(swim, "游泳馆需要预约吗？如何预约？", "预约的时间是取手环的时间。")
    swim_deep = seg(swim, "什么时候可以考深水证？", "延长半小时游泳时间。")
    swim_staff = seg(swim, "教工办卡有啥要求？", "40 元/2 时。")
    swim_need = seg(swim, "什么条件下需要深水证？", "度）。")
    swim_phone = "如有其他问题，可以咨询游泳馆前台，电话：65783365。"

    hosp_fee = seg(hosp, "医事服务费", "急   诊      40 元（公费医疗及医保报销39 元）")
    hosp_out = seg(hosp, "门诊时间\n周一至周五上午", "周五下午：13：30 ～ 16：20")
    hosp_emg = seg(hosp, "急诊时间", "其余门诊时间之外均为急诊，医生24 小时候诊。")
    hosp_hol = seg(hosp, "节假日挂号、药房、注射室值班时间", "下午： 13：30 ～ 16：00")
    hosp_note = seg(hosp, "注：", "夜间急诊只处理各种急症。")
    hosp_dental = "口腔疾病表直接到二楼口腔科挂号收费室挂号收费"

    swim_item = {
        "id": "tiyu-yongyongguan",
        "title": "游泳馆开放时间与收费",
        "aliases": [
            "游泳馆", "游泳馆开放时间", "游泳馆几点开门", "游泳馆几点关门",
            "游泳馆的开放时间", "游泳馆收费", "游泳馆的收费标准", "游泳馆多少钱",
            "游泳馆怎么收费", "游泳多少钱一次", "游泳馆单次票", "游泳卡",
            "学生游泳卡", "教工游泳卡", "游泳馆怎么办卡", "游泳培训",
            "游泳馆预约", "游泳馆需要预约吗", "深水证", "怎么办深水证",
            "深水证怎么考", "游泳馆电话", "游泳馆在哪", "游泳馆位置",
        ],
        "keywords": ["游泳馆", "游泳", "深水证", "泳道", "单次票"],
        "dept": "中国传媒大学（游泳馆）",
        "channel": ["线下"],
        "audience": ["本科生", "研究生", "教职工"],
        "status": "verified",
        "confidence": "high",
        "materials": [],
        "steps": [
            {"when": "淡季", "what": "9 月 1 日—次年 6 月 30 日（淡季）：周一至周五 12:00-13:00、16:00-21:00，周六、日 12:00-21:00；最晚入场 20:00，起水 20:30，清场 21:00。", "where": "游泳馆"},
            {"when": "旺季", "what": "7 月 1 日—8 月 31 日（旺季）：10:30-21:30；最晚入场 20:30，起水 21:00，清场 21:30。", "where": "游泳馆"},
            {"when": "购票", "what": "单次票 60 元（限时两小时）；A 卡 10 次 510 元（6 个月有效期）、B 卡 30 次 1320 元（一年有效期）、D 卡 50 次 2100 元（一年有效期），以上所有卡类型都是限时两小时。", "where": "游泳馆前台"},
            {"when": "学生办卡与培训", "what": "学生本人带学生卡（或电子学生证）在前台办理 260 元/20 次，只限本人使用，禁止外借，一经发现立即停卡；培训：一对一 1760 元/人（8 节课，有效期 120 天）、一对二 1280 元/人（8 节课，有效期 120 天）、蛙泳/自由泳 960 元/人（8 节课，有效期 120 天，四人开班需同样是传媒大学在校生）。", "where": "游泳馆前台"},
            {"when": "预约", "what": "单次票不需要预约；办理计次卡的需预约：微信关注水立方游泳俱乐部服务号——左下角快捷入馆——游泳预约——预约到馆（传媒大学游泳馆），预约的时间是取手环的时间。", "where": "线上"},
            {"when": "深水证", "what": "营业时间均可考深水证，带一张 1 寸纸质照片（底色无要求），在游泳馆考，前台电话 65783365；考核两项：双手和头露出水面原地踩水 30 秒，200 米连续游（不得仰泳、不得以任何理由停歇，不得扒池壁及水线停留）；未通过不得在深水区逗留，测试费用不退；参加深水证考核延长半小时游泳时间。", "where": "游泳馆"},
            {"when": "教工办卡", "what": "教工卡 750 元/30 次（只能绑定两名直系亲属，30 次未使用完不可更换绑定人员）；中午场（寒暑假无中午场）单次票 30 元/时，其他开放时间票 40 元/2 时。", "where": "游泳馆前台"},
            {"when": "场馆条件", "what": "游泳馆位于中国传媒大学校内，建筑面积 2576 平方米，内含 50 米 8 泳道标准泳池；池水消毒以臭氧为主、氯制剂辅助；室温、池岸温度常年保持 22℃~26℃，水温常年保持 28℃±1℃。", "where": "游泳馆"},
        ],
        "fee": "单次票 60 元（限时两小时）；学生卡 260 元/20 次；A 卡 510 元/10 次（6 个月）；B 卡 1320 元/30 次（一年）；D 卡 2100 元/50 次（一年）；教工卡 750 元/30 次",
        "location": "中国传媒大学校内",
        "hours": "淡季（9 月 1 日—次年 6 月 30 日）周一至周五 12:00-13:00、16:00-21:00，周六日 12:00-21:00；旺季（7 月 1 日—8 月 31 日）10:30-21:30",
        "duration": None,
        "window": None,
        "pitfalls": [
            "学生卡只限本人使用，禁止外借，一经发现，立即停卡。",
            "涉及深水区游泳的，需要深水合格证（北方场馆深水区安全管理制度）。",
            "深水考核未通过不得在深水区逗留，并且测试费用不会退还。",
        ],
        "contact": "65783365（游泳馆前台）",
        "slots": [],
        "draft": None,
        "answer": None,
        "kind": "service",
        "source": [
            {
                "title": "游泳馆相关事项",
                "url": "https://aihub.cuc.edu.cn/doc/view/fileview?fileId=513edd5dccba4238a4885d123ddfd866",
                "checked": "2026-10-29",
            }
        ],
        "evidence": {
            "steps.0": q(SWIM_SRC, swim_hours),
            "steps.1": q(SWIM_SRC, swim_hours),
            "steps.2": q(SWIM_SRC, swim_fee),
            "steps.3": q(SWIM_SRC, swim_student),
            "steps.4": q(SWIM_SRC, swim_book),
            "steps.5": q(SWIM_SRC, swim_deep),
            "steps.6": q(SWIM_SRC, swim_staff),
            "steps.7": q(SWIM_SRC, swim_intro),
            "fee": {"sources": [q(SWIM_SRC, swim_fee), q(SWIM_SRC, swim_student), q(SWIM_SRC, swim_staff)]},
            "location": q(SWIM_SRC, swim_intro),
            "hours": {"sources": [q(SWIM_SRC, swim_hours)]},
            "contact": q(SWIM_SRC, swim_phone),
            "pitfalls.0": q(SWIM_SRC, swim_student),
            "pitfalls.1": q(SWIM_SRC, swim_need),
            "pitfalls.2": q(SWIM_SRC, swim_deep),
        },
    }

    hosp_item = {
        "id": "xyy-menzhen-shijian",
        "title": "校医院门急诊时间与医事服务费",
        "aliases": [
            "校医院门诊时间", "校医院的门诊时间", "校医院几点开门", "校医院几点上班",
            "校医院急诊时间", "校医院急诊", "校医院中午开门吗", "校医院周四下午",
            "周末能看病吗", "周末校医院开门吗", "校医院挂号费", "校医院医事服务费",
            "校医院看病多少钱", "校医院口腔科", "校医院什么时候开",
        ],
        "keywords": ["校医院", "门诊时间", "急诊时间", "医事服务费", "挂号费"],
        "dept": "校医院",
        "channel": ["线下"],
        "audience": ["本科生", "研究生", "教职工"],
        "status": "verified",
        "confidence": "high",
        "materials": [],
        "steps": [
            {"when": "门诊", "what": "门诊：周一至周五上午 8:00～11:30；周一至周三下午、周五下午 13:30～16:20。", "where": "校医院"},
            {"when": "急诊", "what": "急诊：周一至周五中午 11:30～13:30；周一至周三下午、周五下午 16:20～18:00；周四全下午（因业务学习）；其余门诊时间之外均为急诊，医生 24 小时候诊。", "where": "校医院"},
            {"when": "节假日", "what": "节假日挂号、药房、注射室值班：上午 8:00～11:30，下午 13:30～16:00。", "where": "校医院"},
            {"when": "挂号", "what": "门诊下班前 5 分钟停止挂号，开始挂急诊号；平日门诊挂号、药房、注射室 8:00～18:00 均有值班；夜间急诊只处理各种急症。", "where": "校医院"},
            {"when": "口腔", "what": "口腔疾病直接到二楼口腔科挂号收费室挂号收费。", "where": "校医院二楼口腔科"},
        ],
        "fee": "普通门诊 20 元（公费医疗及医保报销 19 元）；副主任医师 40 元（报销 20 元）；主任医师 60 元（报销 20 元）；急诊 40 元（报销 39 元）",
        "location": "校医院",
        "hours": "门诊：周一至周五 8:00～11:30；周一至周三、周五 13:30～16:20；其余时间急诊，医生 24 小时候诊",
        "duration": None,
        "window": None,
        "pitfalls": [
            "周四全下午因业务学习，门诊停诊，按急诊处理。",
            "门诊下班前 5 分钟停止挂号，开始挂急诊号。",
            "夜间急诊只处理各种急症。",
            "口腔疾病直接到二楼口腔科挂号收费室挂号收费。",
        ],
        "contact": None,
        "slots": [],
        "draft": None,
        "answer": None,
        "kind": "service",
        "source": [
            {
                "title": "校医院门急诊时间",
                "url": "https://xyy.cuc.edu.cn/",
                "checked": "2026-10-29",
            }
        ],
        "evidence": {
            "steps.0": q(HOSP_SRC, hosp_out),
            "steps.1": q(HOSP_SRC, hosp_emg),
            "steps.2": q(HOSP_SRC, hosp_hol),
            "steps.3": q(HOSP_SRC, hosp_note),
            "steps.4": q(HOSP_SRC, hosp_dental),
            "fee": q(HOSP_SRC, hosp_fee),
            "location": q(HOSP_SRC, "校医院门急诊时间"),
            "hours": {"sources": [q(HOSP_SRC, hosp_out), q(HOSP_SRC, hosp_emg)]},
            "pitfalls.0": q(HOSP_SRC, hosp_emg),
            "pitfalls.1": q(HOSP_SRC, hosp_note),
            "pitfalls.2": q(HOSP_SRC, hosp_note),
            "pitfalls.3": q(HOSP_SRC, hosp_dental),
        },
    }

    data = json.loads(ITEMS.read_text(encoding="utf-8"))
    items = data["items"]
    by_id = {i["id"]: i for i in items}
    if "tiyu-yongyongguan" in by_id and "xyy-menzhen-shijian" in by_id:
        print("已存在，跳过")
        return

    backup = ITEMS.with_suffix(".json.bak-before-venues")
    if not backup.exists():
        backup.write_text(ITEMS.read_text(encoding="utf-8"), encoding="utf-8")

    def insert_after(after_id: str, item: dict) -> None:
        pos = next((n for n, i in enumerate(items) if i["id"] == after_id), len(items) - 1)
        items.insert(pos + 1, item)

    if "xyy-menzhen-shijian" not in by_id:
        insert_after("xyy-jiuzhen", hosp_item)
    if "tiyu-yongyongguan" not in by_id:
        insert_after("campus-changguan-weizhi", swim_item)
    ITEMS.write_text(json.dumps(data, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")

    # 自检：每条引文都必须是原文（去空白后）的子串
    def squash(s: str) -> str:
        return re.sub(r"\s+", "", s)

    texts = {SWIM_SRC: squash(swim), HOSP_SRC: squash(hosp)}
    for it in (swim_item, hosp_item):
        for key, ev in it["evidence"].items():
            for one in (ev.get("sources") if "sources" in ev else [ev]):
                assert squash(one["quote"]) in texts[one["src"]], f"{it['id']} {key} 引文不在原文里"
    print("已写入", len(items), "条；引文自检通过")


if __name__ == "__main__":
    main()
