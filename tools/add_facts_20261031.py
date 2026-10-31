"""补录 2026-10-31 回归中缺失的官方事实条目。

- by-lixiao      毕业离校手续（图书馆 / 校园卡 / 户口 / 离校系统）
- jy-zhaopinhui  校园招聘会与招聘信息
- cy-fuchi       大学生创业扶持
- kaoyan-kaodian 考研报名与 1133 中传考点
- fanzha-baojing 扩充“贵重物品报案”别名与关键词

只追加 / 更新，不删除条目。写入前逐条核对引文是否能在 sources/ 原文找到。
"""
from __future__ import annotations

import json
import os
import re
import shutil
from datetime import date
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
ITEMS = ROOT / "items.json"
SRC = ROOT / "sources"


def squash(s: str) -> str:
    return re.sub(r"\s+", "", s or "")


FILES = {
    "新闻公告-9e31ce6d55288111f10b09a881613531e6a6": SRC / "ilib-list-text/新闻公告-9e31ce6d55288111f10b09a881613531e6a6.txt",
    "新闻公告-37431b7639dc8111f00b09a8d30ad1a4c87e": SRC / "ilib-list-text/新闻公告-37431b7639dc8111f00b09a8d30ad1a4c87e.txt",
    "hbf7d1b95508": SRC / "huibian/hbf7d1b95508.txt",
    "hb86645debec": SRC / "huibian/hb86645debec.txt",
    "hb49833f4409": SRC / "huibian/hb49833f4409.txt",
    "41123054": SRC / "wendao-text/41123054.txt",
    "8d71ae5f": SRC / "wendao-text/8d71ae5f.txt",
    "583a8801": SRC / "wendao-text/583a8801.txt",
    "91aac1fb": SRC / "wendao-text/91aac1fb.txt",
}
TEXTS = {k: squash(v.read_text(encoding="utf-8")) for k, v in FILES.items()}


def ev(src: str, quote: str) -> dict:
    if squash(quote) not in TEXTS[src]:
        raise SystemExit(f"引文不在原文：{src} / {quote[:50]}")
    return {"src": src, "quote": quote}


def evs(*pairs: tuple[str, str]) -> dict:
    return {"sources": [ev(s, q) for s, q in pairs]}


LIB26 = "新闻公告-9e31ce6d55288111f10b09a881613531e6a6"
SEE_2018 = "新闻公告-37431b7639dc8111f00b09a8d30ad1a4c87e"
LIB_HANDBOOK = "hbf7d1b95508"
HUB = "hb86645debec"
HUKOU = "hb49833f4409"

