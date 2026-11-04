"""新增「跨专业选课」条目 + 给新生户口条目补来源链接与一句话结论。

只做追加：不删除任何条目，不改任何条目的 keywords/require/aliases 之外的路由字段
（新条目本身要有关键词才能被检索到）。
用法：./.venv/Scripts/python.exe tools/add_kuazhuan业_20261103.py
"""
from __future__ import annotations

import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
ITEMS = ROOT / "items.json"
CHECKED = "2026-11-03"

SRC_TEXT = {
    "d02e30b4": "sources/wendao-text/d02e30b4.txt",
    "aa226cf5": "sources/wendao-text/aa226cf5.txt",
    "7691069e": "sources/wendao-text/7691069e.txt",
    "hb89efe99078": "sources/huibian/hb89efe99078.txt",
    "att-1aee84ebfe": "sources/attachments/text/att-1aee84ebfe.txt",
    "20190802-c2753a133698": "sources/cdp/20190802-c2753a133698.txt",
    "loc-2026级本科生入学须知-校本部-2cdd30": "sources/local/loc-2026级本科生入学须知-校本部-2cdd30.txt",
}
SQ = lambda s: re.sub(r"\s+", "", s or "")
TEXTS = {k: SQ((ROOT / v).read_text(encoding="utf-8", errors="ignore")) for k, v in SRC_TEXT.items()}


def ev(src: str, quote: str) -> dict:
    assert src in TEXTS, src
    assert SQ(quote) in TEXTS[src], f"原文找不到：{src} {quote[:30]}"
    return {"src": src, "quote": quote}


def multi(*pairs: tuple[str, str]) -> dict:
    return {"sources": [ev(s, q) for s, q in pairs]}


XUANKE = {
    "id": "xuanke-kuazhuanye",
    "title": "跨专业选课（选其他专业开设的课）",
    "kind": "rule",
    "dept": "本科生院",
    "channel": ["线上系统"],
    "audience": ["本科生", "研究生"],
    "status": "verified",
    "confidence": "high",
    "answer": (
        "可以。本科生每学期在教务综合管理系统自行选课，学校随选课通知公布"
        "《开设跨专业选课课程信息表》，表里写明课程、任课教师、跨专业课容量和面向年级；"
        "这类跨专业选修课所获学分可以认定为通识教育拓展课程（公共选修课）学分。"
        "研究生按个人培养计划选课，选校外课程要先经导师和所在培养单位同意并报研究生院备案。"
    ),
    "materials": [],
    "location": "教务综合管理系统",
    "fee": None,
    "hours": None,
    "duration": None,
    "window": None,
    "contact": None,
    "slots": [],
    "draft": None,
    "keywords": ["跨专业", "跨专业选课", "跨学院选课", "跨专业选修课", "外专业课", "通识拓展"],
    "aliases": ["跨专业选课", "跨专业选修课", "跨学院选课", "选其他专业的课", "选外专业的课", "跨专业选课可以吗"],
    "steps": [
        {"when": "本科生能不能选",
         "what": "本科课程分必修课和选修课，选修课按专业培养方案要求、学业发展需求和个人兴趣选择，须在规定学习期限内修满规定学分"},
        {"when": "有哪些课可选",
         "what": "学校随选课通知公布《中国传媒大学开设跨专业选课课程信息表》，表内有开课单位、课程号、课程名、任课教师、跨专业课容量、面向跨专业学生的年级和其他限制条件"},
        {"when": "学分怎么算",
         "what": "跨专业选修课程所获学分可以认定为通识教育拓展课程（公共选修课）学分；执行 2022 级培养方案的学生认定为通识拓展课组学分"},
        {"when": "什么时候选",
         "what": "本科生从第二学期开始选修通识教育核心课程和通识教育拓展课程，在每学期规定时间内自行登录教务综合管理系统选课"},
        {"when": "选完能不能改",
         "what": "每学期教学周第一周集中补退选课，由学生本人在选课系统自行操作完成"},
        {"when": "研究生",
         "what": "研究生按所在学科的培养要求制定个人培养计划，在每学期开学初正式办理选课手续；未正式办理手续而旁听的课程，不得参加考核"},
        {"when": "研究生选校外课程",
         "what": "研究生选修国内其他高校研究生课程，须经导师和所在培养单位同意，报研究生院审核备案，并办理有关手续"},
    ],
    "pitfalls": [
        "跨专业课容量有限，信息表如有改动以选课界面显示信息为准",
        "通识选修课选定后，课程成绩无论是否及格均不予删除",
        "2024 版研究生学籍管理规定没有单列校内跨学院跨专业选课条款，只要求按个人培养计划办理选课手续；跨学院选课先问导师和培养单位",
    ],
    "source": [
        {"title": "中国传媒大学通识教育核心课程、通识教育拓展课程选课办法（试行）",
         "url": "https://aihub.cuc.edu.cn/doc/view/fileview?fileId=d02e30b4de6b4d81a39bc7bca1a922e7",
         "checked": CHECKED},
        {"title": "关于印发《中国传媒大学本科生选课管理办法》的通知",
         "url": "https://aihub.cuc.edu.cn/doc/view/fileview?fileId=aa226cf53b80489faacceaccd940d426",
         "checked": CHECKED},
        {"title": "中传研字〔2024〕159号 中国传媒大学研究生学籍管理规定",
         "url": "https://aihub.cuc.edu.cn/doc/view/fileview?fileId=7691069ec5494dcd92a1b2d205c9249a",
         "checked": CHECKED},
        {"title": "关于开展2026—2027学年秋季学期学生主修、辅修网上选课工作的通知 · 附件3 跨专业选课课程信息表",
         "url": "https://jwc.cuc.edu.cn/_upload/article/files/fb/49/5ae8574b4aa5bd0a687321f97333/5434e356-6aaa-4fe2-bd72-249a85163844.rar",
         "checked": CHECKED},
    ],
    "evidence": {
        "answer": multi(
            ("att-1aee84ebfe", "附件3 中国传媒大学开设跨专业选课课程信息表"),
            ("d02e30b4", "（1）跨专业选修课程"),
            ("d02e30b4", "学生在每学期规定时间内自行登录我校教务综合管理系统选课"),
            ("7691069e", "研究生应按所在学科的培养要求，制定个人培养计划，在每学期开学初正式办理选课手续"),
        ),
        "location": ev("d02e30b4", "学生在每学期规定时间内自行登录我校教务综合管理系统选课"),
        "steps.0": ev("aa226cf5", "选修课是根据专业培养方案要求、学业发展需求和个人兴趣可选择学习的课程"),
        "steps.1": multi(
            ("att-1aee84ebfe", "附件3 中国传媒大学开设跨专业选课课程信息表"),
            ("att-1aee84ebfe", "面向跨专业学生年级"),
        ),
        "steps.2": multi(
            ("d02e30b4", "（1）跨专业选修课程"),
            ("hb89efe99078", "（一）跨专业选修课程"),
            ("hb89efe99078", "学生修读以下课程所获学分可以认定为通识拓展课组学分"),
        ),
        "steps.3": ev("d02e30b4", "本科生从第二学期开始选修通识教育核心课程和通识教育拓展课程"),
        "steps.4": ev("aa226cf5", "集中补退选课由学生本人在选课系统自行操作完成"),
        "steps.5": multi(
            ("7691069e", "研究生应按所在学科的培养要求，制定个人培养计划，在每学期开学初正式办理选课手续"),
            ("7691069e", "未正式办理手续而旁听的课程，不得参加考核"),
        ),
        "steps.6": ev("7691069e", "研究生选修国内其他高校研究生课程，须经导师和所在培养单位同意，报研究生院审核备案"),
        "pitfalls.0": ev("att-1aee84ebfe", "如有改动请以选课界面显示信息为准"),
        "pitfalls.1": ev("hb89efe99078", "课程成绩无论是否及格，均不予删除"),
        "pitfalls.2": ev("7691069e", "研究生应按所在学科的培养要求，制定个人培养计划"),
    },
}

