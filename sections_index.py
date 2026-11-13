"""章节索引：把「条目 → 它在哪份文档的哪一节」读进来，给检索打分用。

只读 `_review_items/sections/*.json`，进程内缓存；目录里文件变了自动重载。
不联网、不调模型——所有判断都是确定的字符串匹配。

对外 API（与检索接入任务书 §1.1 一致）：

    enabled()            -> bool          环境变量 SECTIONS_BOOST=0/1，默认 1
    reload()             -> None          强制重载（测试用）
    section_of(item_id)  -> list[dict]    [{slug, no, heading, lines}]
    section_text(slug, lines) -> str      这一节的原文（去硬换行），给节检索腿当引文
    boost(qn, item)      -> int           0..MAX_BONUS，纯字符串匹配
    stats()              -> dict          {docs, sections, items_mapped, built}

两条硬约束（改动前先读）：

1. **有节就加分、没节不影响**。`boost()` 查不到节一律返回 0，所以一篇章节索引都
   没有时分数与接入前逐字节相同。全库 3.9 万条条目里只有几百条落到节上——这不是
   缺陷，是当前覆盖面；② 必须能这么降级。
2. **节是「这一节讲什么」，不是全局关键词**。加分只在这一节自己的标题、同文档兄弟
   节的标题、或用户明说的章/节/条号被点中时发生；不做正文匹配——那样 `总则`、
   `附则` 这类文书骨架词会把每一篇都点亮。

`sections/*.json` 的口径见 `tools/sections_check.py`：
`{key,title,truncated,sections[{no,heading,heading_kind,lines,items,chars}],items,notes}`，
其中 `lines` 是 `sources/<slug>.txt` 的 **1 起闭区间**。
"""
from __future__ import annotations

import json
import os
import re
import time
from datetime import datetime
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parent
SECDIR = ROOT / "_review_items" / "sections"

# 加分档位（任务书 §1.1.2）
MAX_BONUS = 15
BONUS_HEADING = 12      # 问句点了这一节自己的名字
BONUS_SIBLING = 5       # 问句点的是同一文档里的另一节（同章内联想）
BONUS_NUMBERED = 15     # 问句明说了「第X章 / 第X节 / 第X条」且对得上

# 这些节名是文书骨架，不是「这一节讲什么」：点中它们不能说明问的就是这一节
GENERIC_HEADINGS = {
    "总则", "附则", "通知", "标题", "版记", "附件", "引言", "目录", "前言", "正文",
    "落款", "印发通知", "印发版记", "文头与印发通知", "标题与引言", "附表", "附件清单",
}
# 同一个节名在这么多份文档里都出现，就说明它标识不了「哪一份」——按通用词处理。
# 实测「申请条件」「适用范围」「联系方式」都是这类；「第八条 三类招生类型的转入限制」
# 这种只属于一份文件，才会留下。
HEADING_DF_MAX = 2
# 节名太短就不是「这一节讲什么」，而是一个通用名词：「图书馆」「校园卡」会出现在
# 任何一句提到它的问句里。实测「图书馆能续借吗」被两篇新生手册的「图书馆」一节
# 各加 12 分顶掉了 lib-jieyue。四字起才当标题用（任务书写 2 字，在真实索引上太松）。
MIN_HEADING = 4

PUNCT = re.compile(r"[^0-9a-z\u4e00-\u9fff]+")
# 原始标题上的编号前缀：「第一章」「一、」「（一）」「1.」
LEAD_NO = re.compile(
    r"^(?:第[一二三四五六七八九十百零〇\d]+[章节条款编篇]"
    r"|[一二三四五六七八九十百]+[、.．]"
    r"|[（(][一二三四五六七八九十百\d]+[）)]"
    r"|\d+[、.．])"
)
# 问句里的「第X章 / 第X节 / 第X条」
CHAP_Q = re.compile(r"第([一二三四五六七八九十百零〇\d]+)(章|节|条|编|篇|款)")
# 索引里的 no：「第一章」「第三条」「第三条·二」（「一、」「三（一）」不带「第」，不参与章号匹配）
SEC_NO = re.compile(
    r"^第([一二三四五六七八九十百零〇\d]+)(章|节|条|编|篇|款)"
    r"(?:[·.．][一二三四五六七八九十百零〇\d]+)?$"
)