BY_LIXIAO = {
    "id": "by-lixiao",
    "title": "毕业离校手续（图书馆还书 / 校园卡注销 / 户口迁出）",
    "aliases": [
        "毕业离校",
        "毕业离校手续",
        "离校手续",
        "毕业生离校",
        "毕业离校时图书馆的手续",
        "离校怎么办",
        "还清图书",
        "校园卡注销",
        "户口迁出",
    ],
    "keywords": [
        "毕业离校",
        "离校手续",
        "还书",
        "论文电子版",
        "校园卡注销",
        "户口迁出",
        "离校系统",
        "毕业去向",
    ],
    "dept": "学生工作部（处）/ 图书馆 / 保卫部（处）户籍科 / 校园卡服务中心",
    "channel": ["线上系统", "线下窗口"],
    "audience": ["毕业生", "本科生", "研究生"],
    "status": "verified",
    "confidence": "high",
    "materials": [],
    "steps": [
        {
            "when": "离校系统",
            "what": "登录 http://seeu.cuc.edu.cn 离校系统（登录用户名密码即为校园网上网的用户名密码），或进入中国传媒大学微信企业号里的“数字离校”模块，核对“图书归还”“论文提交”“财务环节”“就业信息核对”四项是否都已通过；“房间退宿”及“领取证书”在毕业离校当天办理。",
            "where": "seeu.cuc.edu.cn / 微信企业号",
        },
        {
            "when": "图书馆",
            "what": "还清所借图书；研究生离校时先提交本人学位论文电子版，审核通过后方可办理离校手续。2026 届毕业生自 2026 年 6 月 1 日起停止外借图书，6 月 5 日前归还全部所借图书；图书遗失的在 6 月 5 日前到图书馆一层借还处办理赔偿。",
            "where": "图书馆一层借还处",
        },
        {
            "when": "个人物品",
            "what": "把存放在图书馆的全部个人物品取走；学期末图书馆清理时，未取走的物品按无主物品处理。",
            "where": "图书馆",
        },
        {
            "when": "校园卡",
            "what": "学生毕业离校时，由校园卡服务中心根据相关部门提供的毕业生离校信息集中办理注销手续，卡内余额转入绑定的银行卡。",
            "where": "校园卡服务中心",
        },
        {
            "when": "户口",
            "what": "外埠生源毕业生（属学校集体户口的）离校时到保卫部（处）户籍科办理户口迁出手续；需要户档暂留的，先在学生工作部（处）就业科办理手续，并持相关证明到户籍科备案。",
            "where": "30 号楼 101 户籍科",
        },
        {
            "when": "就业信息",
            "what": "在就业信息服务平台（jy.cuc.edu.cn）填报毕业去向信息，毕业去向关系到离校时的档案、户口转寄。",
            "where": "jy.cuc.edu.cn",
        },
    ],
    "fee": None,
    "location": "图书馆一层借还处 / 30 号楼 101 户籍科",
    "hours": None,
    "duration": None,
    "window": None,
    "pitfalls": [],
    "slots": [],
    "draft": None,
    "answer": None,
    "kind": "service",
    "source": [
        {
            "title": "图书馆关于2026届毕业生办理图书归还事宜的通知",
            "url": "https://ilib.cuc.edu.cn/engine2/data/api-v2/detail/data/c623aaa02a1a0311ef28b096bdaff9e3cef8/c6272d110a1a0311ef28b098d1b322c5ad5e/9e31ce6d55288111f10b09a881613531e6a6",
            "checked": "2026-10-31",
        },
        {
            "title": "中国传媒大学图书馆校园“一卡通”管理办法",
            "url": "https://xsc.cuc.edu.cn/2023/0904/c2753a259796/page.htm",
            "checked": "2026-10-31",
            "page": 359,
            "compilation": "学生工作规章制度汇编2025",
        },
        {
            "title": "中国传媒大学学生工作规章制度汇编（2025）· 校园卡管理办法 / 集体户口管理暂行规定",
            "url": "",
            "checked": "2026-10-31",
        },
        {
            "title": "关于2018届毕业生使用离校系统的温馨提示",
            "url": "https://ilib.cuc.edu.cn/engine2/data/api-v2/detail/data/c623aaa02a1a0311ef28b096bdaff9e3cef8/c6272d110a1a0311ef28b098d1b322c5ad5e/37431b7639dc8111f00b09a8d30ad1a4c87e",
            "checked": "2026-10-31",
        },
        {
            "title": "学生工作部（处）服务事项 · 毕业生就业信息",
            "url": "https://aihub.cuc.edu.cn/doc/view/fileview?fileId=4112305464ed49598167bad4189ed2ae",
            "checked": "2026-10-31",
        },
    ],
    "evidence": {
        "location": evs(
            (LIB26, "到图书馆一层借还处"),
            ("91aac1fb", "到 30 号楼 101"),
        ),
        "steps.0": evs(
            (SEE_2018, "登录http://seeu.cuc.edu.cn离校系统"),
            (SEE_2018, "或进入中国传媒大学微信企业号里的“数字离校”模块"),
            (SEE_2018, "核对“图书归还”、“论文提交”、“财务环节”、“就业信息核对”四项是否都已通过"),
            (SEE_2018, "“房间退宿”及“领取证书”项目请在毕业离校当天办理"),
        ),
        "steps.1": evs(
            (LIB_HANDBOOK, "读者离校（包括毕业、工作调动、休学、退学、出国、结业等）时，须还清所借图书，方可办理离校手续。"),
            (LIB_HANDBOOK, "研究生离校时，应先提交本人学位论文电子版，审核通过后方可办理离校手续。"),
            (LIB26, "自2026年6月1日（周一）起，停止毕业生外借图书，但可继续入馆阅览学习直至校园一卡通注销。"),
            (LIB26, "毕业生应在2026年6月5日（周五）前，归还全部所借图书，如本人名下有未归还图书，将影响毕业离校手续的办理。"),
            (LIB26, "如图书遗失，请提前到图书馆一层借还处办理赔偿手续（包括购买到同版本图书），办理赔偿的截止日期为2026年6月5日（周五）。"),
        ),
        "steps.2": evs(
            (LIB26, "请将存放在图书馆的全部个人物品取走。"),
            (LIB26, "届时未取走的物品将被视为无主物品进行处理"),
        ),
        "steps.3": ev(
            HUB,
            "学生毕业离校时，由校园卡服务中心根据相关部门提供的毕业生离校信息集中办理注销手续，并将卡内余额转入绑定的银行卡内。",
        ),
        "steps.4": evs(
            (HUKOU, "外埠生源毕业生（属我校集体户口的）离校时要到保卫部（处）户籍科办理户口迁出手续。"),
            (HUKOU, "需要办理户档暂留手续的，在学生工作部（处）就业科办理相应的手续，并持相关证明到保卫部（处）户籍科备案。"),
        ),
        "steps.5": ev(
            "41123054",
            "毕业生在“学生就业服务平台”（jy.cuc.edu.cn）填报的毕业去向信息关系着毕业生离校时的档案、户口转寄",
        ),
    },
    "note": "图书馆的 2026 年 6 月 1 日、6 月 5 日是 2026 届安排，其他届次以当年图书馆通知为准；离校系统入口为 2018 年学校通知，入口如有调整以当年毕业生通知为准。",
}

