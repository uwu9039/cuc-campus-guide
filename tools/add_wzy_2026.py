"""把 2026 年秋季 11 份微专业招生简章逐节、逐课、逐段做成条目。

约定：所有 answer / steps / pitfalls 等事实字段的引文必须是
sources/pdf/wzy-2026-*.txt 原文子串（去掉空白后）。条目只增不删。
"""
from __future__ import annotations

import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SRC = ROOT / "sources" / "pdf"
PAGE_URL = "https://jwc.cuc.edu.cn/2026/0724/c6479a272951/page.htm"
GEN_ID = "doc-20260724-c6479a272951"
CHECKED = "2026-10-29"

HEAD = re.compile(r"^([一二三四五六七八九十]+)、\s*(.+)$")
NATURE = re.compile(r"(必修|选修|实训|限选)$")


def squash(s: str) -> str:
    return re.sub(r"\s+", "", s or "")


def flat(lines: list[str]) -> str:
    return "".join(ln.strip() for ln in lines)


def sections_of(lines: list[str]) -> dict[str, list[str]]:
    heads: list[tuple[int, str]] = []
    for i, ln in enumerate(lines):
        m = HEAD.match(ln)
        if m:
            heads.append((i, m.group(2).strip()))
    out: dict[str, list[str]] = {}
    for j, (i, title) in enumerate(heads):
        end = heads[j + 1][0] if j + 1 < len(heads) else len(lines)
        out.setdefault(title, lines[i + 1:end])
    return out


def pick(secs: dict[str, list[str]], *names: str) -> str:
    for n in names:
        if n in secs:
            return flat(secs[n])
    return ""


def sentence_with(text: str, needle: str) -> str:
    """取包含 needle 的整句（按句号切），用于 fee 这类引文。"""
    i = text.find(needle)
    if i < 0:
        return ""
    start = text.rfind("。", 0, i) + 1
    end = text.find("。", i)
    end = len(text) if end < 0 else end + 1
    return text[start:end]


def parse_enroll(enroll: str) -> list[dict[str, str]]:
    marks = [(m.start(), m.group(1)) for m in re.finditer(r"第([一二三])阶段", enroll)]
    steps: list[dict[str, str]] = []
    for k, (pos, num) in enumerate(marks):
        end = marks[k + 1][0] if k + 1 < len(marks) else len(enroll)
        body = enroll[pos:end].strip()
        steps.append({"when": f"第{num}阶段", "what": body})
    return steps


def parse_courses(lines: list[str]) -> tuple[list[dict[str, str]], str]:
    rows: list[list[str]] = []
    cur: list[str] | None = None
    for ln in lines:
        if ln.startswith("合计"):
            if cur:
                rows.append(cur)
                cur = None
            continue
        if re.match(r"^\d{1,2}\s+\D", ln):
            if cur:
                rows.append(cur)
            cur = [ln]
        elif cur is not None:
            cur.append(ln)
    if cur:
        rows.append(cur)
    out: list[dict[str, str]] = []
    for row in rows:
        text = " ".join(" ".join(row).split())
        m = re.match(r"^(\d{1,2})\s+(.+?)\s+(必修|选修|实训|限选)\s+(\d+(?:\.\d+)?)\s+(\d+)\s*$", text)
        if m:
            out.append({
                "no": m.group(1), "name": m.group(2).strip(), "credits": m.group(4),
                "hours": m.group(5), "teacher": "", "nature": m.group(3), "text": text,
            })
            continue
        m = re.match(r"^(\d{1,2})\s+(.+?)\s+(\d+(?:\.\d+)?)\s+(\d+)\s+(.*)$", text)
        if not m:
            continue
        rest = m.group(5).split()
        nature = next((t for t in rest if NATURE.match(t)), "")
        if not nature:
            continue
        idx = rest.index(nature)
        before, after = rest[:idx], rest[idx + 1:]
        skip = {"中英", "中文", "英文", "双语"}
        teacher = " ".join(before) if before and not any(
            k in " ".join(before) for k in ("学期", "直播", "录播", "线下", "线上", "秋季", "春季")) else ""
        if not teacher:
            teacher = " ".join(t for t in after if t not in skip)
        out.append({
            "no": m.group(1), "name": m.group(2).strip(), "credits": m.group(3),
            "hours": m.group(4), "teacher": teacher.strip(), "nature": nature,
            "text": text,
        })
    if not out:
        for ln in lines:
            text = " ".join(ln.split())
            m = re.match(r"^(.+?)\s+(\d+(?:\.\d+)?)\s+(\d+)\s+(?:\d+\s+)*(?:秋季|春季|秋季学期|春季学期)?\s*(必修|选修|实训|限选)\s*$", text)
            if m:
                out.append({
                    "no": str(len(out) + 1), "name": m.group(1).strip(),
                    "credits": m.group(2), "hours": m.group(3), "teacher": "",
                    "nature": m.group(4), "text": text,
                })
    table = flat([ln for ln in lines if not ln.startswith("合计")])
    return out, table


