"""验收器：只核对结构、条目覆盖与一对多差额，**不判断标题对不对**（那必须人读）。

用法：
  ./.venv/Scripts/python.exe -X utf8 -u tools/validate_toc.py _review_items/toc/att-xxx.json
  ./.venv/Scripts/python.exe -X utf8 -u tools/validate_toc.py _review_items/toc        # 验整个目录
  ./.venv/Scripts/python.exe -X utf8 -u tools/validate_toc.py <file> --quiet            # 只出错才打印

退出码：0 全部通过；1 有硬错误。软问题（低置信、标题过长）只提示，不影响退出码。
"""
import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DOCLIST = ROOT / "_review_items" / "toc" / "_doclist.json"
LONG_HEADINGS = ROOT / "_review_items" / "toc" / "_long_headings.json"
HARD: list[str] = []
SOFT: list[str] = []


def _registered_long() -> set[str]:
    """已登记的长标题例外：原文标题超 20 字、按「原文不截断」保留，不再提示。"""
    try:
        d = json.loads(LONG_HEADINGS.read_text(encoding="utf-8"))
        return {str(x.get("section_id") or "") for x in (d.get("items") or [])}
    except Exception:  # noqa: BLE001
        return set()


REGISTERED_LONG = _registered_long()

# 可选检查（--chapter-node-check）：章标题被并进首段、导致章节点缺失的情形。
# 默认关闭，避免改变既有批次的基线提示数；验收汇编时显式打开。
CHAPTER_CHECK = False
_CHAPTER = re.compile(r"^第[一二三四五六七八九十百]+章")


def hard(msg: str) -> None:
    HARD.append(msg)


def soft(msg: str) -> None:
    SOFT.append(msg)