_CN = "零一二三四五六七八九"
_CN_UNIT = {"十": 10, "百": 100}


def _cn2int(s: str) -> int | None:
    """「三」「十二」「二十一」「3」→ int；认不出返回 None。"""
    s = (s or "").strip()
    if not s:
        return None
    if s.isdigit():
        return int(s)
    total = 0
    cur = 0
    for ch in s:
        if ch in _CN:
            cur = _CN.index(ch)
        elif ch in _CN_UNIT:
            total += (cur or 1) * _CN_UNIT[ch]
            cur = 0
        else:
            return None
    return total + cur


def _norm_heading(h: str) -> str:
    """节标题的匹配形：先在原始形态上去编号前缀，再只留字。"""
    s = LEAD_NO.sub("", (h or "").strip().lower(), count=1)
    return PUNCT.sub("", s)


def enabled() -> bool:
    """② 的总开关。默认开；`SECTIONS_BOOST=0` 时 rank() 走原路径。"""
    return str(os.environ.get("SECTIONS_BOOST", "1")).strip().lower() not in ("0", "false", "off", "no")


# ---------------------------------------------------------------- 缓存与加载

_STATE: dict[str, Any] | None = None
_CHECK_EVERY = 1.0          # 秒：mtime 检查的节流（sections/ 可能正被批量标注写入）
_PREP: dict[str, Any] = {}
_PREP_MAX = 8


def _signature() -> tuple[int, float]:
    n = 0
    mx = 0.0
    try:
        with os.scandir(SECDIR) as it:
            for e in it:
                name = e.name
                if name.startswith("_") or not name.endswith(".json"):
                    continue
                try:
                    m = e.stat().st_mtime
                except OSError:
                    continue
                n += 1
                if m > mx:
                    mx = m
    except OSError:
        return (0, 0.0)
    return (n, mx)


def _load_state() -> dict[str, Any] | None:
    if not SECDIR.is_dir():
        return None
    docs: dict[str, dict[str, Any]] = {}
    sections: list[dict[str, Any]] = []
    item2sec: dict[str, list[int]] = {}
    doc2secs: dict[str, list[int]] = {}
    doc_items: dict[str, list[str]] = {}
    bad: list[str] = []

    for p in sorted(SECDIR.glob("*.json")):
        if p.name.startswith("_"):
            continue
        try:
            d = json.loads(p.read_text(encoding="utf-8"))
        except (OSError, ValueError):
            bad.append(p.stem)
            continue
        if not isinstance(d, dict):
            bad.append(p.stem)
            continue
        slug = str(d.get("key") or p.stem)
        secs = d.get("sections")
        if not isinstance(secs, list):
            continue
        docs[slug] = {
            "title": str(d.get("title") or ""),
            "truncated": bool(d.get("truncated")),
        }
        doc_items[slug] = [str(x) for x in (d.get("items") or [])]
        bucket = doc2secs.setdefault(slug, [])
        for s in secs:
            if not isinstance(s, dict):
                continue
            lines = s.get("lines") or [0, 0]
            try:
                a, b = int(lines[0]), int(lines[1])
            except (TypeError, ValueError, IndexError):
                a, b = 0, 0
            i = len(sections)
            items = [str(x) for x in (s.get("items") or [])]
            sections.append({
                "slug": slug,
                "no": str(s.get("no") or ""),
                "heading": str(s.get("heading") or ""),
                "hn": _norm_heading(str(s.get("heading") or "")),
                "lines": [a, b],
                "items": items,
            })
            bucket.append(i)
            for iid in items:
                item2sec.setdefault(iid, []).append(i)

    # 文档级 items 里没落进任何节的：留着，boost() 时按引文行号反查（今天这批是 0 条）
    doc_only: dict[str, list[str]] = {}
    for slug, ids in doc_items.items():
        rest = [i for i in ids if i not in item2sec]
        if rest:
            doc_only[slug] = rest

    # 节名的「文档频次」：跨多少份文档出现过。出现太多次的通用词不当信号。
    hn_docs: dict[str, set[str]] = {}
    for s in sections:
        if s["hn"]:
            hn_docs.setdefault(s["hn"], set()).add(s["slug"])
    shared = {h for h, docs_ in hn_docs.items() if len(docs_) >= HEADING_DF_MAX}

    # 「第X章/节/条」→ 节下标：问句明说条号时直接查，不必扫全库
    by_no: dict[tuple[str, int], list[int]] = {}
    for i, s in enumerate(sections):
        m = SEC_NO.match(s["no"])
        if m:
            n = _cn2int(m.group(1))
            if n is not None:
                by_no.setdefault((m.group(2), n), []).append(i)
    # 横跨多节的条目：锚定不到某一节，只配拿兄弟节档位
    multi = {iid for iid, lst in item2sec.items() if len(lst) > 1}

    return {
        "docs": docs,
        "sections": sections,
        "item2sec": item2sec,
        "doc2secs": doc2secs,
        "doc_only": doc_only,
        "bad": bad,
        "shared": shared,
        "by_no": by_no,
        "multi": multi,
        "texts": {},        # slug -> 该文档的原文行（懒加载，只给 doc_only 反查用）
    }