def parse_descs(lines: list[str], names: list[str] | None = None) -> list[dict[str, str]]:
    known: dict[str, str] = {}
    for n in names or []:
        k = squash(n)
        if len(k) >= 2:
            known[k] = n
    order = sorted(known, key=len, reverse=True)

    def heading(ln: str) -> tuple[str, str]:
        m = re.match(r"^【(.+?)】\s*$", ln)
        if m and "模块" not in m.group(1):
            return m.group(1).strip(), ""
        m = re.match(r"^（[一二三四五六七八九十]+）\s*(.+)$", ln)
        if m:
            return m.group(1).strip(), ""
        m = re.match(r"^\d{1,2}[.、]\s*(.+)$", ln)
        if m:
            return m.group(1).strip(), ""
        k = squash(ln)
        for key in order:
            if k.startswith(key) and len(k) > len(key):
                tail = k[len(key):]
                if tail[:1] in ("：", ":"):
                    return known[key], tail[1:]
        return "", ""

    out: list[dict[str, str]] = []
    cur: dict[str, object] | None = None

    def close() -> None:
        nonlocal cur
        if cur:
            out.append({"name": cur["name"], "text": flat(cur["lines"])})
            cur = None

    for ln in lines:
        if re.match(r"^(中国传媒大学.*学院|音乐与录音艺术学院|\d{4}\s*年\s*\d{1,2}\s*月)$", ln):
            close()
            continue
        name, rest = heading(ln)
        if name:
            name = re.sub(r"\s*[（(][A-Za-z][^)）]*[)）]\s*$", "", name).strip()
            close()
            cur = {"name": name, "lines": [rest] if rest else []}
        elif cur is not None:
            cur["lines"].append(ln)
    close()
    return out


def qr_label(text: str) -> str:
    if "jiandaoyun.com/app/" in text:
        return "本校学生报名二维码"
    if "jiandaoyun.com/f/" in text:
        return "校外人员报名二维码"
    if "weixin.qq.com" in text:
        return "公众号二维码"
    return ""


