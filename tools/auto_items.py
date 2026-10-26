"""把已采集的官方文件批量转成条目（只从原文抽句，不生成事实）。

做法：
  1. 全语料统计「行频」——在很多页面都出现的行（菜单、页脚、版权）自动剔除
  2. 剩下的行按句切分，筛出"可执行句"（含 请/需/须/申请/办理/提交/登录…）
     和"风险句"（含 不得/不予/逾期/否则/取消/废止…）
  3. 每份文件生成一个条目：步骤=可执行句，易错=风险句，材料=附件名
  4. 每个字段都带 quote（原句本身），check_quotes 一定过得去

用法：
    python tools/auto_items.py --dry-run     # 只看会生成多少
    python tools/auto_items.py               # 真生成
    python tools/auto_items.py --min 120     # 正文门槛（字符）
"""
from __future__ import annotations

import json
import re
import sys
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SRC = ROOT / "sources"

ACTION = re.compile(r"请|需|须|申请|办理|提交|登录|登陆|下载|填写|携带|缴纳|缴费|上传|到.{0,6}(办理|提交)|网址|登录后")
RISK = re.compile(r"不得|不予|逾期|否则|取消|废止|不再|无效|过期|后果|退回")
CORE_HOSTS = {"jwc.cuc.edu.cn", "its.cuc.edu.cn", "xsc.cuc.edu.cn", "tiyu.cuc.edu.cn",
              "lib.cuc.edu.cn", "xyy.cuc.edu.cn", "cwc.cuc.edu.cn", "zchq.cuc.edu.cn"}
POSITIVE = re.compile(r"通知|公告|办法|规定|指南|流程|须知|申请|办理|细则|要求|说明|安排|填报|登记")
EXCLUDE = re.compile(r"名单|公示|致辞|讲话|喜报|招聘|录取|获奖|竞赛|推介|风采|讲堂|论坛|沙龙|回顾|总结|纪实|专题|答辩安排|课程介绍|会议|召开|开学|举办|年会|座谈|纪要|党委书记|校长|教育家|教师队伍|引领|建强|风采|纪实|典礼|培训会|动员|开展|举行|获评|获奖|讲堂|党员|迎新|晚会|运动会|比赛|展演|招聘会")
NAV = re.compile(r"^(菜单|链接|搜索|首页|当前位置|版权所有|京ICP|京公网安备|Copyright|返回|上一条|下一条|\{.*\})")


def load_docs() -> dict[str, dict]:
    docs: dict[str, dict] = {}
    for fname, kind in (("crawl-index.json", "官网"), ("cdp-index.json", "官网"),
                        ("wechat-index.json", "公众号"), ("index.json", "精读")):
        f = SRC / fname
        if not f.exists():
            continue
        data = json.loads(f.read_text(encoding="utf-8"))
        for slug, meta in data.items():
            if kind == "公众号" and not meta.get("official", False):
                continue
            if meta.get("chars", 0) < 150:
                continue
            docs[slug] = {"slug": slug, "kind": kind, **meta}
    return docs


def text_of(slug: str, kind: str) -> str:
    for sub in ("", "crawl", "cdp", "wechat", "pdf"):
        f = SRC / sub / f"{slug}.txt" if sub else SRC / f"{slug}.txt"
        if f.exists():
            return f.read_text(encoding="utf-8")
    return ""


def line_freq(texts: dict[str, str]) -> Counter:
    c: Counter = Counter()
    for t in texts.values():
        for line in set(t.split("\n")):
            c[line.strip()] += 1
    return c


def clean_lines(text: str, freq: Counter, total: int) -> list[str]:
    out = []
    for line in text.split("\n"):
        s = line.strip()
        if len(s) < 8 or NAV.match(s):
            continue
        if freq.get(s, 0) > max(3, total * 0.15):  # 出现在大量页面的行 = 导航/页脚
            continue
        out.append(s)
    return out


def sentences(lines: list[str]) -> list[str]:
    out = []
    for line in lines:
        for s in re.split(r"(?<=[。！？；])", line):
            s = s.strip()
            if 8 <= len(s) <= 140:
                out.append(s)
    return out


def make_keywords(title: str) -> list[str]:
    t = re.sub(r"[（(【\[].*?[）)】\]]", "", title)
    t = re.sub(r"(中国传媒大学|本科生院|教务处|通知|办法|规定|实施细则|关于|的)", " ", t)
    parts = [p.strip() for p in re.split(r"[\s、，,·]+", t) if 2 <= len(p.strip()) <= 8]
    return parts[:4]


