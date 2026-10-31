"""581 题全量复核：每题跑现行代码，把路由、答复内容、残留标点压成一行。

输出 _review581.tsv：组别 | 问题 | 状态 | 命中条目 | 答复面 | 答复摘要 | 备注
状态 OK / ASK（反问）/ MISS（未命中）/ EMPTY（有命中但答复为空）/ BANNED（正文残留禁用标点）
_detail 文件给出被标记题目的完整答复，供逐题细看。
_full 文件给出全部题目的完整可见文字，供逐题通读。
"""
from __future__ import annotations

import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "tools"))

import app  # noqa: E402
from audit_common_20261030 import load_bank  # noqa: E402

BAD = {
    "“": "左双引号", "”": "右双引号", "‘": "左单引号", "’": "右单引号",
    '"': "直双引号", "'": "直单引号", "「": "直角引号", "」": "直角引号",
    "『": "双直角引号", "』": "双直角引号",
    "—": "破折号", "–": "短破折号", "―": "破折号",
    "：": "冒号", ":": "ASCII 冒号",
    "。": "句号", "*": "星号", "#": "井号",
    "…": "省略号",
}

TONE = (
    "值得注意的是", "总而言之",
    "表面看是", "归根结底", "往深了说", "说到这", "你发现没", "说来有趣",
    "这条我认", "这流程我熟", "我理解你的痛苦", "我理解你的焦虑",
    "你不是一个人", "按照这个方案", "马上去行动", "而不是",
    "然而", "与其说", "不如说", "凑齐了", "你这是把", "说白了", "简单来说",
    "换句话说", "总的来说", "需要说明的是", "值得一提的是",
)
ENUM = ("首先", "其次", "再次", "最后", "此外", "另外", "综上")


def tone_hits(s: str) -> list[str]:
    """_display_text 之后还残留的模型腔与转折套话；枚举词只算句首带分隔符的用法。"""
    hits = [w for w in TONE if w in s]
    for m in re.finditer(r"(?:^|[。；！？\n])\s*(?:" + "|".join(ENUM) + r")\s*[，,：:；;]", s):
        hits.append(m.group(0).strip()[0:2])
    return hits


def visible_texts(resp: dict):
    for p in resp.get("answers") or []:
        if p.get("text"):
            yield "text." + str(p.get("focus")), p["text"]
        for s in p.get("steps") or []:
            if isinstance(s, dict):
                for k in ("what", "where", "when"):
                    if s.get(k):
                        yield "step", s[k]
            elif isinstance(s, str):
                yield "step", s
        for ln in p.get("lines") or []:
            if isinstance(ln, str):
                yield "line", ln
    for key in ("note", "clarify"):
        if isinstance(resp.get(key), str) and resp[key]:
            yield key, resp[key]
    for f in resp.get("followups") or []:
        if isinstance(f, str):
            yield "followup", f
        elif isinstance(f, dict):
            for k in ("text", "label", "q"):
                if f.get(k):
                    yield "followup", f[k]
    it = resp.get("item") or {}
    for key in ("title", "dept"):
        if isinstance(it.get(key), str) and it[key]:
            yield "item." + key, it[key]
    for key in ("title", "fee", "location", "hours", "duration", "window", "note", "answer"):
        if isinstance(it.get(key), str) and it[key]:
            yield "item." + key, it[key]
    for s in it.get("steps") or []:
        if isinstance(s, dict):
            for k in ("what", "where", "when"):
                if s.get(k):
                    yield "item.step", s[k]
    for m in it.get("materials") or []:
        if isinstance(m, str):
            yield "item.material", m
        elif m.get("name"):
            yield "item.material", m["name"]
    for p in it.get("pitfalls") or []:
        if isinstance(p, str):
            yield "item.pitfall", p
    for a in it.get("advisory") or []:
        if isinstance(a, str):
            yield "item.advisory", a
    for s in it.get("slots") or []:
        if isinstance(s, dict):
            for k in ("ask", "why"):
                if isinstance(s.get(k), str):
                    yield "item.slot", s[k]


def scan_bad(s: str):
    m = app._KEEP_RE.sub("□", s)
    out = []
    for i, ch in enumerate(m):
        if ch in BAD:
            out.append(f"{BAD[ch]}…{m[max(0, i - 10):i + 11]}")
    return out