JY_ZHAOPINHUI = {
    "id": "jy-zhaopinhui",
    "title": "校园招聘会与招聘信息（jy.cuc.edu.cn）",
    "aliases": [
        "校园招聘会",
        "招聘会",
        "招聘信息",
        "宣讲会",
        "双选会",
        "就业信息网",
        "校园招聘",
        "找工作",
    ],
    "keywords": [
        "招聘",
        "招聘会",
        "宣讲会",
        "双选会",
        "招聘信息",
        "就业信息网",
        "jy.cuc.edu.cn",
        "就业创业指导中心",
    ],
    "dept": "学生工作部（处）就业创业指导中心",
    "channel": ["线上系统", "线下窗口"],
    "audience": ["毕业生", "本科生", "研究生"],
    "status": "verified",
    "confidence": "high",
    "materials": [],
    "steps": [
        {
            "when": "看招聘信息",
            "what": "用人单位通过中国传媒大学就业信息网（jy.cuc.edu.cn）的用人单位板块登录，提交招聘实习信息；审核通过的信息发布在就业信息网。",
            "where": "jy.cuc.edu.cn",
        },
        {
            "when": "校园招聘活动",
            "what": "用人单位登录系统后台，选择宣讲会或者双选会功能板块，选择对应场次预约参会；学校发布线上宣讲会预约指南和学期招聘活动安排。",
            "where": "jy.cuc.edu.cn",
        },
        {
            "when": "咨询",
            "what": "就业创业指导中心：65779343，游泳馆 3 楼 308 室，工作日 8:30-11:30、14:00-16:30。",
            "where": "游泳馆 3 楼 308 室",
        },
        {
            "when": "毕业去向",
            "what": "毕业生在“学生就业服务平台”（jy.cuc.edu.cn）填报毕业去向信息，信息关系到离校时的档案、户口转寄。",
            "where": "jy.cuc.edu.cn",
        },
    ],
    "fee": None,
    "location": "游泳馆 3 楼 308 室",
    "hours": "工作日 8:30-11:30；14:00-16:30",
    "duration": None,
    "window": "常年",
    "pitfalls": [],
    "slots": [],
    "draft": None,
    "answer": None,
    "kind": "service",
    "source": [
        {
            "title": "学生工作部（处）服务事项 · 用人单位招聘、岗位信息发布、校园招聘活动预约",
            "url": "https://aihub.cuc.edu.cn/doc/view/fileview?fileId=4112305464ed49598167bad4189ed2ae",
            "checked": "2026-10-31",
        }
    ],
    "evidence": {
        "location": ev("41123054", "游泳馆 3 楼 308 室"),
        "hours": ev("41123054", "工作日 8:30-11:30; 14:00-16:30"),
        "window": ev("41123054", "常年"),
        "steps.0": evs(
            ("41123054", "用人单位通过中国传媒大学就业信息网（jy.cuc.edu.cn）的用人单位板块登陆"),
            ("41123054", "审核通过的信息将发布在中国传媒大学就业信息网（jy.cuc.edu.cn）"),
        ),
        "steps.1": evs(
            ("41123054", "登陆后可以通过系统后台选择宣讲会或者双选会功能板块，选择对应场次预约参会。"),
            ("41123054", "中国传媒大学线上宣讲会预约指南"),
        ),
        "steps.2": evs(
            ("41123054", "65779343"),
            ("41123054", "游泳馆 3 楼 308 室"),
            ("41123054", "工作日 8:30-11:30; 14:00-16:30"),
        ),
        "steps.3": ev(
            "41123054",
            "毕业生在“学生就业服务平台”（jy.cuc.edu.cn）填报的毕业去向信息关系着毕业生离校时的档案、户口转寄",
        ),
    },
}

