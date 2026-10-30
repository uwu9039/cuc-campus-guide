"""给表格类附件建「表格下载」条目：标题 + 官方下载来源，不从空白表格里抠句子。

选择范围：xls/xlsx、文本过短、正文明显是表单字段（姓名/学号/签字/审批表）。
用法：python tools/build_attachment_form_items.py --apply
"""
from __future__ import annotations

import argparse
import hashlib
import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SRC = ROOT / "sources"
TXT = SRC / "attachments" / "text"

FORM_HINT = re.compile(r"审批表|申请表|登记表|汇总表|审批单|申报表|证明|手续单|承诺书|审批意见表|标准表|计划表")
FORM_BODY = re.compile(r"姓名.{0,6}学号|学号.{0,6}姓名|签字|盖章|填表|年月日")
DEPT_BY_HOST = {
    "jwc.cuc.edu.cn": "本科生院",
    "xsc.cuc.edu.cn": "学生工作部（处）",
    "cwc.cuc.edu.cn": "财务处",
    "yz.cuc.edu.cn": "研究生院",
    "its.cuc.edu.cn": "信息化处",
    "lib.cuc.edu.cn": "图书馆",
    "hq.cuc.edu.cn": "后勤保障处",
    "bwc.cuc.edu.cn": "保卫部（处）",
    "yy.cuc.edu.cn": "校医院",
    "office.cuc.edu.cn": "党政办公室",
    "gzc.cuc.edu.cn": "国有资产管理处",
    "zchq.cuc.edu.cn": "后勤保障处",
    "research.cuc.edu.cn": "科学研究处",
}


def sq(s: str) -> str:
    return re.sub(r"\s+", "", s or "")


def clean_name(name: str) -> str:
    prev = None
    while prev != name:
        prev = name
        name = re.sub(r"\.(pdf|docx?|xlsx?|rar|zip)$", "", name, flags=re.I).strip()
    name = re.sub(r"^\d{4}-\d{2}-\d{2}\s*", "", name)
    name = re.sub(r"^附件\s*\d*\s*[：:、.]?\s*", "", name)
    return name.strip()


def pick_quote(text: str, name: str) -> str:
    t = sq(text)
    label = clean_name(name)
    cands = [sq(name), sq(label), sq(re.sub(r"[（(].*?[）)]", "", label))]
    for cand in cands:
        cand = cand.strip("《》 ")
        if len(cand) >= 6 and cand in t:
            return cand
    return ""


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--apply", action="store_true")
    ap.add_argument("--out", default="")
    args = ap.parse_args()

    idx = json.loads((SRC / "attachments-text-index.json").read_text(encoding="utf-8"))
    data = json.loads((ROOT / "items.json").read_text(encoding="utf-8"))
    have = {i["id"] for i in data["items"]}
    have_titles = {sq(i["title"]) for i in data["items"]}
    new_items = []

    for slug, meta in idx.items():
        p = TXT / f"{slug}.txt"
        text = p.read_text(encoding="utf-8") if p.exists() else ""
        name = meta["name"]
        is_form = (
            meta["ext"] in ("xls", "xlsx")
            or meta["chars"] < 300
            or (FORM_HINT.search(name) and len(FORM_BODY.findall(text)) >= 2)
        )
        if not is_form:
            continue
        label = clean_name(name)
        title = f"表格：{label}"
        if sq(title) in have_titles:
            continue
        quote = pick_quote(text, name)
        host = re.sub(r"^https?://([^/]+).*$", r"\1", meta["page_url"])
        dept = DEPT_BY_HOST.get(host, "中国传媒大学")
        item = {
            "id": "attf-" + hashlib.sha1(meta["url"].encode()).hexdigest()[:10],
            "title": title,
            "aliases": list(dict.fromkeys([label, meta["page_title"]]))[:4],
            "keywords": [w for w in re.split(r"[（）()、，,\s]+", label) if len(w) >= 2][:6],
            "dept": dept,
            "channel": [],
            "audience": ["本科生", "研究生"],
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
            "contact": None,
            "slots": [],
            "draft": None,
            "note": f"这是官方表格附件（{meta['ext'].upper()}），点下方「官方来源」下载或查看填写说明。",
            "source": [{
                "title": meta["page_title"],
                "url": meta["page_url"],
                "checked": "2026-10-30",
            }],
            "evidence": {},
            "auto": True,
            "kind": "form",
        }
        if quote:
            item["answer"] = f"官方表格《{label}》，下载与填写说明见来源页。"
            item["evidence"]["answer"] = {"src": slug, "quote": quote}
        new_items.append(item)

    print(f"表格条目 {len(new_items)} 条")
    for it in new_items[:12]:
        print(" -", it["title"][:56], "|", (it.get("answer") or "（仅来源）")[:40])
    if args.out:
        Path(args.out).write_text(json.dumps(new_items, ensure_ascii=False), encoding="utf-8")
    if args.apply:
        data["items"].extend(new_items)
        data["updated"] = "2026-10-30"
        (ROOT / "items.json").write_text(
            json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        print("written items.json, total", len(data["items"]))
    else:
        print("dry-run：未写入 items.json")


if __name__ == "__main__":
    main()