def _ensure(force: bool = False) -> dict[str, Any] | None:
    global _STATE
    now = time.monotonic()
    if _STATE is not None and not force and now - _STATE.get("checked", 0.0) < _CHECK_EVERY:
        return _STATE
    sig = _signature()
    if force or _STATE is None or sig != _STATE.get("sig"):
        st = _load_state()
        _PREP.clear()
        if st is None:
            _STATE = None
            return None
        st["sig"] = sig
        st["checked"] = now
        _STATE = st
    else:
        _STATE["checked"] = now
    return _STATE


def reload() -> None:
    """强制重载（测试 / 批量标注跑完时用）。"""
    global _STATE
    _STATE = None
    _PREP.clear()
    _SEC_TEXT_CACHE.clear()
    _ensure(force=True)


# ---------------------------------------------------------------- 查询期准备

def _prep(qn: str) -> tuple[dict[str, int], set[int], set[str], list[tuple[str, int]]]:
    """一次问句只算一遍：摊成「条目 id → 加分」的表 + 点中的节/文档 + 章号。

    为什么不能每条都算：全库 3.9 万条、已经落到节上的有 2 万多条，rank() 会调
    boost() 3.9 万次；逐条查节、扫兄弟节会多出 160 ms。摊成表之后每趟 rank() 只
    算一次（O(被点中的节数)），实测 p95 增量从 +162 ms 降到 +2 ms 量级。

    `qn` 用调用方传进来的归一形做键（同一趟 rank() 里同一个问题）。
    """
    hit = _PREP.get(qn)
    if hit is not None:
        return hit
    st = _ensure()
    if st is None:
        return ({}, set(), set(), [])
    q = PUNCT.sub("", str(qn or "").lower())
    own: set[int] = set()
    doc_hit: set[str] = set()
    if q:
        shared = st["shared"]
        for i, s in enumerate(st["sections"]):
            hn = s["hn"]
            if len(hn) < MIN_HEADING or hn in GENERIC_HEADINGS or hn in shared:
                continue
            if hn in q:
                own.add(i)
                doc_hit.add(s["slug"])
    chap: list[tuple[str, int]] = []
    for m in CHAP_Q.finditer(q):
        n = _cn2int(m.group(1))
        if n is not None:
            chap.append((m.group(2), n))

    sections = st["sections"]
    bonus: dict[str, int] = {}

    def put(i: int, val: int) -> None:
        for iid in sections[i]["items"]:
            if val > bonus.get(iid, 0):
                bonus[iid] = val

    for i in own:
        put(i, BONUS_HEADING)
    for slug in doc_hit:
        # 点中的是同文档里另一节：只给兄弟节档位
        for i in st["doc2secs"].get(slug, ()):
            if i not in own:
                put(i, BONUS_SIBLING)
    for key in chap:
        for i in st["by_no"].get(key, ()):
            put(i, BONUS_NUMBERED)
    # 横跨多节的条目锚定不到某一节，封顶到兄弟节档位
    multi = st["multi"]
    for iid, val in bonus.items():
        if val > BONUS_SIBLING and iid in multi:
            bonus[iid] = BONUS_SIBLING

    if len(_PREP) >= _PREP_MAX:
        _PREP.pop(next(iter(_PREP)))
    out = (bonus, own, doc_hit, chap)
    _PREP[qn] = out
    return out