CY_FUCHI = {
    "id": "cy-fuchi",
    "title": "大学生创业扶持（经费、场地、培训、学分）",
    "aliases": [
        "大学生创业",
        "创业扶持",
        "创业政策",
        "创业支持",
        "创业基金",
        "创业园",
        "创业孵化",
        "创业扶持政策",
    ],
    "keywords": [
        "创业",
        "创业支持经费",
        "创新创业专项基金",
        "创业园",
        "孵化基地",
        "创业培训",
        "创新创业学分",
        "休学创业",
    ],
    "dept": "就业创业指导中心 / 教务处 / 研究生院",
    "channel": ["线上", "线下"],
    "audience": ["本科生", "研究生"],
    "status": "verified",
    "confidence": "high",
    "materials": [],
    "steps": [
        {
            "when": "经费支持",
            "what": "学校设立“学生创业支持经费”，学校教育基金会设立“学生创新创业专项基金”，鼓励各学部（院）多渠道联合社会资源资助，用于支持学生创新创业。",
            "where": "学校 / 教育基金会",
        },
        {
            "when": "场地支持",
            "what": "北京中传资产管理有限公司利用北京高校大学生创业园孵化体系、校企合作创业孵化基地等平台，集合创业实训基地、创业孵化器、创业园于一体，为学生创业提供场地支持。",
            "where": "北京中传资产管理有限公司",
        },
        {
            "when": "培训与咨询",
            "what": "就业创业指导中心对有创业愿望并具备一定创业条件的学生开展创业培训，面向学生创业团队提供咨询、辅导、培训、交流等服务；团委举办创新创业大赛、模拟创业等实践活动。",
            "where": "就业创业指导中心 / 团委",
        },
        {
            "when": "学分",
            "what": "教务处、研究生院设置创新创业学分；学生参加创新创业活动或校级以上创新创业竞赛并获得优秀成绩，按相关规定获得相应创新创业学分。",
            "where": "教务处 / 研究生院",
        },
        {
            "when": "休学创业",
            "what": "新生可以申请保留入学资格开展创新创业实践，入学后也可以申请休学开展创业；休学创业次数和期限、最长修业年限、休学创业及复学手续按本科生学籍管理规定和研究生学籍管理规定执行。",
            "where": "教务处 / 研究生院",
        },
    ],
    "fee": None,
    "location": None,
    "hours": None,
    "duration": None,
    "window": None,
    "pitfalls": [],
    "slots": [],
    "draft": None,
    "answer": None,
    "kind": "service",
    "source": [
        {
            "title": "中传就业字〔2017〕281号 中国传媒大学学生就业创业工作管理规定",
            "url": "https://aihub.cuc.edu.cn/doc/view/fileview?fileId=8d71ae5f61a543d681e34cc63491b6c2",
            "checked": "2026-10-31",
        }
    ],
    "evidence": {
        "steps.0": evs(
            ("8d71ae5f", "学校设立“学生创业支持经费”"),
            ("8d71ae5f", "学校教育基金会设立“学生创新创业专项基金”"),
        ),
        "steps.1": evs(
            ("8d71ae5f", "北京中传资产管理有限公司负责充分利用北京高校大学生创业园孵化体系、校企合作创业孵化基地等创新创业"),
            ("8d71ae5f", "集合创业实训基地、创业孵化器、创业园于一体，为学生创业提供场地支持。"),
        ),
        "steps.2": evs(
            ("8d71ae5f", "就业创业指导中心负责对有创业愿望并具备一定创业条件的学生，开展创业培训。"),
            ("8d71ae5f", "就业创业指导中心负责面向学生创业团队提供咨询、辅导、培训、交流等服务。"),
            ("8d71ae5f", "团委负责举办创新创业大赛、模拟创业等实践活动"),
        ),
        "steps.3": evs(
            ("8d71ae5f", "教务处、研究生院负责设置创新创业学分。"),
            ("8d71ae5f", "学生参加创新创业活动或校级以上创新创业竞赛并获得优秀成绩，按教务处及研究生院相关规定获得相应创新创业学分。"),
        ),
        "steps.4": ev(
            "8d71ae5f",
            "新生可以申请保留入学资格开展创新创业实践，入学后也可以申请休学开展创业。",
        ),
    },
}