def check_one(path: Path, docs: dict[str, dict]) -> None:
    tag = path.name
    try:
        d = json.loads(path.read_text(encoding="utf-8"))
    except Exception as e:  # noqa: BLE001
        hard(f"{tag}: JSON 解析失败 {e}")
        return
    doc = d.get("doc") or {}
    key = str(doc.get("key") or "")
    if not key:
        hard(f"{tag}: 缺 doc.key")
        return
    if key not in docs:
        hard(f"{tag}: doc.key={key} 不在 _doclist.json 里")
        return
    if not str(doc.get("title") or "").strip():
        hard(f"{tag}: 缺 doc.title（大标题）")
    if doc.get("title_kind") not in ("author", "derived"):
        soft(f"{tag}: doc.title_kind 应为 author/derived，现在是 {doc.get('title_kind')!r}")
    want_ids = set(docs[key]["ids"])
    sections = d.get("sections") or []
    container = bool(doc.get("container_only"))
    if not sections and not container:
        hard(f"{tag}: sections 为空（只有 doc.container_only=true 的容器页文件允许为空）")
    seen: dict[str, str] = {}
    order_bad = 0
    for i, s in enumerate(sections):
        sid = str(s.get("section_id") or "")
        head = str(s.get("heading") or "").strip()
        cno = str(s.get("clause_no") or "").strip()
        if not sid:
            hard(f"{tag}: 第 {i+1} 个 section 缺 section_id")
            sid = f"<idx{i+1}>"
        if sid in {x.get("section_id") for x in sections if x is not s}:
            hard(f"{tag}: section_id 重复 {sid}")
        if not head:
            hard(f"{tag}: {sid} 缺 heading（小标题）")
        elif cno and head == cno:
            hard(f"{tag}: {sid} 的 heading 就是条号「{head}」，必须是语义名")
        elif len(head) > 20 and sid not in REGISTERED_LONG:
            soft(f"{tag}: {sid} 的 heading 过长（{len(head)} 字），像正文")
        if s.get("heading_kind") not in ("author", "derived"):
            soft(f"{tag}: {sid} 的 heading_kind 应为 author/derived")
        eids = s.get("entry_ids")
        if not isinstance(eids, list) or not eids:
            if s.get("placeholder"):
                # 结构占位节：原文有这一章，但库里一个碎片都没有。保留结构，不挂条目。
                if not str(s.get("note") or "").strip():
                    soft(f"{tag}: 占位节 {sid} 应写 note 说明「原文有、库中 0 条目」")
            else:
                hard(f"{tag}: {sid} 的 entry_ids 为空（结构占位请标 placeholder=true）")
            continue
        if s.get("placeholder"):
            soft(f"{tag}: {sid} 标了 placeholder 却挂了条目，二者矛盾")
        for eid in s["entry_ids"]:
            if eid not in want_ids:
                hard(f"{tag}: {sid} 挂了不属于该文档的条目 {eid}")
            if eid in seen:
                hard(f"{tag}: 条目重复挂载 {eid}（{seen[eid]} 与 {sid}）")
            else:
                seen[eid] = sid
        if s.get("merged_chapters"):
            mc = s["merged_chapters"]
            if not isinstance(mc, list) or len(mc) < 2:
                soft(f"{tag}: {sid} 的 merged_chapters 应是被合并章名的数组（≥2 项）")
            if not str(s.get("note") or "").strip():
                soft(f"{tag}: {sid} 合并了章节，note 里要写清合并了哪几章、为什么")
        if isinstance(s.get("order"), int):
            if s["order"] < order_bad:
                soft(f"{tag}: {sid} 的 order 没有递增")
            order_bad = s["order"]
        for j, c in enumerate(s.get("clauses") or []):
            if not str(c.get("text") or "").strip():
                hard(f"{tag}: {sid} 第 {j+1} 条 clause 正文为空")
        if CHAPTER_CHECK:
            cls = s.get("clauses") or []
            first = str((cls[0] or {}).get("text") or "").strip() if cls else ""
            m = _CHAPTER.match(first)
            if m and not _CHAPTER.match(cno):
                soft(f"{tag}: {sid} 首段以「{m.group(0)}」开头而本节 clause_no={cno!r}，"
                     f"章节点可能缺失（章标题被并进首段）")
    un = [u.get("entry_id") for u in (d.get("unassigned") or [])]
    for u in (d.get("unassigned") or []):
        if not str(u.get("entry_id") or ""):
            hard(f"{tag}: unassigned 里有一条缺 entry_id")
        elif not str(u.get("why") or "").strip():
            hard(f"{tag}: unassigned 条目 {u.get('entry_id')} 没写 why")
        if u.get("entry_id") in seen:
            hard(f"{tag}: 条目 {u.get('entry_id')} 同时出现在 section 和 unassigned")
    covered = set(seen) | {u for u in un if u}
    missing = want_ids - covered
    extra = covered - want_ids
    # 汇编分片（doc.partial=true）：单文件不要求覆盖全量，由 main() 里按 key 汇总校验
    partial = bool(doc.get("partial"))
    if missing:
        if partial:
            # 分片文件本来就不覆盖全量；只在「一条都没覆盖」时才提示，避免 108 份刷屏
            if not covered:
                soft(f"{tag}: 分片文件一个条目都没覆盖，确认是不是空文件")
        else:
            hard(f"{tag}: 漏掉 {len(missing)} 个条目，例：{sorted(missing)[:5]}")
    if extra:
        hard(f"{tag}: 多出 {len(extra)} 个不属于该文档的条目，例：{sorted(extra)[:5]}")
    st = d.get("stats") or {}
    if st:
        # 分片文件的 entries_total 记的是「本片拿到的条目数」，不是外层文件总数
        expect_total = len(covered) if partial else len(want_ids)
        if int(st.get("entries_total", -1)) != expect_total:
            soft(f"{tag}: stats.entries_total 应等于 {expect_total}，现为 {st.get('entries_total')}")
        if int(st.get("entries_assigned", -1)) != len(seen):
            soft(f"{tag}: stats.entries_assigned 应等于 {len(seen)}，现为 {st.get('entries_assigned')}")
        if int(st.get("sections", -1)) != len(sections):
            soft(f"{tag}: stats.sections 应等于 {len(sections)}，现为 {st.get('sections')}")
    # 一对多线索：一节的条目数与文本段数差太多时提示
    for s in sections:
        n_ids = len(s.get("entry_ids") or [])
        n_cl = len(s.get("clauses") or [])
        if n_ids >= 6 and n_cl <= 1:
            soft(f"{tag}: {s.get('section_id')} 挂了 {n_ids} 个条目但只有 {n_cl} 段原文，"
                 f"确认是不是把多段合成一段了")


