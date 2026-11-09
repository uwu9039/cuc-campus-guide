"""把 items.json + 流水线产物建成派生检索库 kb.sqlite（可反复重建，唯一真相仍是 items.json）。

用法：
    ./.venv/Scripts/python.exe tools/build_kb_db.py            # 重建
    ./.venv/Scripts/python.exe tools/build_kb_db.py --verify    # 只核对不重建
    ./.venv/Scripts/python.exe tools/build_kb_db.py --stage     # 把流水线产物落成随包的根目录 gz

表：
    doc        每份进过流水线的正文文件一行（条目数/行数/位图缺口）
    item       条目本体（含 archive_only，入库不等于抢路由）
    quote      逐字引文，一条一个区间，覆盖率按这张表算
    table_row  表格/阅读报告的可检索数据行
    registry   sources/ 下每一个文件的处置结论（含二进制与名单），「每个文件都有交代」的台账
    search     FTS5 虚表：中文按二元 gram 展开 + unicode61（2 字查询也能命中，trigram 不行）

前置：本机在 _review_items/ 里要有 v2_report.json、v2_table_rows.json、coverage_20261104.json，
      由 tools/build_items_v2.py --apply 与 tools/build_coverage.py 产出（都是可重跑的派生物）。
      仓库与云端没有 _review_items/，改读根目录的 items.json.gz、table-rows.json.gz、
      doc-report.json.gz、file-registry.json.gz —— 后两份由 --stage 从本机产物落出来。
"""
from __future__ import annotations

import argparse
import gzip
import json
import re
import sqlite3
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SRC = ROOT / "sources"
REV = ROOT / "_review_items"
DB = ROOT / "kb.sqlite"

CJK = re.compile(r"[一-鿿]")


def norm(s: str) -> str:
    return re.sub(r"\s+", "", s or "")


FULL_SKIP = {"id", "auto", "auto_kind", "archive_only", "status", "confidence",
             "exclude_exact", "slots", "draft", "kind", "url"}


CHUNK_MAX = 120


def split_chunk(s: str) -> list[str]:
    """长句再切成小句：BM25 按块长归一化，400 字的块会被 30 字的块压死。"""
    if len(s) <= CHUNK_MAX:
        return [s]
    out, buf = [], ""
    for piece in re.split(r"(?<=[。；！？;!?])|(?<=\n)", s):
        if not piece:
            continue
        if len(buf) + len(piece) > CHUNK_MAX and buf:
            out.append(buf.strip())
            buf = piece
        else:
            buf += piece
        while len(buf) > CHUNK_MAX:          # 单句就超长，硬切
            out.append(buf[:CHUNK_MAX].strip())
            buf = buf[CHUNK_MAX:]
    if buf.strip():
        out.append(buf.strip())
    return [x for x in out if x]


SHORT_LEAF = 8


def item_chunks(it: dict) -> list[str]:
    """把一条条目切成若干可检索块：长文按句切，短词并成一块。

    整条拼一行会被长度归一化压死（11-06 实测 `xyy-gongfei` 排 60 名开外，
    它的 answer 是空的、正文全在 steps 里）；但反过来把 keywords 里「医保」
    这种 2 字词单独成块，它在任何查询下都靠超短长度通吃 BM25——
    实测「医保」查询前 5 名全是 2 字块，真正的条目反而排 40 名外。
    所以短词合并，长文切句。
    """
    long_chunks: list[str] = []
    shorts: list[str] = []

    def walk(v):
        if isinstance(v, str):
            s = v.strip()
            if not s:
                return
            if len(s) < SHORT_LEAF:
                shorts.append(s)
            else:
                long_chunks.extend(split_chunk(s))
        elif isinstance(v, dict):
            for x in v.values():
                walk(x)
        elif isinstance(v, (list, tuple)):
            for x in v:
                walk(x)

    for k, v in it.items():
        if k in FULL_SKIP:
            continue
        walk(v)

    out = long_chunks
    buf = ""
    for w in shorts:
        if len(buf) + len(w) + 1 > CHUNK_MAX and buf:
            out.append(buf.strip())
            buf = w
        else:
            buf = f"{buf} {w}".strip()
    if buf.strip():
        out.append(buf.strip())
    return [x for x in out if x]


