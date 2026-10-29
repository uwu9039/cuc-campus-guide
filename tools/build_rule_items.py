"""把"制度型"文档（汇编、办法、规定）转成条目：抽条款做要点、步骤与易错。

与 auto_items 的区别：制度文件往往没有"请/需"这种祈使句，但满是"第X条"，
所以这里按条款切分，用条款本身当事实，保证每条都能回溯原文。

用法：
    python tools/build_rule_items.py --src huibian      # 只处理制度汇编
    python tools/build_rule_items.py --src all          # 汇编 + 检索补充
"""
from __future__ import annotations

import argparse
import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SRC = ROOT / "sources"

INDEXES = {
    "wendao": ("wendao-index.json", "wendao-text"),
    "huibian": ("huibian-index.json", "huibian"),
    "extra": ("extra-index.json", "extra"),
    "cdp": ("cdp-index.json", "cdp"),
    "crawl": ("crawl-index.json", "crawl"),
    "national": ("national-index.json", "national"),
    "moe": ("moe-index.json", ""),
    "chsi": ("chsi-index.json", "chsi"),
    "local": ("local-index.json", "local"),
}

# 只有"制度型"标题才转条目，避免把新闻稿变成事项
GENERIC = {"研究生", "本科生", "中国传媒大学", "管理办法", "管理规定", "实施细则",
           "暂行办法", "工作办法", "办法", "规定", "细则", "高校", "学生", "学院"}

RULE_TITLE = re.compile(r"办法|规定|细则|制度|准则|方案|规程|规范|章程|指引|指南")

CLAUSE = re.compile(r"第[一二三四五六七八九十百零〇\d]+条")
APPLY = re.compile(r"申请|办理|提交|审批|报|备案|登记|办理|需|应当|须")
RISK = re.compile(r"不得|不予|取消|无效|后果|逾期|禁止|视为|撤销")


def norm(s: str) -> str:
    return re.sub(r"\s+", "", s)


def clauses(text: str) -> list[str]:
    """按「第X条」切条款，返回每条的完整句子。"""
    parts = CLAUSE.split(text)
    heads = CLAUSE.findall(text)
    out = []
    for h, body in zip(heads, parts[1:]):
        body = body.strip()
        if 12 <= len(body) <= 320:
            out.append(f"{h} {body}")
    return out


def build(slug: str, meta: dict, text: str) -> dict | None:
    title = (meta.get("title") or "").strip()
    title = re.sub(r"[（(]\s*[\u4e00-\u9fff]{0,12}字?〔?20\d\d〕?[^）)]*[）)]$", "", title).strip()
    if len(title) < 6:
        return None

    cs = clauses(text)
    if not cs:
        # 没有条款结构：退化成整段要点
        sents = [s for s in re.split(r"[。；\n]", text) if 14 <= len(s.strip()) <= 180]
        cs = sents[:6]
    if not cs:
        return None

    steps = [c for c in cs if APPLY.search(c)][:6]
    risks = [c for c in cs if RISK.search(c)][:4]
    if not steps and not risks:
        steps = cs[:3]

    evidence: dict[str, dict] = {}
    for i, s in enumerate(steps[:5]):
        evidence[f"steps.{i}"] = {"src": slug, "quote": s}
    for i, s in enumerate(risks[:3]):
        evidence[f"pitfalls.{i}"] = {"src": slug, "quote": s}

    staff = re.search(r"教职工|教师|校属各|各单位|各部门|二级单位|领导干部|管理人员", text[:800])
    student = re.search(r"学生|本科生|研究生|新生|毕业生", text[:1200])
    if staff and not student:
        audience = ["教职工"]
    elif student and staff:
        audience = ["本科生", "研究生", "教职工"]
    else:
        audience = ["本科生", "研究生"]

    item = {
        "id": "rule-" + re.sub(r"[^a-z0-9]+", "-", slug.lower()),
        "title": title,
        "aliases": [title[:10]],
        "keywords": [w for w in re.findall(r"[\u4e00-\u9fff]{2,6}", title)][:3],
        "dept": "中国传媒大学",
        "channel": [],
        "audience": audience,
        "status": "verified" if len(text) > 600 else "source-thin",
        "confidence": "medium",
        "materials": [],
        "steps": [{"when": f"第 {i+1} 步", "what": s[:150]} for i, s in enumerate(steps[:5])],
        "fee": None, "location": None, "hours": None, "duration": None, "window": None,
        "pitfalls": [s[:150] for s in risks[:3]],
        "slots": [], "draft": None,
        "source": [{"title": title, "url": meta.get("url", ""), "checked": "2026-10-27",
                    "page": meta.get("page_start", ""), "compilation": meta.get("compilation", "")}],
        "evidence": evidence,
        "auto": True,
    }
    return item


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--src", default="huibian")
    args = ap.parse_args()

    keys = list(INDEXES) if args.src == "all" else [args.src]
    items_p = ROOT / "items.json"
    data = json.loads(items_p.read_text(encoding="utf-8"))
    have = {i["id"] for i in data["items"]}
    existing_titles = {re.sub(r"\W+", "", i["title"]) for i in data["items"]}

    added = 0
    for key in keys:
        idx_name, folder = INDEXES[key]
        idx_file = SRC / idx_name
        if not idx_file.exists():
            continue
        idx = json.loads(idx_file.read_text(encoding="utf-8"))
        for slug, meta in idx.items():
            f = SRC / folder / f"{slug}.txt"
            if not f.exists():
                continue
            text = f.read_text(encoding="utf-8")
            if len(text) < 400:
                continue
            if key in ("crawl", "cdp") and not RULE_TITLE.search(meta.get("title", "")):
                continue
            item = build(slug, meta, text)
            if not item:
                continue
            key_title = re.sub(r"\W+", "", item["title"])
            if item["id"] in have or key_title in existing_titles:
                continue
            data["items"].append(item)
            have.add(item["id"])
            existing_titles.add(key_title)
            added += 1

    data["updated"] = "2026-10-27"
    items_p.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"新增制度型条目 {added} 条，总计 {len(data['items'])}")


if __name__ == "__main__":
    main()