KAOYAN_KAODIAN = {
    "id": "kaoyan-kaodian",
    "title": "考研报名与考点（1133 中传考点）",
    "aliases": [
        "考研报名",
        "考研考点",
        "研究生考试报名",
        "中传考点",
        "1133考点",
        "1133",
        "网上确认",
        "现场确认",
        "研究生招生考试",
    ],
    "keywords": [
        "考研",
        "报名",
        "考点",
        "1133",
        "研招网",
        "网上确认",
    ],
    "dept": "研究生院 / 中国传媒大学考点（1133）",
    "channel": ["线上系统"],
    "audience": ["本科生", "研究生"],
    "status": "verified",
    "confidence": "high",
    "materials": [],
    "steps": [
        {
            "when": "网上报名",
            "what": "在“中国研究生招生信息网”（全国研招网，https://yz.chsi.com.cn）网上报名；网上报名时间按国家统一规定，逾期不再补报，也不得修改报名信息。",
            "where": "yz.chsi.com.cn",
        },
        {
            "when": "北京应届生",
            "what": "报考中国传媒大学、学校所在地为北京地区的应届本科毕业生，必须选择中国传媒大学考点（考点代码 1133）办理网上报名和网上确认手续。",
            "where": "中国传媒大学考点 1133",
        },
        {
            "when": "其他考生",
            "what": "其他报考中传的考生，符合中传研招网发布的 1133 考点确认须知要求的，选择 1133 考点；不符合的，选择户籍所在地省级教育招生考试机构指定的报考点。",
            "where": "中传研招网 yz.cuc.edu.cn",
        },
        {
            "when": "信息查询",
            "what": "考点确认须知等后续文件在中国传媒大学研招网（https://yz.cuc.edu.cn）发布；也可在“全国研招网”查询各省级教育招生考试机构的网报公告。",
            "where": "yz.cuc.edu.cn",
        },
    ],
    "fee": None,
    "location": None,
    "hours": None,
    "duration": None,
    "window": None,
    "pitfalls": [
        "一位考生只能保留一条有效报名信息；逾期不再补报，也不得修改报名信息。",
    ],
    "slots": [],
    "draft": None,
    "answer": None,
    "kind": "service",
    "source": [
        {
            "title": "中国传媒大学2025年攻读硕士学位研究生招生简章",
            "url": "https://aihub.cuc.edu.cn/doc/view/fileview?fileId=583a8801617a496494a7927dd8de361b",
            "checked": "2026-10-31",
        }
    ],
    "evidence": {
        "steps.0": evs(
            ("583a8801", "报名网址：“中国研究生招生信息网”（网址：https：//yz.chsi.com.cn"),
            ("583a8801", "网上报名时间：按国家统一规定（逾期不再补报，也不得再修改报名信息）。"),
        ),
        "steps.1": ev(
            "583a8801",
            "其中，学校所在地为北京地区且报考中国传媒大学的应届本科毕业生，必须选择中国传媒大学考点（考点代码1133）办理网上报名和网上确认手续。",
        ),
        "steps.2": evs(
            ("583a8801", "符合中传研招网（https://yz.cuc.edu.cn）发布的《2025年全国硕士研究生招生考试1133中国传媒大学考点确认须知》相关要求的考生，须选择中国传媒大学考点（考点代码1133）办理网上报名和网上确认手续。"),
            ("583a8801", "不符合①中所述相关要求的考生，应选择户籍所在地省级教育招生考试机构指定的报考点办理网上报名和网上确认手续。"),
        ),
        "steps.3": evs(
            ("583a8801", "中传研招网（https://yz.cuc.edu.cn）"),
            ("583a8801", "考生可通过“全国研招网”查询各省级教育招生考试机构的网报公告"),
        ),
        "pitfalls.0": ev(
            "583a8801",
            "一位考生只能保留一条有效报名信息。逾期不再补报，也不得修改报名信息。",
        ),
    },
    "note": "以上为 2025 年硕士招生简章口径，当年考点代码与确认要求以最新招生简章和中传研招网通知为准。",
}