def summary(resp: dict) -> str:
    bits = []
    for p in resp.get("answers") or []:
        if p.get("steps"):
            first = p["steps"][0]
            bits.append(str(first.get("what") if isinstance(first, dict) else first))
        elif p.get("lines"):
            first = p["lines"][0]
            bits.append(str(first.get("text") if isinstance(first, dict) else first))
        elif p.get("text"):
            bits.append(str(p["text"]))
    tmp = " ｜ ".join(b for b in bits if b)
    return re.sub(r"\s+", " ", tmp)


def main() -> None:
    rows = load_bank(None)
    out_rows = []
    detail = []
    full = []
    stats = {"OK": 0, "ASK": 0, "MISS": 0, "EMPTY": 0, "BANNED": 0, "TONE": 0}
    for group, q in rows:
        try:
            resp = app.clean_response(app.answer_question(q, {}, router_llm=False))
        except Exception as e:  # noqa: BLE001
            out_rows.append(f"{group}\t{q}\tEXC\t\t\t\t{repr(e)}")
            detail.append(f"### {q}\nEXC {repr(e)}\n")
            full.append(f"### [EXC] {q}\nEXC {repr(e)}")
            stats["EMPTY"] += 1
            continue
        it = resp.get("item") or {}
        title = it.get("title") or ""
        focus = "/".join(p.get("label") or p.get("focus") or "" for p in resp.get("answers") or [])
        note = resp.get("note") or ""
        clarify = resp.get("clarify") or ""
        fu = resp.get("followups") or []
        hits = []
        for where, t in visible_texts(resp):
            for b in scan_bad(t):
                hits.append(f"{where} {b}")
        hits = list(dict.fromkeys(hits))
        tones = []
        for where, t in visible_texts(resp):
            for b in tone_hits(t):
                tones.append(f"{where} {b}…{t[max(0, t.find(b) - 8):t.find(b) + len(b) + 12]}")
        tones = list(dict.fromkeys(tones))
        if not resp.get("matched"):
            status = "MISS"
        elif resp.get("disambiguate"):
            status = "ASK"
        elif hits:
            status = "BANNED"
        elif not resp.get("answers"):
            status = "EMPTY"
        else:
            status = "OK"
        stats[status] += 1
        stats["TONE"] += 1 if tones else 0
        flags = []
        if note:
            flags.append("note:" + note)
        if clarify:
            flags.append("clarify:" + clarify)
        if fu:
            flags.append("followups:" + "、".join(str((f or {}).get("question", f)) for f in fu))
        if tones:
            flags.append("tone:" + " || ".join(tones)[:200])
        ans = summary(resp)
        out_rows.append("\t".join([
            group, q, status, title, focus, ans[:260], " || ".join(flags)[:300],
        ]))
        body = [f"### [{status}] {q}  ->  {title}"]
        for p in resp.get("answers") or []:
            label = p.get("label") or p.get("focus") or ""
            if p.get("text"):
                body.append(f"- {label} | {p['text']}")
            for s in p.get("steps") or []:
                if isinstance(s, dict):
                    bits = [str(s.get(k) or "") for k in ("when", "what", "where")]
                    body.append("- · " + " | ".join(b for b in bits if b))
                else:
                    body.append(f"- · {s}")
            for ln in p.get("lines") or []:
                if isinstance(ln, dict):
                    body.append("- · " + str(ln.get("text") or ln.get("what") or ln))
                else:
                    body.append(f"- · {ln}")
        if hits:
            body.append("- BANNED: " + " || ".join(hits))
        if tones:
            body.append("- TONE: " + " || ".join(tones))
        if note:
            body.append("- note: " + note)
        if clarify:
            body.append("- clarify: " + clarify)
        if fu:
            body.append("- followups: " + "、".join(str((f or {}).get("question", f)) for f in fu))
        if resp.get("disambiguate"):
            body.append("- options: " + "、".join(
                f"{b.get('title')}({b.get('hint', '')})" for b in resp["disambiguate"]))
        full.append("\n".join(body))
        if status in ("ASK", "MISS", "EMPTY", "BANNED", "EXC") or not ans or tones:
            detail.append("\n".join(body))

    (ROOT / "_review581.tsv").write_text("\n".join(out_rows) + "\n", encoding="utf-8")
    (ROOT / "_review581_detail.txt").write_text("\n\n".join(detail) + "\n", encoding="utf-8")
    (ROOT / "_review581_full.txt").write_text("\n\n".join(full) + "\n", encoding="utf-8")
    print("questions", len(rows), json.dumps(stats, ensure_ascii=False))


if __name__ == "__main__":
    main()