HUKOU_URL = "http://welcome.cuc.edu.cn/"
HUKOU_ANSWER = (
    "户口迁移按自愿原则办理：京外新生可以自愿把户口迁入学校集体户口；"
    "在北京就读且已是北京学生集体户口的新生必须办理迁移。"
    "符合条件但选择入学时不迁的，就读期间不得再申请迁移。"
)


def main() -> None:
    data = json.loads(ITEMS.read_text(encoding="utf-8"))
    items = data["items"]
    by = {it["id"]: n for n, it in enumerate(items)}

    assert "xuanke-kuazhuanye" not in by, "跨专业选课条目已存在，脚本只做新增"
    items.append(XUANKE)
    print("新增 xuanke-kuazhuanye，steps", len(XUANKE["steps"]))

    n = by["xinsheng-hukou"]
    hk = items[n]
    assert not hk.get("answer"), "户口条目已有 answer，不覆盖"
    hk["answer"] = HUKOU_ANSWER
    hk["evidence"]["answer"] = multi(
        ("20190802-c2753a133698", "凡属国家计划招生范围内的外埠本科生、二学位、研究生和分配来学校工作的外埠教职工，自愿办理户口迁移手续，落户学校集体户口集中管理"),
        ("loc-2026级本科生入学须知-校本部-2cdd30", "在北京就读并为北京学生集体户口的新生，必须办理户口迁移"),
        ("loc-2026级本科生入学须知-校本部-2cdd30", "入学时不迁移户口的，就读期间不得再申请迁移"),
    )
    src0 = hk["source"][0]
    if not src0.get("url"):
        src0["url"] = HUKOU_URL
        src0["checked"] = CHECKED
    extra = {"title": "中国传媒大学集体户口管理暂行规定",
             "url": "https://xsc.cuc.edu.cn/2019/0802/c2753a133698/page.htm",
             "checked": CHECKED}
    if extra["url"] not in [s.get("url") for s in hk["source"]]:
        hk["source"].append(extra)
    print("户口条目补 answer 与来源：", [s.get("url") for s in hk["source"]])

    ITEMS.write_text(json.dumps(data, ensure_ascii=False, indent=1), encoding="utf-8")
    print("写入 items.json，条目数", len(items))


if __name__ == "__main__":
    main()