NEW_ITEMS = [BY_LIXIAO, JY_ZHAOPINHUI, CY_FUCHI, KAOYAN_KAODIAN]


def main() -> None:
    data = json.loads(ITEMS.read_text(encoding="utf-8"))
    items = data["items"]
    by_id = {i["id"]: i for i in items}
    for item in NEW_ITEMS:
        if item["id"] in by_id:
            raise SystemExit(f"条目已存在：{item['id']}")

    shutil.copy2(ITEMS, ROOT / "items_before_facts_20261031.json")
    for item in NEW_ITEMS:
        items.append(item)
        print(f"ADD {item['id']} | {item['title']}")

    baojing = by_id.get("fanzha-baojing")
    if not baojing:
        raise SystemExit("找不到 fanzha-baojing")
    add_alias = ["贵重物品丢失", "丢了贵重物品", "物品丢失", "校园被盗", "被盗", "失窃", "东西被偷", "报案"]
    add_kw = ["报案", "贵重物品", "被盗", "失窃", "3110"]
    before_a, before_k = len(baojing["aliases"]), len(baojing["keywords"])
    for a in add_alias:
        if a not in baojing["aliases"]:
            baojing["aliases"].append(a)
    for k in add_kw:
        if k not in baojing["keywords"]:
            baojing["keywords"].append(k)
    print(f"UPDATE fanzha-baojing aliases {before_a}->{len(baojing['aliases'])} keywords {before_k}->{len(baojing['keywords'])}")

    data["updated"] = date.today().isoformat()
    tmp = ITEMS.with_suffix(".json.tmp")
    tmp.write_text(json.dumps(data, ensure_ascii=False, indent=1), encoding="utf-8")
    os.replace(tmp, ITEMS)
    print(f"已写入，items={len(items)}")


if __name__ == "__main__":
    main()
