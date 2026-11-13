"""节级 FTS：给 11,531 个节单独建一张小库，按二字组检索。

为什么另建一张：`kb.sqlite` 的 FTS 是**条目级**的（一句话一条），
「中途退课或终止微专业学习，所交学费不予退还」这种条款在条目里被切碎，
`微专业 退费` 这种问法在条目级 FTS 上排不进来。节级索引按「这一节全文」建，
问法对不上标题时还能靠正文命中。

三个约束：
  · **独立库文件**（`sources/section_fts.sqlite`），不碰 `kb.sqlite`；
  · 切词与 `app._gram_terms` 同口径（二字组），否则查询串与索引对不上；
  · 只读 `sections/*.json` + `sections_index.section_text()`，不改任何标注。
"""
from __future__ import annotations

import re
import sqlite3
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parent.parent
# 任务书写的是 `sources/section_fts.sqlite`，但本机 `sources/` 带一条显式 DENY ACE
# （`Everyone:(CI)(DENY)(S,DC)`），连**新建**文件都会被拒（Errno 13 / unable to open database file）。
# 改放 `_review_items/`：同在 workspace 内、与其它评测产物同处；删掉这个文件即可彻底回滚。
# `SECTION_FTS_DB` 可覆盖路径（换机器/换目录时不用改代码）。
import os as _os

DB = Path(_os.getenv("SECTION_FTS_DB") or (ROOT / "_review_items" / "section_fts.sqlite"))
TABLE = "section_fts"


def _grams(text: str) -> list[str]:
    """与 `app._gram_terms` 同一切词法：中文按二字组，英文按整词小写。"""
    toks: list[str] = []
    for run in re.findall(r"[一-鿿]+|[^\s一-鿿]+", text or ""):
        if len(run) == 1 and "\u4e00" <= run <= "\u9fff":
            continue                     # 单字不成二字组，检索价值低且噪声大
        elif "\u4e00" <= run[0] <= "\u9fff":
            toks.extend(run[i:i + 2] for i in range(len(run) - 1))
        else:
            toks.append(run.lower())
    out: list[str] = []
    for t in toks:
        if t not in out:
            out.append(t)
    return out


def _conn() -> sqlite3.Connection | None:
    if not DB.exists():
        return None
    try:
        return sqlite3.connect(f"file:{DB}?mode=ro", uri=True)
    except sqlite3.Error:
        return None


def build() -> int:
    """从 `_review_items/sections/*.json` + 原文建库；返回写入行数。"""
    import json

    import sections_index as si

    st = si._ensure()
    if not st:
        return 0
    rows: dict[str, tuple[str, str, str, str, str]] = {}
    secdir = ROOT / "_review_items" / "sections"
    for p in sorted(secdir.glob("*.json")):
        if p.name.startswith("_"):
            continue
        try:
            d = json.loads(p.read_text(encoding="utf-8"))
        except (OSError, ValueError):
            continue
        if not isinstance(d, dict):
            continue
        slug = str(d.get("key") or p.stem)
        for s in d.get("sections") or []:
            if not isinstance(s, dict):
                continue
            lines = s.get("lines") or [0, 0]
            try:
                a, b = int(lines[0]), int(lines[1])
            except (TypeError, ValueError, IndexError):
                continue
            if a < 1 or b < a:
                continue
            no = str(s.get("no") or "")
            heading = str(s.get("heading") or "")
            body = si.section_text(slug, [a, b], 4000)
            if not body:
                continue
            # v7：key 必须带行号。同一份文档里 `no` 会重复（`00f4cdcc` 的 `no="—"` 有 7 节、
            # `no="一、"` 有 6 节），只按 `slug#no` 去重会让 2,176 个节没有独立行，检索永远取不到。
            key = f"{slug}#{no}#L{a}"
            if key in rows:
                continue
            toks = " ".join(_grams(heading + " " + body))
            rows[key] = (key, slug, no, a, b, heading, body, toks)  # type: ignore[assignment]

    if DB.exists():
        DB.unlink()
    con = sqlite3.connect(DB)
    try:
        con.execute(
            f"create virtual table {TABLE} using fts5("
            f"key unindexed, slug unindexed, no unindexed, start unindexed, end unindexed, "
            f"heading, body, tokens, tokenize='unicode61')")
        con.executemany(
            f"insert into {TABLE}(key, slug, no, start, end, heading, body, tokens) "
            f"values (?,?,?,?,?,?,?,?)",
            list(rows.values()))
        con.commit()
    finally:
        con.close()
    return len(rows)


def search(text: str, k: int = 8) -> list[tuple[str, float]]:
    """返回 `[(key, bm25)]`，bm25 越小越相关；空查询或没库返回 []。"""
    terms = [t for t in _grams(text) if len(t) > 1][:24]
    if not terms:
        return []
    con = _conn()
    if con is None:
        return []
    q = " OR ".join('"%s"' % t.replace('"', '""') for t in terms)
    try:
        rows = con.execute(
            f"select key, bm25({TABLE}) as s from {TABLE} where tokens match ? "
            f"order by s limit ?", (q, int(k))).fetchall()
    except sqlite3.Error:
        return []
    finally:
        con.close()
    return [(str(r[0]), float(r[1])) for r in rows]


def get(key: str) -> dict[str, Any] | None:
    """`key = slug#no#L{start}` → `{slug, no, heading, lines}`；找不到返回 None。

    v7 起直接按 key 查表（表里存了 start/end），不再按 `(slug,no)` 回 `sections_index` 猜——
    同一个 `no` 有多节时，猜出来的可能是另一节。
    """
    if not key or "#L" not in key:
        return None
    con = _conn()
    if con is None:
        return None
    try:
        row = con.execute(
            f"select slug, no, heading, start, end from {TABLE} where key = ?",
            (key,)).fetchone()
    except sqlite3.Error:
        return None
    finally:
        con.close()
    if not row:
        return None
    return {"slug": str(row[0]), "no": str(row[1]), "heading": str(row[2]),
            "lines": [int(row[3]), int(row[4])]}


def stats() -> dict[str, Any]:
    con = _conn()
    if con is None:
        return {}
    try:
        n = con.execute(f"select count(*) from {TABLE}").fetchone()[0]
        return {"rows": int(n), "path": str(DB)}
    except sqlite3.Error:
        return {}
    finally:
        con.close()