def main() -> None:
    args = [a for a in sys.argv[1:] if not a.startswith("--")]
    quiet = "--quiet" in sys.argv[1:]
    # 分批交付模式：同一个 key 只交了部分分片时，把「漏」当进度而不是错误
    partial_batch = "--partial-batch" in sys.argv[1:]
    global CHAPTER_CHECK
    CHAPTER_CHECK = "--chapter-node-check" in sys.argv[1:]
    if not DOCLIST.exists():
        print("找不到 _review_items/toc/_doclist.json")
        sys.exit(1)
    docs = {x["key"]: x for x in json.loads(DOCLIST.read_text(encoding="utf-8"))["docs"]}
    targets: list[Path] = []
    for a in args:
        p = Path(a)
        if p.is_dir():
            # 目录扫描时跳过 _doclist / _no_text / _report 这些元文件
            targets += [q for q in sorted(p.glob("*.json")) if not q.name.startswith("_")]
        else:
            targets.append(p)
    if not targets:
        print("没有可验的文件")
        sys.exit(1)

    # 汇编会被拆成多个文件（doc.partial=true，同一个 doc.key）。
    # 这种情况下覆盖率要按 key 汇总后再查，单看一个文件永远不齐。
    by_key: dict[str, list[Path]] = {}
    for p in targets:
        try:
            d = json.loads(p.read_text(encoding="utf-8"))
        except Exception:  # noqa: BLE001
            continue
        k = str(((d.get("doc") or {}).get("key")) or "")
        if k:
            by_key.setdefault(k, []).append(p)

    for p in targets:
        check_one(p, docs)

    # 多文件同 key：把各文件合起来再查一次覆盖
    for key, paths in by_key.items():
        if len(paths) <= 1:
            continue
        want = set(docs.get(key, {}).get("ids") or [])
        if not want:
            continue
        got: set[str] = set()
        dup: list[str] = []
        for p in paths:
            try:
                d = json.loads(p.read_text(encoding="utf-8"))
            except Exception:  # noqa: BLE001
                continue
            for s in d.get("sections") or []:
                for eid in s.get("entry_ids") or []:
                    if eid in got:
                        dup.append(eid)
                    got.add(eid)
            for u in d.get("unassigned") or []:
                got.add(str(u.get("entry_id") or ""))
        missing = want - got
        if missing:
            if partial_batch:
                # 分批交付模式：本次只交了该 key 的一部分分片，漏的算进度，不算错。
                done = len(want & got)
                pct = round(100 * done / max(1, len(want)))
                print(f"ℹ️  {key}: 分批模式，本批 {len(paths)} 个分片覆盖 {done}/{len(want)} 条"
                      f"（{pct}%），未交 {len(missing)} 条")
            else:
                hard(f"{key}: 拆成 {len(paths)} 个文件后仍漏 {len(missing)} 个条目，"
                     f"例：{sorted(missing)[:5]}")
        if dup:
            hard(f"{key}: 跨文件重复挂载 {len(set(dup))} 个条目，例：{sorted(set(dup))[:5]}")
        if not missing and not dup:
            print(f"ℹ️  {key}: {len(paths)} 个分片合起来覆盖 {len(want)} 个条目，无重复 ✓")

    if REGISTERED_LONG:
        print(f"ℹ️  长标题已登记例外 {len(REGISTERED_LONG)} 条（不计提示）："
              f"{sorted(REGISTERED_LONG)[:3]}")
    if HARD:
        print(f"❌ 硬错误 {len(HARD)} 条：")
        for m in HARD[:40]:
            print("   -", m)
    if SOFT:
        print(f"⚠️  提示 {len(SOFT)} 条：")
        for m in SOFT[:20]:
            print("   -", m)
    if not quiet or HARD:
        print(f"\n验了 {len(targets)} 份；硬错误 {len(HARD)}，提示 {len(SOFT)}")
    sys.exit(1 if HARD else 0)


if __name__ == "__main__":
    main()
