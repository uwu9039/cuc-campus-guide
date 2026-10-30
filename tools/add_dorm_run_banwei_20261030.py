"""补录 2026-10-30 四类缺口：宿舍家具尺寸、冰箱、校园跑、班干部。

只做 upsert / append，不删除任何已有条目。
"""
from __future__ import annotations

import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SRC = ROOT / "sources"


def squash(s: str) -> str:
    return re.sub(r"\s+", "", s or "")


TEXTS: dict[str, str] = {}
for sub in ("wendao-text", "great", "local", "huibian", "crawl", "cdp", "extra", "wechat", "pdf"):
    d = SRC / sub
    if not d.exists():
        continue
    for f in d.glob("*.txt"):
        TEXTS[f.stem] = squash(f.read_text(encoding="utf-8", errors="ignore"))


def step(src: str, what: str, when: str) -> tuple[dict[str, str], dict[str, str]]:
    assert squash(what) in TEXTS.get(src, ""), f"{src} 找不到：{what[:50]}"
    return ({"src": src, "quote": what}, {"when": when, "what": what})


def build(iid: str, title: str, aliases: list[str], keywords: list[str], dept: str,
          steps: list[tuple[str, str, str]], pitfalls: list[tuple[str, str]],
          sources: list[dict[str, str]], confidence: str = "high",
          answer: tuple[str, str] | None = None, note: str | None = None) -> dict:
    ev: dict[str, dict] = {}
    out_steps = []
    for i, (src, what, when) in enumerate(steps):
        ev[f"steps.{i}"] = {"src": src, "quote": what}
        out_steps.append({"when": when, "what": what})
    out_pf = []
    for i, (src, what) in enumerate(pitfalls):
        ev[f"pitfalls.{i}"] = {"src": src, "quote": what}
        out_pf.append(what)
    answer_text = None
    if answer:
        src, what = answer
        assert squash(what) in TEXTS.get(src, ""), f"{iid} answer 找不到"
        ev["answer"] = {"src": src, "quote": what}
        answer_text = what
    item = {
        "id": iid, "title": title, "aliases": aliases, "keywords": keywords,
        "dept": dept, "channel": ["线下"], "audience": ["本科生", "研究生"],
        "status": "verified", "confidence": confidence, "materials": [],
        "steps": out_steps, "fee": None, "location": None, "hours": None,
        "duration": None, "window": None, "pitfalls": out_pf, "contact": None,
        "slots": [], "draft": None, "answer": answer_text, "kind": "service",
        "source": sources, "evidence": ev,
    }
    if note:
        item["note"] = note
    return item


DORM_SRC = {"title": "知识库 · 学生公寓服务中心",
            "url": "https://aihub.cuc.edu.cn/doc/view/fileview?fileId=9bf17365e1e543f38dc410b2a34e0686",
            "checked": "2026-10-30"}
INFO_SRC = {"title": "公寓信息汇总（3部分）.docx",
            "url": "https://aihub.cuc.edu.cn/doc/view/fileview?fileId=d940cbaed1094dd994e4a084d2fa7919",
            "checked": "2026-10-30"}
GUIDE_SRC = {"title": "中国传媒大学新生指南（2026）", "url": "", "checked": "2026-10-30"}
USER_RUN_SRC = {"title": "班级通知（用户提供，2026-10-29）", "url": "", "checked": "2026-10-29"}
BANWEI_SRC = {"title": "中国传媒大学班级学生委员会工作办法（学工教字〔2024〕72号）", "url": "", "checked": "2026-10-30"}
USER_BANWEI_SRC = {"title": "班级岗位设置（用户提供，2026-10-29）", "url": "", "checked": "2026-10-29"}


