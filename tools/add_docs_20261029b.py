"""把剩余高价值未入库文档补成条目：简称对照表、2027 推免办法，并给两个服务条目补充证据。"""
from __future__ import annotations

import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
ITEMS = ROOT / "items.json"


def squash(s: str) -> str:
    return re.sub(r"\s+", "", s or "")


def read_text(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def check(src: str, quote: str) -> str:
    coll, stem = src.split("/")
    t = squash(read_text(ROOT / "sources" / coll / f"{stem}.txt"))
    q = squash(quote)
    assert q and q in t, f"引文不在原文: {src} :: {quote[:50]}"
    return quote


def main() -> None:
    data = json.loads(ITEMS.read_text(encoding="utf-8"))
    items = data["items"]
    by_id = {it["id"]: it for it in items}

    # ---------- 简称对照表 ----------
    raw_abbr = read_text(ROOT / "sources/wendao-text/cd72bce4.txt")
    abbr_quote = raw_abbr[raw_abbr.index("中国传媒大学=中传") :].strip()
    check("wendao-text/cd72bce4", abbr_quote)
    answer_lines = [
        "中国传媒大学 = 中传、传媒大学、广院、CUC、本校",
        "立德楼 = 1教 = 一教",
        "博学楼 = 48教 = 四十八教",
        "中传礼堂 = 1500报 = 大报告厅 = 1500人报告厅 = 大礼堂",
        "中传讲堂 = 400报 = 400人报告厅 = 小讲堂",
        "中传演播馆 = 1400平米演播室 = 4K演播馆",
        "手球馆 = 羽毛球馆 = 新利体育馆",
        "游泳馆 = 游泳池 = 水立方",
        "大学生活动中心 = 大活 = 活动中心",
        "操场 = 风雨操场 = 南操场 = 南操 = 田径场",
        "艺术展览中心 = 艺展中心",
    ]
    abbr = {
        "id": "campus-jiancheng",
        "title": "校园地点简称对照表（一教 / 48教 / 1500报 / 400报…）",
        "aliases": [
            "简称对照表",
            "简称",
            "一教",
            "1教",
            "立德楼",
            "48教",
            "四十八教",
            "博学楼",
            "1500报",
            "大报告厅",
            "大礼堂",
            "400报",
            "小讲堂",
            "1400平米",
            "4K演播馆",
            "手球馆",
            "羽毛球馆",
            "新利体育馆",
            "水立方",
            "大活",
            "风雨操场",
            "南操场",
            "艺展中心",
        ],
        "keywords": [],
        "dept": "校园地图",
        "channel": ["线上"],
        "audience": ["本科生", "研究生", "教职工"],
        "status": "verified",
        "confidence": "high",
        "materials": [],
        "steps": [],
        "fee": None,
        "location": None,
        "hours": None,
        "duration": None,
        "window": None,
        "pitfalls": [],
        "slots": [],
        "draft": None,
        "answer": "；".join(answer_lines) + "。",
        "kind": "service",
        "source": [
            {
                "title": "简称对应表 · 问道中传",
                "url": "https://aihub.cuc.edu.cn/doc/view/fileview?fileId=cd72bce453414bfeb0bbbf9ffd81dfd8",
                "checked": "2026-10-29",
            }
        ],
        "evidence": {"answer": {"src": "cd72bce4", "quote": abbr_quote}},
    }

    # ---------- 2027 推免办法 ----------
    tui = {
        "id": "tuimian-2027",
        "title": "2027 年推免（含直博生）申请流程",
        "aliases": [
            "推免",
            "保研",
            "推荐免试",
            "推免生",
            "直博",
            "直博生",
            "推免预报名",
            "推免服务系统",
            "复试费",
        ],
        "keywords": [],
        "dept": "招生处 / 研究生院",
        "channel": ["线上"],
        "audience": ["本科生"],
        "status": "verified",
        "confidence": "high",
        "materials": [
            {"name": "《中国传媒大学2027年招收推荐免试攻读硕士学位研究生（含直博生）申请表》（加盖所在学校教务部门或院系公章）"},
            {"name": "本人第二代（或第三代）居民身份证扫描件（正反两面，扫描在同一页上）"},
            {"name": "本科前三学年成绩单（加盖所在学校教务部门或院系公章）"},
            {"name": "大学英语水平考试成绩单或其他能证明本人外国语水平的正式成绩证明"},
            {"name": "个人陈述"},
            {"name": "其他证明材料（获奖证书、论文或著作、专利等）"},
            {"name": "诚信考试承诺书"},
        ],
        "steps": [
            {
                "when": "预报名",
                "what": "2026年9月2日10:00-9月10日20:00 登录“中国传媒大学推免预报名系统”报名并提交报考材料",
                "where": "https://yzbm.cuc.edu.cn/10033/user/login/login",
            },
            {
                "when": "材料",
                "what": "各项材料电子版整合为一个 PDF，按“报考学院_报考专业_考生姓名”命名后上传，并上传其他音视频作品",
            },
            {
                "when": "复试",
                "what": "材料评审通过后参加复试，复试前在预报名系统缴纳复试费 100 元/人；复试时间拟定 9月16日—9月18日",
            },
            {
                "when": "正式报名",
                "what": "在教育部“推免服务系统”注册、填写基本信息、上传照片、支付报名费并完成网上报名；接受并确认复试及待录取通知后才获得拟录取资格",
                "where": "https://yz.chsi.com.cn/tm",
            },
        ],
        "fee": "复试费 100 元/人",
        "location": None,
        "hours": None,
        "duration": None,
        "window": "预报名 2026年9月2日10:00-9月10日20:00；复试拟定 9月16日—9月18日",
        "pitfalls": [
            "申请专业原则上应与本科就读专业相同或相近；跨专业申请者须提供相关证明材料。",
            "预报名复试合格人员正式报名时，报考专业原则上须与公示名单中的接收学院、专业相同，变更专业需经我校同意。",
        ],
        "slots": [],
        "draft": None,
        "kind": "service",
        "source": [
            {
                "title": "中国传媒大学2027年接收推荐免试攻读硕士学位研究生（含直博生）办法",
                "url": "https://yz.cuc.edu.cn",
                "checked": "2026-10-29",
            }
        ],
        "evidence": {
            "steps.0": {
                "src": "5a54d96750",
                "quote": "预报名时间为2026年9月2日10:00-9月10日20:00，预报名系统网址为：https://yzbm.cuc.edu.cn/10033/user/login/login。",
            },
            "steps.1": {
                "src": "5a54d96750",
                "quote": "请严格按照《中国传媒大学2027年招收推荐免试攻读硕士学位研究生（含直博生）申请材料汇总表》（模板见附件4）要求的格式将各项材料的电子版整合为一个PDF文档，文件命名格式为“报考学院_报考专业_考生姓名”，通过预报名系统上传此PDF文档和其他音视频作品。",
            },
            "steps.2": {
                "src": "5a54d96750",
                "quote": "获得复试资格的考生须在复试前通过“中国传媒大学推免预报名系统”缴纳复试费，复试费为100元/人。\n复试时间拟定为9月16日—9月18日",
            },
            "steps.3": {
                "src": "5a54d96750",
                "quote": "所有报考我校的推免生须在国家规定时间内登录教育部“推免服务系统”进行注册、填写基本信息、上传照片、支付报名费，并在我校规定时间内完成网上报名等相关操作。",
            },
            "fee": {"src": "5a54d96750", "quote": "复试费为100元/人"},
            "window": {"src": "5a54d96750", "quote": "预报名时间为2026年9月2日10:00-9月10日20:00"},
            "pitfalls.0": {
                "src": "5a54d96750",
                "quote": "申请专业原则上应与本科就读专业相同或相近。对于跨专业申请者，应具备所申请专业大学本科阶段应达到的知识能力和水平，且须提供相关证明材料。",
            },
            "pitfalls.1": {
                "src": "5a54d96750",
                "quote": "报考专业原则上须与预报名复试合格人员名单公示中的接收学院（研究院、实验室）、专业相同，变更专业需经我校同意。",
            },
            "materials.0": {
                "src": "5a54d96750",
                "quote": "《中国传媒大学2027年招收推荐免试攻读硕士学位研究生（含直博生）申请表》（模板见附件1），须加盖所在学校教务部门或院系公章。",
            },
            "materials.1": {
                "src": "5a54d96750",
                "quote": "本人第二代（或第三代）居民身份证扫描件，要求身份证正反两面信息清晰，且扫描在同一页上。",
            },
            "materials.2": {
                "src": "5a54d96750",
                "quote": "本科前三学年成绩单，须加盖所在学校教务部门或院系公章。",
            },
            "materials.3": {
                "src": "5a54d96750",
                "quote": "大学英语水平考试成绩单或其他能证明本人外国语水平的正式成绩证明。",
            },
            "materials.4": {"src": "5a54d96750", "quote": "个人陈述（模板见附件2）。"},
            "materials.5": {
                "src": "5a54d96750",
                "quote": "其他证明材料，如获奖证书、发表的论文或著作、获批的专利等。",
            },
            "materials.6": {"src": "5a54d96750", "quote": "诚信考试承诺书（模板见附件3）。"},
        },
    }

    # ---------- 补充信息化处条目 ----------
    info = by_id["xinxi-fuwu-daohang"]
    info["hours"] = "上午 8:00-12:00，下午 2:00-4:30"
    info["evidence"]["hours"] = {
        "src": "252a96fb",
        "quote": "办公时间：上午8:00-12:00，下午2:00-4:30",
    }
    info["evidence"]["location"] = {
        "src": "252a96fb",
        "quote": "信息化处办公室位于25号楼3层，校园卡处理中心，也叫学生服务大厅，位于艺术与传播大楼1层。",
    }

    # ---------- 补充招生处条目 ----------
    zs = by_id["zhaosheng-chu"]
    zs["title"] = "本科 / 研究生招生咨询联系方式"
    zs["steps"] = [
        {"when": "本科招生电话", "what": "010-65779370、010-65779256（工作日 8:30-11:30；14:00-16:30）"},
        {"when": "本科招生邮箱", "what": "cuczsb@cuc.edu.cn"},
        {"when": "研究生招生电话", "what": "010-65779227"},
        {"when": "研究生招生邮箱", "what": "cucyzb@cuc.edu.cn"},
    ]
    zs["location"] = "北京市朝阳区定福庄东街一号中国传媒大学招生处（邮编 100024）"
    zs["contact"] = "本科 010-65779370、010-65779256；研究生 010-65779227"
    zs["evidence"] = {
        "steps.0": {"src": "78a2ab4a", "quote": "咨询电话：010-65779370   65779256 （工作日：8:30-11:30；14:00-16:30）"},
        "steps.1": {"src": "78a2ab4a", "quote": "咨询邮箱：cuczsb@cuc.edu.cn"},
        "steps.2": {"src": "9c682277", "quote": "电话：010-65779227"},
        "steps.3": {"src": "9c682277", "quote": "邮箱：cucyzb@cuc.edu.cn"},
        "location": {"src": "78a2ab4a", "quote": "地址：北京市朝阳区定福庄东街一号中国传媒大学招生处（邮编：100024）"},
        "contact": {"src": "78a2ab4a", "quote": "咨询电话：010-65779370   65779256 （工作日：8:30-11:30；14:00-16:30）"},
    }
    zs["source"].append(
        {
            "title": "联系我们 · 中国传媒大学本科招生",
            "url": "",
            "checked": "2026-10-29",
        }
    )

    for it in (abbr, tui):
        if it["id"] in by_id:
            items[items.index(by_id[it["id"]])] = it
        else:
            items.append(it)

    data["updated"] = "2026-10-29"
    ITEMS.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"新增/更新 2 条，补充 2 条证据；总计 {len(items)} 条")


if __name__ == "__main__":
    main()
