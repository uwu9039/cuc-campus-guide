"""探针（只读，不改任何逻辑）：rank() 全量扫描 39k 条值不值当，预筛能省多少。

做法：给每条目的「标题+别名+关键词」建二字组倒排，查询时只对命中的条目打分，
与现行 rank() 的前 10 名对比是否一致，并计时。
"""
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
import app  # noqa: E402

QS = [
    "图书馆开放时间", "校园网怎么办理", "保研基本条件", "转专业需要什么条件",
    "挂科了还能保研吗？补考通过算吗？", "校园卡冻结了，奖学金还能打进卡里吗？",
    "国家奖学金和国家励志奖学金能同时拿吗？", "宿舍电费怎么交", "体测多少分算良好",
    "推免是教务处管还是研究生院管？",
]


def build_index() -> dict[str, set[int]]:
    post: dict[str, set[int]] = {}
    for i, it in enumerate(app.ITEMS):
        if it.get("archive_only"):
            continue
        text = " ".join([str(it.get("title") or ""), *(it.get("aliases") or []),
                         *(it.get("keywords") or [])])
        for g in app.bigrams(app.norm(text)):
            post.setdefault(g, set()).add(i)
    return post


def prefiltered(q: str, post: dict[str, set[int]]) -> list[tuple[dict, int]]:
    qn = app.norm(q)
    grams = app.bigrams(qn)
    hit: set[int] = set()
    for g in grams:
        hit |= post.get(g, set())
    blocked = app.blocked_keys(qn)
    scored = [(app.ITEMS[i], app.score_item(qn, app.ITEMS[i], blocked.get(app.ITEMS[i]["id"])))
              for i in hit]
    scored.sort(key=lambda x: -x[1])
    return scored


def main() -> None:
    t0 = time.perf_counter()
    post = build_index()
    t_build = time.perf_counter() - t0
    print(f"倒排索引：{len(post)} 个二字组，耗时 {t_build:.2f}s\n")
    t_full = t_pre = 0.0
    same = 0
    for q in QS:
        t0 = time.perf_counter()
        full = app.rank(q)
        t_full += time.perf_counter() - t0
        t0 = time.perf_counter()
        pre = prefiltered(q, post)
        t_pre += time.perf_counter() - t0
        top_full = [it["id"] for it, _ in full[:10]]
        top_pre = [it["id"] for it, _ in pre[:10]]
        ok = top_full == top_pre
        same += ok
        print(f"{'前10一致' if ok else '前10不同'} | 全量 {len(full)} 条 / 预筛 {len(pre)} 条 | {q[:26]}")
        if not ok:
            print("   全量:", top_full[:5])
            print("   预筛:", top_pre[:5])
    n = len(QS)
    print(f"\nrank() 平均 {t_full / n:.2f}s；预筛平均 {t_pre / n:.3f}s；"
          f"前 10 一致 {same}/{n}；加速 {t_full / max(t_pre, 1e-6):.0f}x")


if __name__ == "__main__":
    main()