def build(docs: dict[str, dict], texts: dict[str, str], min_chars: int) -> list[dict]:
    freq = line_freq(texts)
    total = max(1, len(texts))
    items = []
    seen_titles: set[str] = set()

    for slug, meta in sorted(docs.items(), key=lambda kv: kv[1].get("published", ""), reverse=True):
        text = texts.get(slug, "")
        if not text:
            continue
        lines = clean_lines(text, freq, total)
        body = "\n".join(lines)
        title = (meta.get("title") or "").split("|")[0].strip()
        title = re.sub(r"\s*[-—_]\s*中国传媒大学.*$", "", title).strip()
        if len(title) < 4 or EXCLUDE.search(title):
            continue
        host = (meta.get("url") or "").split("//")[-1].split("/")[0]
        # 学院站点：只收办事类标题，新闻/活动一律不要
        if host not in CORE_HOSTS and not POSITIVE.search(title):
            continue
        key = re.sub(r"\W+", "", title)
        if key in seen_titles:
            continue

        sents = sentences(lines)
        acts = [s for s in sents if ACTION.search(s)][:4]
        risks = [s for s in sents if RISK.search(s)][:3]
        atts = [l.replace("[附件]", "").strip() for l in lines if l.startswith("[附件]")][:4]
        substantive = len("".join(sents))

        # 必须有可执行句，否则就是空壳（只有附件下载的表格单列不算事项）
        if not acts:
            continue
        if substantive < min_chars and not atts:
            continue
        seen_titles.add(key)

        item_id = "doc-" + re.sub(r"[^a-z0-9]+", "-", slug.lower())[:28]
        item = {
            "id": item_id,
            "title": title,
            "aliases": list({title, key[:10]}),
            "keywords": make_keywords(title),
            "dept": "中国传媒大学",
            "channel": ["线上系统"] if "网址" in body or "登录" in body else [],
            "audience": ["本科生"],
            "status": "verified" if substantive >= min_chars else "source-thin",
            "confidence": "high" if substantive >= 300 else "medium",
            "materials": [{"name": a} for a in atts],
            "steps": [{"when": f"第 {i+1} 步", "what": s.rstrip("。；")} for i, s in enumerate(acts)],
            "fee": None, "location": None, "hours": None, "duration": None, "window": None,
            "pitfalls": [s.rstrip("。；") for s in risks],
            "kind": "notice" if re.search(r"通知|公告", title) else "rule",
            "auto": True,
            "slots": [], "draft": None,
            "source": [{"title": meta.get("title", title), "url": meta.get("url", ""),
                        "checked": "2026-10-21", "kind": meta.get("kind", ""),
                        "published": meta.get("published") or meta.get("date", "")}],
            "evidence": {},
        }
        for i, s in enumerate(acts):
            item["evidence"][f"steps.{i}"] = {"src": slug, "quote": s}
        for i, s in enumerate(risks):
            item["evidence"][f"pitfalls.{i}"] = {"src": slug, "quote": s}
        for i, a in enumerate(atts):
            item["evidence"][f"materials.{i}"] = {"src": slug, "quote": a}
        if not item["evidence"]:
            continue
        items.append(item)

    return items


def main() -> None:
    dry = "--dry-run" in sys.argv
    min_chars = 120
    if "--min" in sys.argv:
        min_chars = int(sys.argv[sys.argv.index("--min") + 1])

    docs = load_docs()
    texts = {s: text_of(s, d["kind"]) for s, d in docs.items()}
    texts = {k: v for k, v in texts.items() if v}
    print(f"语料：{len(texts)} 份可用于生成")

    items = build(docs, texts, min_chars)
    print(f"可生成条目：{len(items)}（正文≥{min_chars} 字或含附件）")

    target = ROOT / "items.json"
    data = json.loads(target.read_text(encoding="utf-8"))
    used = {s.get("url") for it in data["items"] for s in it.get("source", [])}
    fresh = [it for it in items if it["source"][0]["url"] not in used]
    print(f"其中尚未覆盖：{len(fresh)}")

    if dry:
        for it in fresh[:15]:
            print(f"  [{it['status']:<11}] {len(it['steps'])}步 {len(it['pitfalls'])}险  {it['title'][:40]}")
        return

    have = {i["id"] for i in data["items"]}
    added = 0
    for it in fresh:
        if it["id"] in have:
            continue
        data["items"].append(it)
        have.add(it["id"])
        added += 1
    data["updated"] = "2026-10-21"
    target.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"\n新增 {added} 条，条目总数 {len(data['items'])}")


if __name__ == "__main__":
    main()
