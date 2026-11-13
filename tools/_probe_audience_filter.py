"""量化：人群过滤（_evidence_allowed）到底砍掉了多少关键条款。

对 diag 里的 30 问，用记录下来的检索短句重算候选池，比较两种过滤：
  A 现行：文件标题含 硕士/博士/研究生/教师… 且问句没提 → 整条砍掉
  B 改后：条目自带 audience 时以条目为准（本科/通用条目不因标题被砍）
统计：被砍的引文数、被砍的「穷尽枚举」条款数、恢复了哪些关键条款。
只读，不写 app。
"""
import json
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import app  # noqa: E402

OK, BLOCKED = "ok", "blocked"
KEYWORD = re.compile(r"(资格|条件|要求|标准|下列|以下)")
MARK = re.compile(r"[（(]\s*([一二三四五六七八九十]{1,2}|\d{1,2})\s*[）)]")


def enum_len(q: str) -> int:
    return len(MARK.findall(q))


def aud_allows(item: dict | None, question: str) -> bool:
    """B 方案：条目自带 audience 优先。"""
    aud = " ".join(item.get("audience") or []) if item else ""
    if aud and not any(w in aud for w in ("研究生", "博士", "教师", "教职工", "留学生")):
        return True
    return True if not aud else _title_allows((" ".join(item.get("audience") or [])), question)


def _title_allows(label: str, question: str) -> bool:
    for w in ("博士", "硕士", "研究生", "教师", "教职工", "人事", "招聘", "留学生", "国际学生"):
        if w in label and w not in question:
            return False
    return True


def rows_for(t: str) -> dict[str, dict]:
    rows: dict[str, dict] = {}
    for it, sc in app.rank(t)[:8]:
        if sc >= 40:
            rows.setdefault(it["id"], it)
    for it, _ in app.bm25_hits(t, k=40):
        rows.setdefault(it["id"], it)
    for it, _ in app.meta_hits(t, k=10):
        rows.setdefault(it["id"], it)
    return rows


def main() -> None:
    recs = [json.loads(l) for l in
            open("_review_items/synth_diag_20261110.jsonl", encoding="utf-8")]
    recs = [r for r in recs if not r.get("error")]
    tot_quotes = tot_blocked = 0
    enum_blocked = 0
    recover: dict[str, list[str]] = {}
    for r in recs:
        q = r["q"]
        qb_all = {g for g in app.bigrams(app.norm(q)) if g not in app._TOPIC_STOP}
        for t in dict.fromkeys(r["queries"]):
            rows = rows_for(t)
            for it in rows.values():
                for _k, v in (it.get("evidence") or {}).items():
                    for one in app._ev_items(v):
                        qq = str((one or {}).get("quote") or "").strip()
                        if len(app._mn(qq)) < 12:
                            continue
                        lab = str(app.src_label(str((one or {}).get("src") or ""))
                                  .get("label") or "")
                        nb = len(qb_all & app.bigrams(app.norm(qq)))
                        if nb < 1:
                            continue
                        if re.search(r"[\u4e00-\u9fff]", lab) and len(lab) < 6:
                            continue
                        tot_quotes += 1
                        if _title_allows(lab, q):
                            continue
                        tot_blocked += 1
                        if enum_len(qq) >= 3 and KEYWORD.search(qq[:60]):
                            enum_blocked += 1
                            recover.setdefault(q, []).append(
                                f"{lab[:26]} | {qq[:70]}")
        print(f"…{len(recover)} 问已出现可恢复条款 | {q[:30]}")
    print("=" * 70)
    print(f"候选引文总数(按 30 问×短句去重前) {tot_quotes}，被标题人群过滤砍掉 {tot_blocked}")
    print(f"其中「穷尽枚举且带资格/条件引语」的关键条款 {enum_blocked}")
    print()
    for q, items in recover.items():
        print("·", q)
        for x in items[:3]:
            print("    ", x)


if __name__ == "__main__":
    main()