def _quote_lines(st: dict[str, Any], slug: str) -> list[str]:
    """懒读 sources/<slug>.txt 的行（只给 doc_only 反查用，不常走这条路）。"""
    cache = st["texts"]
    if slug in cache:
        return cache[slug]
    lines: list[str] = []
    for d in ("", "pdf", "huibian", "wendao-text", "wechat", "crawl", "cdp", "local",
              "attachments/text", "ilib-text", "ilib-list-text", "wendao-extra",
              "chsi", "moe", "national", "extra"):
        p = (ROOT / "sources" / d / f"{slug}.txt") if d else (ROOT / "sources" / f"{slug}.txt")
        if p.exists():
            try:
                lines = p.read_text(encoding="utf-8", errors="ignore").split("\n")
            except OSError:
                lines = []
            break
    cache[slug] = lines
    return lines


def _item_quotes(item: dict[str, Any]) -> list[str]:
    """条目证据里的引文（去空白后前 26 字），与 tools/sections_check.py 同口径。"""
    ev = (item.get("evidence") or {}).get("answer") or {}
    raw: list[str] = []
    if isinstance(ev, dict):
        if ev.get("quote"):
            raw.append(str(ev["quote"]))
        srcs = ev.get("sources") or []
        if isinstance(srcs, dict):
            srcs = [srcs]
        for s in srcs:
            if isinstance(s, dict) and s.get("quote"):
                raw.append(str(s["quote"]))
    return [re.sub(r"\s+", "", q)[:26] for q in raw if q]


def _sections_for(st: dict[str, Any], item_id: str, item: dict[str, Any] | None) -> list[int]:
    """条目 → 节下标。先查 sections[].items；查不到再按文档级 items + 引文行号反查。"""
    got = st["item2sec"].get(item_id)
    if got:
        return got
    doc_only = st["doc_only"]
    if not doc_only or not isinstance(item, dict):
        return []
    quotes = _item_quotes(item)
    if not quotes:
        return []
    out: list[int] = []
    for slug, ids in doc_only.items():
        if item_id not in ids:
            continue
        lines = _quote_lines(st, slug)
        if not lines:
            continue
        flat = [re.sub(r"\s+", "", x) for x in lines]
        for i in st["doc2secs"].get(slug, []):
            sec = st["sections"][i]
            a, b = sec["lines"]
            if not (1 <= a <= b <= len(flat)):
                continue
            blob = "".join(flat[a - 1:b])
            if any(q in blob for q in quotes):
                out.append(i)
    return out


# ---------------------------------------------------------------- 对外

def section_of(item_id: str, item: dict[str, Any] | None = None) -> list[dict[str, Any]]:
    """这个条目落在哪些节：`[{slug, no, heading, lines}]`；没落节返回 []。"""
    st = _ensure()
    if st is None or not item_id:
        return []
    out = []
    for i in _sections_for(st, str(item_id), item):
        s = st["sections"][i]
        out.append({"slug": s["slug"], "no": s["no"], "heading": s["heading"], "lines": s["lines"]})
    return out


# 纯页码行：「- 244 -」「2」「- 7-」。节区间里夹着的页码不是正文，进了引文会脏。
PAGE_ONLY = re.compile(r"^-?\s*\d{1,3}\s*-?$")
# 条/项起点：「第六条」「第三章」「（一）」「(2)」「1.」「3、」。
# 只在它们前面换行——这是「条界/项界」，不是逐句拆行：句内的。；仍同一行。
ITEM_START = re.compile(
    r"^(?:第[一二三四五六七八九十百零〇\d]+[章节条款编篇]"
    r"|[（(][一二三四五六七八九十百\d]+[）)]"
    r"|\d+[、.．])"
)
TRUNC_MARK = "……（本节较长，已截取，未见全文）"
_SEC_TEXT_CACHE: dict[tuple[str, int, int, int], str] = {}
_SEC_TEXT_MAX = 64