def bigrams(t: str) -> str:
    """中文串按相邻 2 字展开，非中文整段小写保留；单字补一个全角空格占位，保证它也可查。"""
    out: list[str] = []
    for run in re.findall(r"[一-鿿]+|[^\s一-鿿]+", t or ""):
        if CJK.match(run):
            if len(run) == 1:
                out.append(run + "　")
            out.extend(run[i:i + 2] for i in range(len(run) - 1))
        else:
            out.append(run.lower())
    return " ".join(out)


def one_src(item: dict) -> dict:
    s = item.get("source")
    if isinstance(s, list):
        s = next((x for x in s if isinstance(x, dict)), {})
    return s if isinstance(s, dict) else {}


def bucket_of(rel: str) -> str:
    parts = Path(rel).parts
    return parts[0] if len(parts) > 1 else "(根)"


def load_rows() -> list[dict]:
    """数据表行：本机在 _review_items/，仓库与云端只带 table-rows.json.gz。"""
    p = REV / "v2_table_rows.json"
    if p.exists():
        return json.loads(p.read_text(encoding="utf-8"))
    gz = ROOT / "table-rows.json.gz"
    if gz.exists():
        return json.loads(gzip.decompress(gz.read_bytes()).decode("utf-8"))
    sys.exit("缺数据表行产物（_review_items/v2_table_rows.json 或 table-rows.json.gz）")


def _read_json(path: Path) -> object:
    if path.suffix == ".gz":
        return json.loads(gzip.decompress(path.read_bytes()).decode("utf-8"))
    return json.loads(path.read_text(encoding="utf-8"))


def _pick(local_name: str, shipped: str) -> object:
    """本机优先读 _review_items/ 的明文产物，仓库与云端退回随包的根目录 gz。"""
    p = REV / local_name
    if p.exists():
        return _read_json(p)
    gz = ROOT / shipped
    if gz.exists():
        return _read_json(gz)
    sys.exit(f"缺 {local_name}（本机）或 {shipped}（随包）\n"
             "本机先跑：python tools/build_items_v2.py --apply && python tools/build_coverage.py\n"
             "云端先跑：python tools/build_kb_db.py --stage 后把根目录 gz 一并入库")


def load_items() -> list[dict]:
    src = (ROOT / "items.json") if (ROOT / "items.json").exists() else (ROOT / "items.json.gz")
    if not src.exists():
        sys.exit("缺 items.json 或 items.json.gz")
    return _read_json(src)["items"]


def load_report() -> list[dict]:
    return _pick("v2_report.json", "doc-report.json.gz")


def load_registry() -> list[dict]:
    reg = _pick("coverage_20261104.json", "file-registry.json.gz")
    return reg["rows"] if isinstance(reg, dict) and "rows" in reg else reg


def stage() -> None:
    """把两份流水线产物压成根目录 gz，供仓库与云端重建用（gzip mtime=0，可比对字节）。"""
    for local, shipped in [("v2_report.json", "doc-report.json.gz"),
                           ("coverage_20261104.json", "file-registry.json.gz")]:
        data = _read_json(REV / local)
        raw = json.dumps(data, ensure_ascii=False, separators=(",", ":")).encode("utf-8")
        gz = ROOT / shipped
        gz.write_bytes(gzip.compress(raw, 9, mtime=0))
        print(f"{shipped} {len(raw)} → {gz.stat().st_size} 字节，{len(data)} 行")


