"""把本轮补抓的 43 份文件做成条目（同文号的通知+正文合并成一条）。

依据：_wendao_digest2.json（每份文件的文号/日期/原文开头/章节标题）+ index.json（标题/链接）。
不编内容：answer 里只放原文开头与章节标题，逐字取自文件。
"""
from __future__ import annotations

import json
import re
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
P = ROOT / "items.json"
DIG = ROOT / "_wendao_digest2.json"

# fileId前8 → (kind, dept, 标题覆盖/额外别名)
META: dict[str, dict] = {
    "76fa0b1c": {"kind": "notice", "dept": "研究生院 / 招生处",
                 "title": "2025 年全国硕士研究生招生考试初试 1133 中国传媒大学考点考生须知",
                 "kw": ["考研", "考点", "初试", "考场", "研考"]},
    "e8f791b8": {"kind": "rule", "dept": "研究生院 / 招生处",
                 "title": "中国传媒大学 2025 年接收推荐免试攻读硕士学位研究生（含直博生）办法",
                 "kw": ["推免", "接收推免", "直博", "预报名", "推免办法"]},
    "f420b4ad": {"kind": "notice", "dept": "研究生院",
                 "title": "中国传媒大学 2025 年预推免网络远程复试考生须知",
                 "kw": ["预推免", "复试", "双机位", "网络远程复试"]},
    "2329e36d": {"kind": "notice", "dept": "研究生院 / 招生处",
                 "title": "中国传媒大学关于 2025 年接收推免研究生（含直博生）正式报名的提醒",
                 "kw": ["推免", "正式报名", "推免服务系统"]},
    "c0cf083f": {"kind": "rule", "dept": "国有资产管理处",
                 "title": "中传政字〔2020〕70 号 中国传媒大学修缮工程及货物管理系列办法",
                 "kw": ["修缮工程", "货物", "采购", "招标"]},
    "2d9a8928": {"kind": "rule", "dept": "国有资产管理处",
                 "title": "中传资产字〔2012〕66 号 中国传媒大学招标采购管理暂行办法",
                 "kw": ["招标", "采购", "投标"]},
    "b3e34e4b": {"kind": "rule", "dept": "人事处",
                 "title": "中传人字〔2017〕97 号 中国传媒大学实行社会化及委托评审系列评审工作实施办法（试行）",
                 "kw": ["职称", "社会化评审", "委托评审"]},
    "5cd4d846": {"kind": "rule", "dept": "人事处", "title": "中传人字〔2018〕9 号 中国传媒大学教职工考勤管理办法",
                 "kw": ["考勤", "请假", "教职工"], "merge": ["d06660fd"]},
    "73c59a13": {"kind": "rule", "dept": "人事处", "title": "中传人字〔2021〕301 号 中国传媒大学青年教授聘任实施办法",
                 "kw": ["青年教授", "聘任", "职称"]},
    "a427fd21": {"kind": "rule", "dept": "人事处", "title": "中传人字〔2022〕63 号 中国传媒大学职称评审工作管理办法",
                 "kw": ["职称评审", "职称", "评审"]},
    "200d1b7e": {"kind": "rule", "dept": "人事处", "title": "中传人字〔2023〕139 号 中国传媒大学专业技术岗位聘用基本条件",
                 "kw": ["岗位聘用", "专业技术岗位", "职称"], "merge": ["8c201857"]},
    "2ad61009": {"kind": "rule", "dept": "团委 / 党委学生工作部",
                 "title": "中传党团字〔2024〕81 号 中国传媒大学学生社团建设管理办法",
                 "kw": ["学生社团", "社团", "社团管理"]},
    "c253bde9": {"kind": "rule", "dept": "实验室与设备管理处",
                 "title": "中传实验字〔2025〕122 号 中国传媒大学实验室安全分级分类管理办法",
                 "kw": ["实验室安全", "分级分类", "危险源"]},
    "f87eef55": {"kind": "rule", "dept": "科学研究处 / 学校",
                 "title": "中传政字〔2016〕113 号 中国传媒大学预防与处理学术不端行为细则",
                 "kw": ["学术不端", "学术诚信", "抄袭", "查重"]},
    "aa31caae": {"kind": "rule", "dept": "党政办公室",
                 "title": "中传政字〔2023〕43 号 中国传媒大学合同管理办法",
                 "kw": ["合同", "合同审批", "合同管理"]},
    "8b85bfbf": {"kind": "rule", "dept": "本科生院",
                 "title": "中传教字〔2013〕37 号 中国传媒大学教学成果奖评审及奖励办法（修订）",
                 "kw": ["教学成果奖", "教学奖励"]},
    "733c88dd": {"kind": "rule", "dept": "本科生院",
                 "title": "中传教字〔2014〕118 号 中国传媒大学本科生课程调课管理办法",
                 "kw": ["调课", "停课", "代课"]},
    "03f41409": {"kind": "rule", "dept": "本科生院",
                 "title": "中传教字〔2018〕30 号 中国传媒大学本科生创新创业学分认定管理办法（试行）",
                 "kw": ["创新学分", "创新创业", "学分认定"]},
    "001e708d": {"kind": "rule", "dept": "本科生院",
                 "title": "中传教字〔2021〕259 号 中国传媒大学 2022 版本科专业培养方案修订指导意见",
                 "kw": ["培养方案", "本科专业", "课程体系"]},
    "d171e33a": {"kind": "rule", "dept": "本科生院",
                 "title": "中传教字〔2025〕196 号 中国传媒大学国际本科生学籍管理实施细则",
                 "kw": ["国际本科生", "留学生", "学籍", "国际学生"]},
    "2616e109": {"kind": "rule", "dept": "研究生院",
                 "title": "中传研字〔2025〕6 号 中国传媒大学攻读专业学位博士研究生培养工作规定",
                 "kw": ["专业学位博士", "专博", "培养"]},
    "fdf478ae": {"kind": "rule", "dept": "研究生院",
                 "title": "中传研字〔2026〕225 号 中国传媒大学攻读专业学位博士研究生培养工作规定（2026 修订）",
                 "kw": ["专业学位博士", "专博", "培养"]},
    "8869d8fd": {"kind": "rule", "dept": "科学研究处",
                 "title": "中传科研字〔2023〕245 号 中国传媒大学科研机构管理规定（修订）",
                 "kw": ["科研机构", "科研平台"], "merge": ["111786df"]},
    "acc06e20": {"kind": "rule", "dept": "国有资产管理处",
                 "title": "中传资产字〔2024〕231 号 中国传媒大学采购管理办法（2024 年修订）",
                 "kw": ["采购", "政府采购", "招标"]},
    "0634c05d": {"kind": "form", "dept": "本科生院",
                 "title": "中国传媒大学“大学生创新创业训练计划”结项证明模板",
                 "kw": ["大创", "结项", "证明模板", "表格"]},
    "fe22e365": {"kind": "service", "dept": "实验室与设备管理处",
                 "title": "中国传媒大学实验室开放预约业务说明",
                 "kw": ["实验室", "预约", "开放预约"]},
    "48b31888": {"kind": "service", "dept": "信息化处",
                 "title": "信息化服务常见问题（2026-11-03 制）",
                 "kw": ["校园网", "校园卡", "VPN", "统一身份认证", "信息化", "邮箱", "流量"]},
    "cea1bbbc": {"kind": "doc", "dept": "党政办公室",
                 "title": "公文办文材料：校内单位印发或提交学校的各类文稿的规范性提示",
                 "kw": ["公文", "办文", "格式", "文稿规范"]},
    "6577fdba": {"kind": "notice", "dept": "研究生院",
                 "title": "关于举办中国传媒大学 2023 年优秀大学生夏令营的通知",
                 "kw": ["夏令营", "优秀大学生", "推免"]},
    "14416a6e": {"kind": "notice", "dept": "研究生院",
                 "title": "关于举办中国传媒大学 2024 年优秀大学生夏令营的通知",
                 "kw": ["夏令营", "优秀大学生", "推免"]},
    "246e64d2": {"kind": "doc", "dept": "国有资产管理处",
                 "title": "国有资产管理处及各科室机构职能",
                 "kw": ["国资处", "机构职能", "科室"]},
    "892fc156": {"kind": "rule", "dept": "国务院学位委员会 / 教育部",
                 "title": "学士学位授权与授予管理办法",
                 "kw": ["学士学位", "学位授权", "学位授予"]},
    "09cf6ca8": {"kind": "form", "dept": "本科生院",
                 "title": "中国传媒大学本科生校内考试试卷复查（成绩复议）申请单",
                 "kw": ["成绩复议", "试卷复查", "申请单", "表格"]},
    "595da6b2": {"kind": "doc", "dept": "教育服务中心",
                 "title": "教育服务中心部门概况（含科室职责与教学空间办公室联系方式）",
                 "kw": ["教育服务中心", "教室", "教学空间", "场地"]},
    "037b9107": {"kind": "form", "dept": "本科生院",
                 "title": "本科生院常用表格汇编",
                 "kw": ["表格", "常用表格", "模板", "本科生院"]},
    "d52d15f7": {"kind": "service", "dept": "信息化处",
                 "title": "校外 VPN 使用说明",
                 "kw": ["VPN", "校外访问", "校外"]},
    "7a7af32f": {"kind": "service", "dept": "本科生院",
                 "title": "畅课（U3i）用户使用手册 · 学生",
                 "kw": ["畅课", "U3i", "在线教学", "学习平台"]},
    "bc52e01f": {"kind": "service", "dept": "党政办公室",
                 "title": "签报、办文办理流程",
                 "kw": ["签报", "办文", "公文", "流程"]},
    "c7d5304a": {"kind": "doc", "dept": "本科生院",
                 "title": "中国传媒大学通识教育核心课程手册 2025",
                 "kw": ["通识教育", "核心课程", "通识课", "学分"]},
    "20814f89": {"kind": "service", "dept": "本科生院",
                 "title": "学生重考、缓考报名操作流程",
                 "kw": ["重考", "缓考", "报名", "e.cuc.edu.cn"]},
}