NEW: list[dict] = [
    build(
        "sushe-jiaju",
        "宿舍家具尺寸（桌子 / 椅子 / 柜子 / 床）",
        ["宿舍桌子规格", "桌子规格", "桌子尺寸", "桌子多大", "桌子长宽", "桌子长宽高",
         "宿舍桌子", "书桌尺寸", "电脑桌尺寸", "宿舍家具尺寸", "家具尺寸",
         "柜子尺寸", "衣柜尺寸", "宿舍柜子多大", "床的尺寸", "宿舍床多大", "床长宽",
         "上下铺怎么分", "宿舍有被子吗", "床上用品", "被子褥子", "床垫", "中蓝桌子",
         "中蓝宿舍一期桌子"],
        ["桌子", "书桌", "电脑桌", "尺寸", "规格", "长宽", "柜子", "衣柜", "储物柜",
         "上下铺", "被子", "褥子", "床垫", "床上用品", "家具", "宿舍床", "单人床"],
        "后勤保障处 学生公寓服务中心",
        [
            ("d940cbae", "桌子尺寸:长85宽55高75，椅子尺寸：长38宽40高80，柜子尺寸:长0.6宽0.5高2米（分2个小柜，2人使用），因家具厂家、生产年份、各楼户型等原因，尺寸略有不同。", "桌子 / 椅子 / 柜子"),
            ("9bf17365", "中蓝宿舍一期桌子长宽是多少？850*550*750 或 650*450*750mm，公寓家 具购置年度且批次不同，具体尺寸也会有不同", "中蓝一期桌子"),
            ("9bf17365", "房间内的双层铁床以 2000`*`900`*`2200的为主，衣柜以 500`*`600`*`2000 的为主，电脑桌 850`*`550`*`750 的为主 。", "床 / 衣柜 / 电脑桌"),
            ("9bf17365", "公寓床铺以双层铁床为主，上铺为单数，下铺为双数（注：梆子井公寓硕士房间 1.3为上铺；2.4.5为下铺）", "上下铺怎么分"),
            ("9bf17365", "宿舍不提供被子褥子等床上用品。", "床上用品"),
            ("9bf17365", "床上用品实行自愿购买原则，包括被子、褥子、床垫、枕芯、被罩、床单、枕套、枕巾、蚊帐、毛巾被（或凉被）10种14件套（被罩、床单、枕套、枕巾为双件），价格为每套 500元左右。", "床上用品怎么买"),
            ("9bf17365", "每个房间按照住宿人数配备对应的床、储物柜、电脑桌、椅子", "房间配置"),
        ],
        [("d940cbae", "因家具厂家、生产年份、各楼户型等原因，尺寸略有不同。"),
         ("9bf17365", "注个别公寓楼房间内的配套设施尺寸有所不同")],
        [INFO_SRC, DORM_SRC],
        note="桌子常规尺寸来自《公寓信息汇总》，中蓝一期与床/衣柜尺寸来自学生公寓服务中心知识库；各楼年份与户型不同，实际会有出入。",
    ),
    build(
        "tiyu-xiaoyuanpao",
        "校园跑（阳光长跑）规则与计分",
        ["校园跑", "阳光长跑", "阳光跑", "闪动校园", "跑步打卡", "校园跑多少次",
         "校园跑满分", "校园跑计分", "跑步算分", "体育课跑步", "乐跑", "校园跑区域",
         "校队抵校园跑", "跑步要求", "校园跑规定", "32次", "20次"],
        ["校园跑", "阳光长跑", "长跑", "闪动校园", "跑步打卡", "打卡", "配速",
         "公里", "32次", "20次", "校队", "代步工具"],
        "体育部 / 本科生院",
        [
            ("loc-新生指南2026-水印版-76f3d8", "中传的阳光长跑在 APP闪动校园 上进行。", "用什么软件"),
            ("user-2026-campus-run", "2026 年起，所有人一学期跑满 32 次为满分；男生每次至少 2.5km，女生每次至少 2km；满分十分，12 次以后开始计分，每次 0.5 分。", "2026 年起次数与计分（班级口径）"),
            ("user-2026-campus-run", "25 年以前为 20 次。", "2025 年及以前"),
            ("loc-新生指南2026-水印版-76f3d8", "目前，一学期需要跑 20 次，男生一次 2.5km，女生一次 2km。", "新生指南口径"),
            ("loc-新生指南2026-水印版-76f3d8", "阳光长跑在体育课里占 10 分，前十次不算分，后十次每次算一分", "计分（新生指南）"),
            ("loc-新生指南2026-水印版-76f3d8", "阳光长跑的开放时间一般会在开学一个半月之后，每天只能跑一次，期末前一个月内结束。", "开放时间"),
            ("loc-新生指南2026-水印版-76f3d8", "阳光长跑必须在规定的区域内进行，超出区域一定时间后就需要重新跑。", "区域要求"),
            ("loc-新生指南2026-水印版-76f3d8", "目前有两个区域，一个是南操，一个是从一教门口到动院南侧的长方形范围。", "两个区域"),
            ("loc-新生指南2026-水印版-76f3d8", "如果加入校队，一般来说可以抵消阳光长跑，需要校队老师出具相关证明或跟体育老师说明。", "校队"),
            ("loc-新生指南2026-水印版-76f3d8", "闪动校园 APP存在违规获取过多用户信息和违规使用用户信息的情况，如果不允许信息获取的话软件会无法运行，所以请注意个人隐私安全。", "隐私提示"),
        ],
        [("loc-新生指南2026-水印版-76f3d8", "学校原则上不允许使用代步工具")],
        [GUIDE_SRC, USER_RUN_SRC],
        confidence="medium",
        note="2026 年起的 32 次 / 12 次后每次 0.5 分来自班级通知（用户提供），官网未检索到同口径文件；软件、区域、开放时间与隐私提示来自新生指南。两者如有冲突，以体育部当学期通知为准。",
    ),
    build(
        "banwei-roles",
        "班干部 / 班委有哪些岗位（含团支部）",
        ["班干部有哪些", "班委有哪些", "班干部种类", "班委岗位", "班干部岗位",
         "团支部委员", "团支部书记", "团支部宣传委", "团支部组织委员", "男班长", "女班长",
         "德育委员", "学习委员", "生活委员", "宣传委员", "美育委员", "体育委员",
         "劳动委员", "心理委员", "安全委员", "就业委员", "竞选班干部", "当班委"],
        ["班干部", "班委", "班长", "团支部", "德育委员", "学习委员", "生活委员",
         "宣传委员", "美育委员", "体育委员", "劳动委员", "心理委员", "安全委员",
         "就业委员", "团员", "竞选"],
        "学生工作部（处）/ 班级",
        [
            ("user-banwei-roles", "班干部种类：男班长、女班长、德育委员、学习委员、生活委员、宣传委员、美育委员、体育委员、劳动委员、心理委员、安全委员、就业委员、团支部书记、团支部宣传委、团支部组织委员（最后三项必须是团员方可报名）", "班级岗位设置（15 类）"),
            ("hbcac8e2b503", "班委会要全面落实以学生党支部为引领、班团一体化联动的工作模式，持续推进落实学生党支部支委会、团支部支委会、班委会的“三委”协同机制。", "班委会与团支部关系"),
            ("hbcac8e2b503", "各岗位可根据实际情况安排兼任，原则上兼任不超过两个岗位。", "兼任限制"),
        ],
        [],
        [BANWEI_SRC, USER_BANWEI_SRC],
        confidence="medium",
        note="班级实际设置的 15 类岗位来自班级通知（用户提供）；学校《班级学生委员会工作办法》（学工教字〔2024〕72号）第八至十八条分设班长、德育委员、学习委员、生活委员、宣传委员、体育委员、美育委员、劳动委员、心理委员、安全委员、就业委员，团支部书记、宣传委员、组织委员属团支部支委会。",
    ),
    build(
        "banwei-xuanju",
        "班委选举、换届与任职积分",
        ["班委怎么选", "班委换届", "班委什么时候换届", "竞选班委", "怎么当班干部",
         "班干部怎么选", "班委任期", "优秀学生干部", "班委加综测吗", "班委劳动积分",
         "临时班委会", "班委述职"],
        ["班委", "班干部", "选举", "换届", "改选", "任期", "劳动积分", "综测",
         "优秀学生干部", "述职", "临时班委会", "班主任"],
        "学生工作部（处）/ 班级",
        [
            ("hbcac8e2b503", "班委会在班主任的指导下成立，班委由班级全体学生选举产生。每届班委会任期为一年，原则上每学年改选一次。除新生外，其余年级均应在每学年第一学期开学后1-3周内进行班委会换届。", "选举与换届"),
            ("hbcac8e2b503", "新生入学时，可由班主任根据学生入学档案和实际表现指定人员组成临时班委会，经学院批准后开展工作。新生入学一个月后，在班主任的指导下，由班级全体学生选举并报请学院批准，产生第一届班委会。", "新生班委会"),
            ("hbcac8e2b503", "各班根据班级人数、任职申请及班级工作具体需要设定班委会职数。各岗位可根据实际情况安排兼任，原则上兼任不超过两个岗位。各班班委会组成后，填写《中国传媒大学班级学生委员会登记表》，及时上报学生工作部（处）备案。", "职数与备案"),
            ("hbcac8e2b503", "担任班委会成员满一年及以上者，思想品德端正，热心服务同学，在班级建设中发挥积极作用，经学院认定，可获得相应劳动积分，相关结果纳入学生综合素质评价。", "任职积分"),
            ("hbcac8e2b503", "班委履职及综合表现优异、为学校做出重要贡献的，经学校相关部门和学院认定，可获得该学年优秀学生干部相关荣誉称号奖励。", "优秀学生干部"),
            ("hbcac8e2b503", "班委会成员如无故缺勤学院及学校的相关培训、会议次数达三分之一及以上的，取消其该学年“优秀学生干部”的评选资格。", "缺勤后果"),
            ("hbcac8e2b503", "班委会应建立工作例会制度，定期进行工作总结，交流班级同学思想、学习、生活等方面的情况，讨论解决班级工作中存在的问题。", "工作例会"),
            ("hbcac8e2b503", "班委会要每学期进行班务公开，特别是班费管理使用情况的公开。", "班务公开"),
            ("hbcac8e2b503", "期满，须向全班同学作工作述职，由班级同学、班主任及辅导员老师共同考核工作任职情况。", "述职考核"),
        ],
        [],
        [BANWEI_SRC],
    ),
]