def build() -> None:
    if DB.exists():
        DB.unlink()
    items = load_items()
    report = load_report()
    rows = load_rows()
    reg = load_registry()

    con = sqlite3.connect(DB)
    con.executescript(
        """
        pragma journal_mode = off;
        create table doc(file text primary key, key text, bucket text, title text,
                         chars int, kind text, items int, rows int, missing int, overlap int, note text);
        create table item(id text primary key, doc text, kind text, title text, answer text,
                          archive_only int, status text, confidence text, dept text,
                          url text, published text, author text, column text,
                          keywords text, aliases text, also_from text);
        create table quote(item_id text, field text, src text, a int, b int, text text,
                           primary key(item_id, field));
        create table table_row(rowid integer primary key, doc text, bucket text, row_no int,
                               col int, header text, value text, title text);
        create table registry(file text primary key, bytes int, status text, chars int,
                              items int, rows int, kind text, slug text, note text);
        create virtual table search using fts5(gram, ref unindexed, kind unindexed, text,
                                               tokenize='unicode61');
        create index idx_item_doc on item(doc);
        create index idx_item_arch on item(archive_only);
        create index idx_quote_src on quote(src);
        create index idx_row_doc on table_row(doc);
        create view coverage as select file, key, chars, chars - missing as covered_chars,
               round(100.0 * (chars - missing) / max(chars, 1), 2) as pct, missing, overlap
               from doc;
        """)

    t0 = time.perf_counter()
    con.executemany(
        "insert into doc values(?,?,?,?,?,?,?,?,?,?,?)",
        [(r["file"], Path(r["file"]).stem, bucket_of(r["file"]), r.get("title", ""), r.get("chars", 0),
          r.get("kind", ""), r.get("items", 0), r.get("rows", 0), r.get("missing", 0),
          r.get("overlap", 0), r.get("note") or "")
         for r in report])

    ins_item, ins_quote = [], []
    for it in items:
        s = one_src(it)
        ins_item.append((it["id"], s.get("slug") or "", it.get("auto_kind") or ("curated" if not it.get("auto") else "auto"),
                         it.get("title", ""), it.get("answer") or "",
                         1 if it.get("archive_only") else 0, it.get("status") or "", it.get("confidence") or "",
                         it.get("dept") or "", s.get("url") or "", s.get("published") or "", s.get("author") or "",
                         s.get("column") or "",
                         json.dumps(it.get("keywords") or [], ensure_ascii=False),
                         json.dumps(it.get("aliases") or [], ensure_ascii=False),
                         json.dumps(it.get("also_from") or [], ensure_ascii=False)))
        for field, ev in (it.get("evidence") or {}).items():
            if isinstance(ev, dict):
                span = ev.get("span") or [None, None]
                ins_quote.append((it["id"], field, ev.get("src") or s.get("slug") or "",
                                  span[0], span[1], ev.get("quote") or ""))
    con.executemany("insert into item values(" + ",".join("?" * 16) + ")", ins_item)
    con.executemany("insert into quote values(?,?,?,?,?,?)", ins_quote)

    con.executemany("insert into table_row values(null,?,?,?,?,?,?,?)",
                    [(r["doc"], r.get("bucket", ""), r.get("row_no", 0), r.get("col", 0),
                      r.get("header", ""), r["value"], r.get("title", "")) for r in rows])

    con.executemany("insert into registry values(?,?,?,?,?,?,?,?,?)",
                    [(x["file"], x.get("bytes", 0), x.get("status", ""), x.get("chars", 0),
                      x.get("items", 0), x.get("rows", 0), x.get("kind", "") or "", x.get("slug", "") or "",
                      x.get("note", "") or "") for x in reg])

    # 检索索引：条目答案 + 数据行 + 逐字引文，三类都进 gram 虚表，kind 用来分路
    trip = [("item", it["id"], it.get("answer") or "") for it in items]
    trip += [("title", it["id"], it.get("title") or "") for it in items]
    # 字段级块：长文切句、短词合并（见 item_chunks 的说明）
    for it in items:
        trip += [("full", it["id"], chunk) for chunk in item_chunks(it)]
    # 名目行：标题＋别名＋关键词单独一块，权重自成一路。
    # 「学校医保」这种问句，正文里出现「医保」的摘录有几十条，
    # 只有别名里写着「医保报销」的那条才是学生口径——名目行让这一眼可排。
    for it in items:
        meta = " ".join([it.get("title") or ""]
                        + [str(a) for a in (it.get("aliases") or [])]
                        + [str(w) for w in (it.get("keywords") or [])]).strip()
        if meta:
            trip.append(("meta", it["id"], meta))
    trip += [("row", f"{r['doc']}#{r.get('row_no', 0)}#{r.get('col', 0)}", r["value"]) for r in rows]
    trip += [(f"{q[0]}~{q[1]}", q[2], q[5]) for q in ins_quote if len(q[5]) <= 1200]
    con.executemany("insert into search(gram, ref, kind, text) values(?,?,?,?)",
                    [(bigrams(t), ref, k, t) for k, ref, t in trip])
    con.commit()
    print(f"建库 {time.perf_counter() - t0:.1f}s")
    con.close()
    print(f"{DB.name} {DB.stat().st_size / 1e6:.1f} MB")