def build_one(meta: dict) -> tuple[list[dict], dict]:
    slug = meta["slug"]
    txt = (SRC / f"{slug}.txt").read_text(encoding="utf-8")
    lines = [ln.strip() for ln in txt.splitlines() if ln.strip()]
    secs = sections_of(lines)
    name = lines[1].replace("微专业", "").strip() if len(lines) > 1 else slug
    title = f"2026年秋季{name}微专业招生简章"

    intro = pick(secs, "微专业介绍")
    goal = pick(secs, "培养目标")
    req = pick(secs, "培养要求")
    audience = pick(secs, "招生对象及条件")
    duration = pick(secs, "学制")
    mode = pick(secs, "授课方式")
    cert = pick(secs, "学分认定与证书颁发", "学分认定与证书授予")
    enroll = pick(secs, "招生时间安排及报名方式")
    contact = pick(secs, "咨询方式")
    fee_sec = pick(secs, "微专业课程费用")
    advantage = pick(secs, "课程优势")

    college = ""
    m = re.search(r"由(?:中国传媒大学)?(.+?)颁发微专业证书", cert)
    if m:
        college = m.group(1)
    if not college and contact:
        m = re.match(r"^(.+?学院)", contact)
        if m:
            college = m.group(1)
    dept = college or "中国传媒大学"

    quota = ""
    m = re.search(r"计划招生[^。]*。?", audience)
    if m:
        quota = m.group(0)

    fee_value = ""
    fee_quotes: list[str] = []
    fm = re.search(r"(\d+)\s*元/学分[，,]?\s*总计\s*(\d+)\s*元", fee_sec or txt)
    if fm:
        fee_value = f"{fm.group(1)} 元/学分，总计 {fm.group(2)} 元"
        fee_quotes = [sentence_with(fee_sec or txt, "元/学分") or fm.group(0)]
    else:
        m1 = re.search(r"(\d+)\s*元/学分", fee_sec or txt)
        m2 = re.search(r"总计\s*(\d+)\s*元", fee_sec or txt)
        if m1 and m2:
            fee_value = f"{m1.group(1)} 元/学分，总计 {m2.group(1)} 元"
            fee_quotes = [q for q in (sentence_with(fee_sec or txt, "元/学分"),
                                      sentence_with(fee_sec or txt, "总计")) if q]

    window = ""
    wm = re.search(r"\d{4}年\d{1,2}月\d{1,2}日(?:\d{1,2}:\d{2})?之前", enroll)
    if wm:
        window = wm.group(0)

    pitfalls: list[str] = []
    for pat in (r"每位学生限报一个微专业[^。]*。?", r"报名期间系统只允许提交一次[^。]*。?",
                r"(?:实际)?缴费人数不足[^。]*。?", r"不足\d+人时[^。]*。?"):
        mm = re.search(pat, enroll or txt)
        if mm and mm.group(0) not in pitfalls:
            pitfalls.append(mm.group(0))

    steps = parse_enroll(enroll)
    src = slug
    courses, table = parse_courses(secs.get("课程设置及学时分配表", []))
    course_src = src
    if not courses:
        alt = SRC / f"{slug}-table.txt"
        if alt.exists():
            tlines = [ln.strip() for ln in alt.read_text(encoding="utf-8").splitlines() if ln.strip()]
            courses, table = parse_courses(tlines)
            course_src = alt.stem
    descs = parse_descs(secs.get("微专业课程简介", []), [c["name"] for c in courses])

    pdf_url = meta["url"]
    srcs = [{"title": f"{title}（PDF）", "url": pdf_url, "checked": CHECKED},
            {"title": "2026年秋季微专业招生信息", "url": PAGE_URL, "checked": CHECKED}]
    qrs = [{"label": qr_label(q["text"]), "src": f"/qr/wzy-2026/{q['file']}"}
           for q in meta.get("qr", []) if qr_label(q["text"])]

    audience_tags = ["本科生", "研究生"]
    if "校外人员" in audience:
        audience_tags.append("校外人员")

    base = {
        "dept": dept, "channel": ["微专业"], "audience": audience_tags,
        "status": "verified", "confidence": "high", "materials": [],
        "fee": None, "location": None, "hours": None, "duration": None,
        "window": None, "pitfalls": [], "slots": [], "draft": None,
        "source": srcs, "auto": True,
    }
    items: list[dict] = []

    ev: dict[str, dict] = {}
    for i, s in enumerate(steps):
        ev[f"steps.{i}"] = {"src": src, "quote": s["what"]}
    for i, p in enumerate(pitfalls):
        ev[f"pitfalls.{i}"] = {"src": src, "quote": p}
    if fee_value:
        if len(fee_quotes) > 1:
            ev["fee"] = {"sources": [{"src": src, "quote": q} for q in fee_quotes]}
        else:
            ev["fee"] = {"src": src, "quote": fee_quotes[0] if fee_quotes else fee_value}
    if duration:
        ev["duration"] = {"src": src, "quote": duration}
    if mode:
        ev["hours"] = {"src": src, "quote": mode}
    if window:
        ev["window"] = {"src": src, "quote": window}
    if contact:
        ev["contact"] = {"src": src, "quote": contact}

    overview = {
        **base,
        "id": f"wzy26-{slug}",
        "title": title,
        "aliases": [f"{name}微专业", f"2026年秋季{name}微专业", f"{name}招生简章",
                    f"{name}微专业招生简章", f"2026年秋季{name}微专业招生简章"],
        "keywords": ["微专业", name, "报名", "费用", "学制"],
        "steps": steps,
        "fee": fee_value or None,
        "hours": mode or None,
        "duration": duration or None,
        "window": window or None,
        "pitfalls": pitfalls,
        "contact": contact or None,
        "pdf": [{"title": meta["title"], "url": pdf_url}],
        "qr": qrs,
        "kind": "procedure",
        "evidence": ev,
    }
    items.append(overview)

    def point(key: str, ptitle: str, answer: str, extra_aliases: list[str],
              keywords: list[str], quote: str | None = None, ev_src: str | None = None,
              quotes: list[str] | None = None, **fields) -> None:
        if not answer:
            return
        if quotes and len(quotes) > 1:
            evidence = {"answer": {"sources": [{"src": ev_src or src, "quote": q} for q in quotes]}}
        else:
            evidence = {"answer": {"src": ev_src or src, "quote": quote or answer}}
        # fee/location/hours/duration/window 是独立事实字段，校验器要求各自有证据
        for fact in ("fee", "location", "hours", "duration", "window"):
            if fields.get(fact):
                evidence[fact] = evidence["answer"]
        items.append({
            **base, "id": f"wzy26-{slug}-{key}", "title": ptitle,
            "aliases": [ptitle, *extra_aliases],
            "keywords": ["微专业", name, *keywords],
            "kind": "paragraph", "para": True,
            "answer": answer,
            "evidence": evidence,
            **fields,
        })

    point("intro", f"{name}微专业介绍", intro,
          [f"{name}微专业介绍"], ["介绍", "培养"], )
    point("goal", f"{name}微专业培养目标", goal, [f"{name}培养目标"], ["培养目标"], )
    point("req", f"{name}微专业培养要求", req, [f"{name}培养要求"], ["培养要求"], )
    point("audience", f"{name}微专业招生对象及条件", audience,
          [f"{name}招生对象", f"{name}微专业报名条件"], ["招生对象", "报名条件"])
    point("quota", f"{name}微专业计划招生人数", quota,
          [f"{name}微专业招多少人", f"{name}招生人数"], ["计划招生", "名额"])
    point("duration", f"{name}微专业学制", duration,
          [f"{name}微专业读多久", f"{name}学制"], ["学制", "多久"])
    point("mode", f"{name}微专业授课方式", mode,
          [f"{name}微专业怎么上课", f"{name}授课方式"], ["授课方式", "上课", "线上", "线下"])
    point("cert", f"{name}微专业学分认定与证书", cert,
          [f"{name}微专业证书", f"{name}微专业学分认定"], ["证书", "学分认定", "学分兑换"])
    point("enroll", f"{name}微专业报名时间及报名方式", enroll,
          [f"{name}微专业报名", f"{name}微专业报名时间", f"{name}微专业怎么报名"],
          ["报名", "报名时间", "报名方式"])
    point("contact", f"{name}微专业咨询方式", contact,
          [f"{name}微专业咨询", f"{name}微专业联系方式"], ["咨询", "电话", "联系方式"],
          contact=contact or None)
    point("fee", f"{name}微专业课程费用", fee_value or "",
          [f"{name}微专业学费", f"{name}微专业多少钱"], ["费用", "学费", "多少钱"],
          quotes=fee_quotes or None, fee=fee_value or None)
    point("courses", f"{name}微专业课程设置及学时分配表", table,
          [f"{name}微专业课程", f"{name}微专业课程表"], ["课程", "课程设置", "学时", "学分"],
          ev_src=course_src)
    point("advantage", f"{name}微专业课程优势", advantage,
          [f"{name}微专业优势"], ["优势", "特色"]) if advantage else None

    for i, c in enumerate(courses, 1):
        items.append({
            **base, "id": f"wzy26-{slug}-c{i:02d}",
            "title": f"《{c['name']}》· {name}微专业课程",
            "aliases": [c["name"], f"{c['name']}课程", f"{name}微专业 {c['name']}"],
            "keywords": ["微专业", name, c["name"], "课程", "学分", "学时"],
            "kind": "paragraph", "para": True,
            "answer": c["text"],
            "note": f"表格列：序号 课程名称 学分 学时 授课教师 课程性质；本行：{c['credits']} 学分 / {c['hours']} 学时 / {c['teacher'] or '未列'} / {c['nature']}。",
            "evidence": {"answer": {"src": course_src, "quote": c["text"]}},
        })

    for i, d in enumerate(descs, 1):
        if not d["text"]:
            continue
        items.append({
            **base, "id": f"wzy26-{slug}-d{i:02d}",
            "title": f"《{d['name']}》课程简介 · {name}微专业",
            "aliases": [f"{d['name']}课程简介", f"{name}微专业 {d['name']}课程简介"],
            "keywords": ["微专业", name, d["name"], "课程简介", "课程内容"],
            "kind": "paragraph", "para": True,
            "answer": d["text"],
            "evidence": {"answer": {"src": src, "quote": d["text"]}},
        })

    stats = {"name": name, "college": college, "steps": len(steps), "courses": len(courses),
             "descs": len(descs), "qrs": len(qrs), "fee": fee_value, "items": len(items)}
    return items, stats


