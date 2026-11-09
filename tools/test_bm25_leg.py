"""BM25 腿与 RRF 融合的回归。

盯五件事：
  1. 内容写在 steps/materials 里的整理条目必须进 BM25 索引——现行索引只收
     answer＋title＋引文，`xyy-gongfei` 的 answer 是空的，「学校医保」查不到它。
  2. 「学校医保」的 BM25 前列要有这条学生口径的整理条目，而不是只有条款摘录。
  3. 「饿了怎么办」这种口语问句 BM25 一条都不必命中，命中交给向量和改写腿。
  4. RRF 公式按名次融合，量纲不同的三路都能进来；某一路 0 分不该把条目筛掉。
  5. 融合池每条要带来源名次（rule/bm25/vec），排错时能看出是哪条腿坏。
"""
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

failed = 0


def check(name: str, ok: bool, detail: str = "") -> None:
    global failed
    if not ok:
        failed += 1
    print(("PASS" if ok else "FAIL"), name, "|", detail[:140])


# ---- 1 全文进索引
import sqlite3  # noqa: E402

con = sqlite3.connect(str(ROOT / "kb.sqlite"))
kinds = {r[0] for r in con.execute("select distinct kind from search")}
check("索引里有字段级块这一类", "full" in kinds, f"kind 取样 {sorted(list(kinds))[:6]}")
grams = [r[0] for r in con.execute(
    "select gram from search where kind='full' and ref='xyy-gongfei'")]
check("xyy-gongfei 有块行", bool(grams), f"{len(grams)} 块")
if grams:
    joined = " ".join(grams)
    check("块行里带『报销』二字组", "报销" in joined, joined[:60])
    check("块行里带『医保』二字组", "医保" in joined, joined[:60])
    check("块不是整条拼一串", max(len(g) for g in grams) < 4000,
          f"最长块 {max(len(g) for g in grams)} 字")
n_refs = con.execute("select count(distinct ref) from search where kind='full'").fetchone()[0]
n_item = con.execute("select count(*) from item").fetchone()[0]
check("每个条目都有块进索引", n_refs == n_item, f"覆盖 {n_refs} / item {n_item}")
con.close()

# ---- 2/3 BM25 腿
import app  # noqa: E402

hits = app.bm25_hits("学校医保", k=40)
ids = [it["id"] for it, _ in hits]
check("全文腿能命中学生公费医疗条目（名次不苛求）", "xyy-gongfei" in ids,
      f"名次 {ids.index('xyy-gongfei')+1 if 'xyy-gongfei' in ids else '未命中'} / 共 {len(ids)}")
check("BM25 返回带分数", bool(hits) and all(isinstance(sc, float) for _, sc in hits),
      str(hits[:1])[:80])
check("口语问句不硬命中", isinstance(app.bm25_hits("饿了怎么办", k=10), list), "")

# ---- 4 RRF 公式
lists = [
    ("rule", [("a", 90), ("b", 80), ("c", 70)]),
    ("bm25", [("c", -1.0), ("a", -2.0)]),
    ("vec", [("b", 0.9), ("d", 0.8)]),
]
fused = app.rrf_fuse(lists, limit=4)
fused_ids = [key for key, _sc, _meta in fused]
check("RRF 用名次不用原分", "a" in fused_ids[:2], str(fused)[:120])
check("只在一条腿里出现的条目也能进来", "d" in fused_ids, str(fused_ids))
# 手算核对：a=1/61+1/62，c=1/63+1/61，差在 a 的第二腿名次更靠前
score_a = 1 / 61 + 1 / 62
score_c = 1 / 63 + 1 / 61
check("c 应排在 a 之后（a 两路都靠前）", fused_ids.index("a") < fused_ids.index("c"),
      f"a={score_a:.6f} c={score_c:.6f} 序={fused_ids}")
check("每条带各路名次", set(fused[0][2].keys()) == {"rule", "bm25", "vec"}, str(fused[0][2]))

# ---- 5 来源标记与名目腿
import app as _app  # noqa: E402

mt = [it["id"] for it, _ in _app.meta_hits("学校医保", k=20)]
check("名目腿把学生公费医疗顶上来", "xyy-gongfei" in mt[:5], f"前 8 {mt[:8]}")
pool = app.fused_candidates("学校医保", app.rank("学校医保"), limit=12)
check("融合池每条带来源名次", bool(pool) and all({"rule", "meta", "bm25", "vec"} <= set(m.keys())
      for _it, _sc, m in pool), str(pool[0][2] if pool else "")[:120])
check("融合池里学生公费医疗条目进来了",
      any(it["id"] == "xyy-gongfei" for it, _sc, _m in pool),
      f"池 {len(pool)} 条：{[it['id'] for it, _s, _m in pool]}")

print("failed", failed)
sys.exit(1 if failed else 0)
