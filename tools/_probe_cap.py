"""查证：资格条款在 _synth_candidates 里是被 cap 挤掉的，还是根本没进池。"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import app  # noqa: E402

TARGET = "tuimian-tiaojian"


def trace(question: str, queries: list[str]) -> None:
    print("=" * 74)
    print("Q:", question)
    pool: dict[str, dict] = {}
    for t in queries:
        qb = {g for g in app.bigrams(app.norm(t)) if g not in app._TOPIC_STOP}
        rows: dict[str, dict] = {}
        for it, sc in app.rank(t)[:8]:
            if sc >= 40:
                rows.setdefault(it["id"], it)
        for it, _ in app.bm25_hits(t, k=40):
            rows.setdefault(it["id"], it)
        for it, _ in app.meta_hits(t, k=10):
            rows.setdefault(it["id"], it)
        seen_target = TARGET in rows
        for it in rows.values():
            for _k, v in (it.get("evidence") or {}).items():
                for one in app._ev_items(v):
                    q = str((one or {}).get("quote") or "").strip()
                    if len(app._mn(q)) < 12:
                        continue
                    meta = app.src_label(str((one or {}).get("src") or ""))
                    lab = str(meta.get("label") or "")
                    if not app._evidence_allowed(lab, question):
                        continue
                    cover = len(qb & app.bigrams(app.norm(q)))
                    if cover < 1:
                        continue
                    key = app.norm(q)[:80]
                    if key in pool:
                        pool[key]["hits"].add(t)
                        pool[key]["cover"] = max(pool[key]["cover"], cover)
                        continue
                    pool[key] = {"doc": lab, "quote": q, "cover": cover,
                                 "query": t, "hits": {t}, "id": it["id"]}
        print(f"  query {t!r}: 目标条目在本轮 rows 里={seen_target}")

    cands = list(pool.values())
    strong = [c for c in cands if len(c["hits"]) >= 2 or int(c["cover"]) >= 2]
    use = strong if len(strong) >= 6 else cands
    use.sort(key=lambda c: (-len(c["hits"]), -int(c.get("tcover") or 0), -int(c["cover"])))
    print(f"  pool={len(cands)} strong={len(strong)} use={len(use)} cap=48")
    pos = [i + 1 for i, c in enumerate(use) if c["id"] == TARGET]
    print(f"  目标条目在 use 里的位置: {pos or '不在 use'}")
    if pos:
        print(f"    会被 cap 截掉: {pos[0] > 48}")
    # 单条精确检索这条条款
    for it, s in app.rank("推免 资格条件 基本条件")[:3]:
        print(f"    rank('推免 资格条件 基本条件') -> {it['id']} score={s}")


if __name__ == "__main__":
    trace("四六级没过能毕业吗？能保研吗？",
          ["毕业 学分要求 外语", "推免 基本条件 外语", "综合测评 四六级 计分",
           "推免 资格条件", "毕业 外语 要求"])
    trace("挂科了还能保研吗？补考通过算吗？",
          ["推免 基本条件 挂科 补考 成绩认定", "补考成绩 推免 排名 计算规则",
           "推免 综合测评 成绩 挂科 一票否决", "推免 申请条件 成绩要求",
           "补考 成绩记载 绩点 计算"])