def enrich_general(data: dict) -> str:
    """总览条目补上 11 个专业清单、11 份简章 PDF 链接、报名二维码与报名入口说明。"""
    page_txt = (ROOT / "sources" / "crawl" / "20260724-c6479a272951.txt").read_text(encoding="utf-8")
    src = "20260724-c6479a272951"
    item = next((i for i in data["items"] if i["id"] == GEN_ID), None)
    if item is None:
        return "总览条目不存在"
    meta = json.loads((SRC / "wzy-2026-index.json").read_text(encoding="utf-8"))
    names = [m["title"].replace("中国传媒大学2026年秋季", "").replace("微专业招生简章", "") for m in meta]
    lines = [ln.strip() for ln in page_txt.splitlines() if ln.strip()]
    # 表格 4 列，部分行缺「招生对像」；用专业名清单当锚点，避免行列串位
    rows: list[dict] = []
    try:
        i = lines.index("微专业名称") + 1
    except ValueError:
        i = 0
    while i + 2 < len(lines) and not lines[i].startswith("[附件]"):
        name, college, span = lines[i], lines[i + 1], lines[i + 2]
        if not college.endswith("院") or span not in ("半年", "一年"):
            i += 1
            continue
        target = ""
        if i + 3 < len(lines) and not lines[i + 3].endswith("院") \
                and lines[i + 3] not in ("半年", "一年") \
                and lines[i + 3] not in names and not lines[i + 3].startswith("[附件]"):
            target = lines[i + 3]
            i += 4
        else:
            i += 3
        rows.append({"name": name, "college": college, "span": span, "target": target})
    steps = []
    ev = item.setdefault("evidence", {})
    for n, r in enumerate(rows):
        text = f"{r['name']}｜{r['college']}｜{r['span']}" + (f"｜{r['target']}" if r["target"] else "")
        steps.append({"when": f"专业 {n + 1}", "what": text})
        ev[f"steps.{n}"] = {"src": src, "quote": r["name"] + r["college"] + r["span"] + r["target"]}
    item["steps"] = steps
    item["answer"] = "我校将于2026年秋季学期开设11个微专业，即日起开始招生，欢迎各位同学咨询报名。"
    ev["answer"] = {"src": src, "quote": item["answer"]}
    item["aliases"] = list(dict.fromkeys([
        *(item.get("aliases") or []),
        "微专业", "微专业招生", "微专业报名", "微专业怎么报名", "微专业有哪些",
        "微专业招生简章", "2026年秋季微专业", "2026年秋季微专业招生",
    ]))
    item["keywords"] = list(dict.fromkeys([*(item.get("keywords") or []),
                                           "微专业", "报名", "招生", "简章", "二维码"]))
    item["qr"] = [{"label": "身份验证二维码（本校报名报错时先扫这个）",
                   "src": "/qr/wzy-2026/verify.png"}]
    item["pdf"] = [{"title": m["title"], "url": m["url"]} for m in meta]
    item["note"] = ("本校同学若扫码报名报错，先扫身份验证二维码；通过后回到本页扫原报名二维码。"
                    "11 个专业各自的招生简章 PDF、报名二维码、课程表、学费都单独成条，"
                    "直接问专业名（如「数智品牌传播微专业」）即可。")
    item.pop("slot_hint", None)
    return f"总览条目补入 {len(rows)} 个专业"