def section_text(slug: str, lines: list[int], max_chars: int = 1200) -> str:
    """把某节的行区间从 sources/<slug>.txt 切出来，保留条界，返回可读原文。

    给「节检索腿」当引文用：向量命中的是节，能直接进证据的必须是原文——
    节 chunk 的 text 是 heading + 正文且被截到 TARGET（520 字），拿来当引文会带进小标题、
    也可能与 lines 对不上；这里按索引里的行区间重新切，口径与 sections JSON 同源。

    **为什么保留 `\n`（v3）**：v2 把整节拼成一整段（316 字的第三章没有一处断行），
    模型读不出「第三章 = 第六条 + 第七条 + 第八条」，于是把第八条当成整章的内容。
    现在只在条/项起点前断行（`ITEM_START`），句内不拆——PDF 的硬折行照样被接回去，
    但「第七条」「（一）（二）」各自起行，穷举了几项一眼能数。

    **截断要说出来**：超过 `max_chars` 时截断并追加 `TRUNC_MARK`。菜单按 `"已截取" in txt`
    给这一条标【节选】，合成器不许对节选的节断言「没有规定」。
    """
    st = _ensure()
    if st is None:
        return ""
    try:
        a, b = int(lines[0]), int(lines[1])
    except (TypeError, ValueError, IndexError):
        return ""
    if a < 1 or b < a:      # [0, 0] 这种占位区间不该被当成「第一节」
        return ""
    key = (slug, a, b, max_chars)
    hit = _SEC_TEXT_CACHE.get(key)
    if hit is not None:
        return hit
    src = _quote_lines(st, slug)
    if not src:
        return ""
    a = max(1, min(a, len(src)))
    b = max(a, min(b, len(src)))
    parts: list[str] = []
    for line in src[a - 1:b]:
        s = line.strip()
        if not s or PAGE_ONLY.match(s):
            continue
        s = re.sub(r"[ \t]+", "", s)
        if parts and ITEM_START.match(s):
            parts.append("\n")
        parts.append(s)
    txt = "".join(parts)
    if len(txt) > max_chars:
        txt = txt[:max_chars] + TRUNC_MARK
    if len(_SEC_TEXT_CACHE) >= _SEC_TEXT_MAX:
        _SEC_TEXT_CACHE.pop(next(iter(_SEC_TEXT_CACHE)))
    _SEC_TEXT_CACHE[key] = txt
    return txt


def section_outline(slug: str, lines: list[int], max_items: int = 12) -> str:
    """章/节范围内各子节的 `no + heading`，用「；」连接；没有子节返回 ""。

    这是「章级题答案漂移」的根因修复：只有整章原文时，模型得自己从 316 字里猜
    「哪些是禁止情形」；把「第六条 申请条件；第七条 原则上不得申请…；第八条 三类…」
    直接摆出来，它就不必猜（仍是原文的节名，不是新造的摘要）。

    三条口径：
      · 只收**真被 `[a,b]` 包住**的节（`a <= la and lb <= b`），区间相同的自身不算子节；
      · 按行号排序，避免 `sections` 列表顺序（文件内顺序）与正文顺序不一致；
      · 最多 `max_items` 条，超出补「…等N条」，N 是子节总数。
    """
    st = _ensure()
    if st is None:
        return ""
    try:
        a, b = int(lines[0]), int(lines[1])
    except (TypeError, ValueError, IndexError):
        return ""
    if a < 1 or b < a:
        return ""
    got: list[tuple[int, int, str]] = []
    seen: set[tuple[str, str]] = set()
    for s in st["sections"]:
        if s["slug"] != slug:
            continue
        la, lb = s["lines"]
        if (la, lb) == (a, b):
            continue
        if not (a <= la and lb <= b):
            continue
        if (s["no"], s["heading"]) in seen:
            continue
        seen.add((s["no"], s["heading"]))
        got.append((la, lb, s["no"] + "\0" + s["heading"]))
    if not got:
        return ""
    got.sort()
    names: list[str] = []
    for _la, _lb, blob in got[:max_items]:
        no, heading = blob.split("\0", 1)
        h = heading or ""
        if no and h.startswith(no):
            h = h[len(no):].strip()
        lab = f"{no} {h}".strip() if no else h
        if lab:
            names.append(lab)
    if not names:
        return ""
    out = "；".join(names)
    if len(got) > max_items:
        out += f"…等{len(got)}条"
    return out