DEPT_BY_NO = [
    ("中传教字", "本科生院"), ("中传研字", "研究生院"), ("中传人字", "人事处"),
    ("中传政字", "党政办公室"), ("中传资产字", "国有资产管理处"), ("中传科研字", "科学研究处"),
    ("中传实验字", "实验室与设备管理处"), ("中传党团字", "团委"), ("中传财字", "财务处"),
]


def dept_of(no: str, fallback: str) -> str:
    for pre, d in DEPT_BY_NO:
        if no.startswith(pre):
            return d
    return fallback or "学校"


def main() -> None:
    dig = {r["fid"]: r for r in json.loads(DIG.read_text(encoding="utf-8"))}
    idx = json.loads((ROOT / "sources" / "wendao" / "index.json").read_text(encoding="utf-8"))
    by_short = {f[:8]: (f, r) for f, r in idx.items()}
    items = json.loads(P.read_text(encoding="utf-8"))
    have = {i["id"] for i in items["items"]}

    used = set()
    new_items = []
    for fid8, meta in META.items():
        if fid8 not in by_short:
            print("跳过（找不到文件）", fid8)
            continue
        full, rec = by_short[fid8]
        d = dig.get(fid8, {})
        title = meta["title"]
        no = d.get("no") or ""
        date = d.get("date") or ""
        lead = re.sub(r"\s+", " ", d.get("lead") or "").strip()
        heads = d.get("heads") or []
        url = f"https://aihub.cuc.edu.cn/doc/view/fileview?fileId={full}"

        answer = f"《{title}》"
        if no:
            answer += f"（{no}"
            answer += f"，{date}）" if date else "）"
        elif date:
            answer += f"（{date}）"
        answer += "，全文已入库。"
        if lead and len(lead) > 12:
            answer += f"\n原文开头：{lead[:180]}"
        if heads:
            answer += "\n主要章节/条款：" + "；".join(heads[:6])
        answer += f"\n原文附件：{url}"

        kw = meta.get("kw") or []
        aliases = [title]
        if no:
            aliases.append(no.replace(" ", ""))
        aliases += kw[:4]

        item = {
            "id": f"wd-{fid8}",
            "title": title,
            "aliases": list(dict.fromkeys(aliases))[:10],
            "keywords": kw,
            "dept": dept_of(no, meta.get("dept", "")),
            "channel": ["线上文件"],
            "audience": meta.get("audience", ["本科生", "研究生", "教职工"]),
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
            "kind": meta["kind"],
            "source": [{"title": title, "url": url, "checked": "2026-11-11"}],
            "answer": answer,
            "file": rec.get("path", ""),
        }
        if item["id"] in have:
            used.add(item["id"])
            continue
        new_items.append(item)
        used.add(item["id"])

    if new_items:
        items["items"].extend(new_items)
        items["updated"] = datetime.now().strftime("%Y-%m-%d")
        tmp = P.with_suffix(".json.tmp")
        tmp.write_text(json.dumps(items, ensure_ascii=False, separators=(",", ":")), encoding="utf-8")
        tmp.replace(P)

    print("新增条目", len(new_items), "总条目", len(items["items"]))
    cov = {f for f in META} | {x for m in META.values() for x in m.get("merge", [])}
    left = sorted(set(by_short) - cov)
    print("未做条目的文件", len(left), [f for f in left])


if __name__ == "__main__":
    main()