def main() -> None:
    p = ROOT / "items.json"
    data = json.loads(p.read_text(encoding="utf-8"))
    items = data["items"]
    by = {i["id"]: i for i in items}
    added = updated = 0
    for it in NEW:
        if it["id"] in by:
            old = by[it["id"]]
            for k, v in it.items():
                old[k] = v
            updated += 1
        else:
            items.append(it)
            added += 1

    dq = by["sushe-dianqi"]
    for a in ("冰箱", "电冰箱", "小冰箱", "宿舍冰箱", "冷藏", "冷冻",
              "宿舍能用冰箱吗", "宿舍可以放冰箱吗", "宿舍能放冰箱吗",
              "宿舍能用洗衣机吗", "宿舍可以用洗衣机吗", "宿舍能放洗衣机吗",
              "宿舍能用吹风机吗", "宿舍可以用吹风机吗", "宿舍能用电磁炉吗",
              "宿舍能用电煮锅吗", "宿舍能用大功率电器吗"):
        if a not in dq["aliases"]:
            dq["aliases"].append(a)
    for k in ("冰箱", "电冰箱", "小冰箱", "冷藏", "冷冻", "制冷"):
        if k not in dq["keywords"]:
            dq["keywords"].append(k)
    ban = "禁止使用电吹风、电冰箱、洗衣机、电炉、电热杯、电热褥、电暖器、电磁加热装置、电阻加热装置等电器，若宿舍内存放以上物品，一经发现以使用违章电器论处，予以没收（没收物品交由相关部门处理），并按照相关规定处理。"
    assert squash(ban) in TEXTS["9bf17365"]
    if not dq.get("answer"):
        dq["answer"] = ban
        dq["evidence"]["answer"] = {"src": "9bf17365", "quote": ban}
        updated += 1

    data["updated"] = "2026-10-30"
    p.write_text(json.dumps(data, ensure_ascii=False, indent=1), encoding="utf-8")
    print(f"新增 {added} 条，更新 {updated} 条，总计 {len(items)} 条")


if __name__ == "__main__":
    main()