def bonus_map(qn: str) -> dict[str, int]:
    """批量接口：一次问句的「条目 id → 加分」表（没有节被点中时返回 {}）。

    给 `app.rank()` 用：3.9 万条条目逐条调 `boost()` 要花 68 ms（函数调用 + 参数
    打包），摊成表之后整个 rank() 只多 8 ms 量级。逐条查用 `boost()`，两者口径相同。
    """
    if not qn:
        return {}
    return _prep(qn)[0]


def boost(qn: str, item: dict[str, Any] | None) -> int:
    """② 的加分：0..MAX_BONUS。查不到节 → 0（完全等价于没接这一层）。

    热路径：一次 rank() 会调 3.9 万次，所以按问句把「条目 → 加分」摊成一张表
    （见 `_prep`），这里只剩一次字典查 + 时间节流检查。
    """
    if not qn or not isinstance(item, dict):
        return 0
    st = _STATE
    if st is None or time.monotonic() - st.get("checked", 0.0) >= _CHECK_EVERY:
        st = _ensure()
        if st is None:
            return 0
    bonus = _prep(qn)[0]
    if not bonus:
        return 0
    iid = str(item.get("id") or "")
    got = bonus.get(iid)
    if got is not None:
        return got
    # 文档级 items 里没落进任何节的那几条（今天 4 条）：按引文行号反查
    if st["doc_only"]:
        return _doc_only_boost(st, qn, iid, item)
    return 0


def _doc_only_boost(st: dict[str, Any], qn: str, iid: str,
                    item: dict[str, Any] | None) -> int:
    """兜底路径：极少数只挂在文档级 items 上的条目，按引文落在哪一节反查。"""
    if not iid or iid not in bonus_ids(st):
        return 0
    idxs = _sections_for(st, iid, item)
    if not idxs:
        return 0
    _bonus, own, doc_hit, chap = _prep(qn)
    best = 0
    for i in idxs:
        s = st["sections"][i]
        if i in own:
            best = max(best, BONUS_HEADING)
        elif s["slug"] in doc_hit:
            best = max(best, BONUS_SIBLING)
        if chap:
            m = SEC_NO.match(s["no"])
            if m:
                num = _cn2int(m.group(1))
                if num is not None and (m.group(2), num) in chap:
                    best = max(best, BONUS_NUMBERED)
    return min(best, MAX_BONUS if len(idxs) == 1 else BONUS_SIBLING)


def bonus_ids(st: dict[str, Any]) -> set[str]:
    """文档级 items 里没落进任何节的那几条 item id（用来判断要不要走兜底）。"""
    cache = st.get("_doc_only_ids")
    if cache is None:
        cache = {iid for ids in st["doc_only"].values() for iid in ids}
        st["_doc_only_ids"] = cache
    return cache


def stats() -> dict[str, Any]:
    """索引体量：{docs, sections, items_mapped, built, ...}；没索引时返回 {}。"""
    st = _ensure()
    if st is None:
        return {}
    mx = st.get("sig", (0, 0.0))[1]
    return {
        "docs": len(st["docs"]),
        "sections": len(st["sections"]),
        "items_mapped": len(st["item2sec"]),
        "doc_only_items": sum(len(v) for v in st["doc_only"].values()),
        "truncated_docs": sum(1 for d in st["docs"].values() if d["truncated"]),
        "built": datetime.fromtimestamp(mx).isoformat(timespec="minutes") if mx else "",
        "bad_files": list(st["bad"]),
    }