def verify() -> int:
    items = load_items()
    n_reg_src = len(load_registry())
    n_doc_src = len(load_report())
    con = sqlite3.connect(DB)
    n_item = con.execute("select count(*) from item").fetchone()[0]
    n_quote = con.execute("select count(*) from quote").fetchone()[0]
    n_ev = sum(len(it.get("evidence") or {}) for it in items)
    n_row = con.execute("select count(*) from table_row").fetchone()[0]
    n_src_row = len(load_rows())
    n_reg = con.execute("select count(*) from registry").fetchone()[0]
    n_doc = con.execute("select count(*) from doc").fetchone()[0]
    files = [p for p in SRC.rglob("*") if p.is_file() and "_quarantine" not in p.parts]
    miss = con.execute("select count(*) from doc where missing > 0").fetchone()[0]
    over = con.execute("select coalesce(sum(overlap),0) from doc").fetchone()[0]
    arch = con.execute("select count(*) from item where archive_only = 1").fetchone()[0]
    # 正文文件必须逐个在场；二进制原件（434 份 PDF/Office）不随包，只报数不判失败
    strict = [r[0] for r in con.execute("select file from registry where status like '正文%'")]
    loose = [r[0] for r in con.execute("select file from registry where status like '二进制·已抽%'")]
    gone = [f for f in strict if not (SRC / f).exists()]
    gone_bin = [f for f in loose if not (SRC / f).exists()]

    def hit(q: str) -> int:
        toks = [q[i:i + 2] for i in range(len(q) - 1)] if CJK.search(q) else [q.lower()]
        expr = " AND ".join('"' + t.replace('"', "") + '"' for t in toks)
        return con.execute("select count(*) from search where search match ?", (expr,)).fetchone()[0]

    probes = {p: hit(p) for p in ("户口", "补考", "挂失", "绩点", "ps", "校园卡", "公费医疗", "家属区")}
    bad = []
    if n_item != len(items):
        bad.append(f"item 行数 {n_item} != items.json {len(items)}")
    if n_quote != n_ev:
        bad.append(f"quote 行数 {n_quote} != 证据字段 {n_ev}")
    if n_row != n_src_row:
        bad.append(f"table_row 行数 {n_row} != 产物 {n_src_row}")
    if n_reg != n_reg_src:
        bad.append(f"registry 行数 {n_reg} != 产物 {n_reg_src}")
    if n_doc != n_doc_src:
        bad.append(f"doc 行数 {n_doc} != 产物 {n_doc_src}")
    if gone:
        bad.append(f"登记为正文但盘上没有的文件 {len(gone)} 份，例如 {gone[:3]}")
    if miss or over:
        bad.append(f"位图缺口 {miss} 份 / 重复认领 {over} 字")
    if not any(v > 0 for v in probes.values()):
        bad.append("FTS 探针全 0 命中，索引没建对")

    print(f"item {n_item}（archive_only {arch}）/ quote {n_quote} / table_row {n_row} "
          f"/ registry {n_reg} / doc {n_doc}")
    print("2 字探针命中：", " ".join(f"{k}:{v}" for k, v in probes.items()))
    print(f"sources/ 在场文件 {len(files)} 份；正文 {len(strict) - len(gone)}/{len(strict)}；"
          f"二进制原件缺 {len(gone_bin)}/{len(loose)} 份（不随包，属预期）")
    for b in bad:
        print("  ✗", b)
    print("✅ 库与 items.json、流水线产物、sources/ 逐一对上" if not bad else "❌ 有对不上的项")
    con.close()
    return 1 if bad else 0


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--verify", action="store_true")
    ap.add_argument("--stage", action="store_true", help="只落随包产物，不建库")
    a = ap.parse_args()
    if a.stage:
        stage()
        sys.exit(0)
    if not a.verify:
        build()
    if not DB.exists():
        print("库不存在，先跑不带 --verify 的建库")
        sys.exit(2)
    sys.exit(verify())