def main() -> None:
    dry = "--dry" in sys.argv
    meta = json.loads((SRC / "wzy-2026-index.json").read_text(encoding="utf-8"))
    all_new: list[dict] = []
    stats = []
    texts: dict[str, str] = {}
    fails: list[str] = []
    for m in meta:
        items, st = build_one(m)
        all_new.extend(items)
        stats.append(st)
        texts[m["slug"]] = squash((SRC / f"{m['slug']}.txt").read_text(encoding="utf-8"))
        alt = SRC / f"{m['slug']}-table.txt"
        if alt.exists():
            texts[alt.stem] = squash(alt.read_text(encoding="utf-8"))

    for it in all_new:
        for key, one in (it.get("evidence") or {}).items():
            group = one.get("sources") if isinstance(one, dict) and "sources" in one else [one]
            for single in group:
                quote = squash(single.get("quote", ""))
                if not quote or quote not in texts.get(single.get("src", ""), ""):
                    fails.append(f"{it['id']} {key} 引文对不上：{single.get('quote','')[:40]}")

    for st in stats:
        print(f"{st['name']:<18} {st['college']:<12} 步骤{st['steps']} 课程{st['courses']:>2} "
              f"简介{st['descs']:>2} 二维码{st['qrs']} {st['fee']:<22} 条目{st['items']}")
    print(f"新条目合计 {len(all_new)}，引文失败 {len(fails)}")
    for f in fails[:20]:
        print("  ✗", f)
    if dry or fails:
        return

    path = ROOT / "items.json"
    data = json.loads(path.read_text(encoding="utf-8"))
    by_id = {i["id"]: n for n, i in enumerate(data["items"])}
    added = updated = 0
    for it in all_new:
        if it["id"] in by_id:
            data["items"][by_id[it["id"]]] = it
            updated += 1
        else:
            data["items"].append(it)
            added += 1
    print(enrich_general(data))
    data["updated"] = CHECKED
    path.write_text(json.dumps(data, ensure_ascii=False, indent=1), encoding="utf-8")
    print(f"写入 items.json：新增 {added}，更新 {updated}，总计 {len(data['items'])}")


if __name__ == "__main__":
    main()
